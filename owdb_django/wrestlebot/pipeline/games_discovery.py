"""
Discover + ingest professional-wrestling video games from the curated
seed catalog (`games_catalog.WRESTLING_GAME_SEEDS`).

This is the games equivalent of `title_history.ingest_title_history_discovery`
— for each seed, it:

  1. Picks the first Wikipedia title fallback that resolves to a real
     article (using the same `_first_existing_page` helper title-history
     uses).
  2. Queues the article for fetching through `fetch_video_game_candidates`
     so the standard fetch → classify → extract → persist pipeline runs
     end-to-end. Accuracy contract enforcement, FieldProvenance writing,
     and SourceFetch recording are unchanged.
  3. Returns per-slug stats: `found`, `already_in_db`, `queued_for_ingest`.

Like every other ingester in this codebase, missing seeds are a no-op.
Never fabricate metadata; if a Wikipedia article doesn't exist or the
extractor can't pull fields, the slug is silently skipped.

The discovered VideoGame's wrestler roster gets populated through the
*existing* persist_video_game path, which:
  * Writes a Wrestler M2M for every wrestler-mention resolved in the
    article's prose.
  * Adds promotion links for any KNOWN_PROMOTIONS hits.
That all happens INSIDE the persist call — this discovery module only
handles the candidate-queueing side.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def _resolve_first_existing_title(title_fallbacks: tuple[str, ...]) -> Optional[str]:
    """
    Find the first title in `title_fallbacks` whose Wikipedia article
    actually exists AND classifies as a video-game article. Returns the
    resolved canonical title (with redirects followed), or None if nothing
    resolved.

    Round-2 fix: previously this helper accepted any redirect target,
    which let a seed pointing at e.g. 'MDickie' (the human developer's
    page) resolve and queue as a VideoGame. The new pass-2 check looks
    for video-game infobox / category evidence in the lead HTML before
    accepting. Articles that exist but aren't games (people, list pages,
    TV shows, service hubs) are skipped, falling through to the next
    fallback in the seed tuple.
    """
    from .title_history import _wiki_parse_page

    for cand in title_fallbacks:
        d = _wiki_parse_page(cand)
        if not d or "parse" not in d:
            continue
        # Wikipedia's `action=parse` follows redirects by default and
        # returns the canonical title in `result.parse.title`.
        resolved = d["parse"].get("title", cand)
        text = d["parse"].get("text")
        html = (
            text if isinstance(text, str) else (text.get("*") if isinstance(text, dict) else None)
        )
        if not html:
            continue
        if not _looks_like_video_game_article(html, resolved):
            logger.info(
                "games_discovery: %r resolved but classifier rejected as "
                "non-video-game; trying next fallback",
                resolved,
            )
            continue
        return resolved
    return None


def _looks_like_video_game_article(html: str, article_title: str) -> bool:
    """
    Confirm a Wikipedia article's subject is a video game.

    Cheap-and-strict check:
      1. The article has an `infobox vg` / `infobox video game` table, OR
      2. Its lead paragraph contains explicit video-game phrasing
         ("is a [year] video game", "is a wrestling video game", etc.).

    Returns False for pages that exist but are about people (the article
    happens to mention games they made), list/hub pages, or sub-topics
    (a wrestler's filmography section).
    """
    from bs4 import BeautifulSoup
    import re as _re

    soup = BeautifulSoup(html or "", "lxml")

    # 1. Infobox class check. Wikipedia uses `infobox vg` (legacy) or
    # `infobox video-game` (modern) for game articles.
    infobox = soup.find(
        "table",
        class_=_re.compile(r"\binfobox\b.*\b(vg|video[-_ ]game)\b", _re.IGNORECASE),
    )
    if infobox is not None:
        return True

    # 2. Lead-paragraph phrasing check. Walk first 3 <p> elements in the
    # mw-parser-output body.
    body = soup.find("div", class_=_re.compile(r"mw-parser-output"))
    if body is None:
        return False
    paragraphs = []
    for child in body.children:
        if getattr(child, "name", None) == "p":
            text = child.get_text(separator=" ", strip=True).lower()
            if text:
                paragraphs.append(text)
        if len(paragraphs) >= 3:
            break
    lead_text = " ".join(paragraphs)[:2000]
    # Require a "is a ... game" phrase. Single-phrase matches false-positive
    # too often (a wrestler biography saying "appeared in a video game"),
    # but inside the games-discovery loop we only call this on URLs that
    # already came from a curated seed catalog, so a positive match here
    # is high signal.
    return any(
        p in lead_text
        for p in (
            "is a video game",
            "is a wrestling video game",
            "is an upcoming video game",
            "is a fighting game",
            "is a sports video game",
            "is a professional wrestling video game",
            "is a 2d professional wrestling",
            "is a 3d professional wrestling",
        )
    )


def ingest_games_discovery(
    slug: Optional[str] = None,
    *,
    max_unknown_to_queue: int = 30,
) -> dict:
    """
    Iterate seeds (or just one, if `slug` is set) and queue unknown games
    for the standard ingest pipeline. Returns per-slug stats.

    Mirrors the signature of `ingest_title_history_discovery` so the
    same agent-tool / management-command shell works for either.
    """
    from owdb_django.owdbapp.models import VideoGame
    from .fetch import fetch_video_game_candidates
    from .games_catalog import WRESTLING_GAME_SEEDS

    if slug is not None and slug not in WRESTLING_GAME_SEEDS:
        return {"error": f"unknown seed slug={slug!r}; valid: {sorted(WRESTLING_GAME_SEEDS)[:10]}…"}

    targets: list[str] = [slug] if slug else list(WRESTLING_GAME_SEEDS.keys())

    out: dict[str, dict] = {}
    grand_queued = 0
    grand_skipped = 0
    grand_already = 0

    for s in targets:
        fallbacks = WRESTLING_GAME_SEEDS[s]
        resolved = _resolve_first_existing_title(fallbacks)
        if not resolved:
            out[s] = {
                "resolved_wikipedia_title": None,
                "found": False,
                "already_in_db": 0,
                "queued_for_ingest": 0,
            }
            grand_skipped += 1
            continue

        # Already-in-db check: if a VideoGame with this exact canonical
        # title or matching wikipedia_url already exists, no need to
        # re-queue.
        existing = (
            VideoGame.objects.filter(
                name__iexact=resolved,
            ).first()
            or VideoGame.objects.filter(
                wikipedia_url__icontains=resolved.replace(" ", "_"),
            ).first()
        )

        if existing is not None:
            out[s] = {
                "resolved_wikipedia_title": resolved,
                "found": True,
                "already_in_db": 1,
                "queued_for_ingest": 0,
                "existing_id": existing.id,
            }
            grand_already += 1
            continue

        # Queue for the standard ingest path. fetch_video_game_candidates
        # writes a SourceFetch + classifies the page. The extract+persist
        # cycle that JR runs (`run_jr_cycle`) then picks it up.
        try:
            fetch_video_game_candidates([resolved], force=False)
            queued = 1
        except Exception as e:
            logger.warning(
                "games_discovery: fetch failed for %r (%s): %s",
                s,
                resolved,
                e,
            )
            queued = 0

        out[s] = {
            "resolved_wikipedia_title": resolved,
            "found": True,
            "already_in_db": 0,
            "queued_for_ingest": queued,
        }
        grand_queued += queued

        # Polite spacing on top of the rate-limiter; Wikipedia's article
        # API is generous but a per-seed pause makes the trace readable.
        time.sleep(0.1)

        if grand_queued >= max_unknown_to_queue:
            logger.info(
                "games_discovery: queue cap (%d) reached after %d slugs",
                max_unknown_to_queue,
                list(out).index(s) + 1,
            )
            break

    out["__totals__"] = {
        "seeds_processed": len(out) - 1,  # exclude the __totals__ key itself
        "total_queued": grand_queued,
        "total_already_in_db": grand_already,
        "total_skipped": grand_skipped,
    }
    return out
