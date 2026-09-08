"""
Extract Wikipedia internal links from source content into EntityMention rows.

Every `<a href="/wiki/X">Y</a>` we find inside an entity's lead paragraphs is
a candidate cross-link. This module's job is to enumerate them — classification
and resolution happen later in the pipeline.

This is intentionally cheap: pure HTML parsing, no network, no LLM.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote

from bs4 import BeautifulSoup

from ..models import EntityMention, SourceFetch

logger = logging.getLogger(__name__)


# Patterns we deliberately exclude — Wikipedia infrastructure pages that are
# never standalone entities in our DB.
EXCLUDED_WIKI_PREFIXES = (
    "Help:", "Special:", "Wikipedia:", "Portal:", "Category:", "File:",
    "Template:", "Talk:", "User:", "Image:", "Module:",
)
# Disambiguation suffixes we strip — e.g. "Calgary,_Alberta" -> "Calgary, Alberta"
_DISAMBIG_RE = re.compile(r"_\((?:disambiguation|wrestler|wrestling|wrestling_promotion|wrestler\)\b)")


def _normalize_wiki_link(href: str) -> str:
    """
    Turn a raw href like '/wiki/Stampede_Wrestling#History' into the canonical
    page identifier 'Stampede Wrestling'. Returns '' for non-/wiki/ hrefs.
    """
    if not href.startswith("/wiki/"):
        return ""
    name = href[len("/wiki/"):]
    name = name.split("#", 1)[0].split("?", 1)[0]  # strip fragment / query
    name = unquote(name)
    name = name.replace("_", " ")
    return name.strip()


def _should_skip(wiki_link: str) -> bool:
    if not wiki_link:
        return True
    if any(wiki_link.startswith(prefix) for prefix in EXCLUDED_WIKI_PREFIXES):
        return True
    return False


def extract_mentions_from_lead(
    raw_html: str,
    max_mentions: int = 80,
) -> list[dict]:
    """
    Walk every `<a>` inside the .mw-parser-output lead area (before first <h2>)
    and return [{mention_text, wiki_link}] for /wiki/ links.

    Returns the deduplicated, position-ordered list.
    """
    if not raw_html:
        return []

    soup = BeautifulSoup(raw_html, "lxml")
    body = soup.find("div", class_=re.compile(r"mw-parser-output"))
    if body is None:
        return []

    # Strip footnote markers to avoid capturing cite-style internal links.
    for noisy in body.find_all(["sup", "style", "script"]):
        noisy.decompose()

    out: list[dict] = []
    seen: set[str] = set()

    for child in body.children:
        name = getattr(child, "name", None)
        if name in ("h2", "h3"):
            break
        # Wikipedia (Vector 2022 skin, late 2023+) wraps section headings in
        # <div class="mw-heading mw-headingN">. Treat those as section
        # boundaries.
        classes = child.get("class", []) if hasattr(child, "get") else []
        if "mw-heading" in classes:
            break
        # Only inspect prose paragraphs. Tables (infoboxes, sidebars, navboxes)
        # and lists (bibliography, "see also") are navigational and would
        # falsely link the subject to every entity Wikipedia thought worth
        # listing. The prose mentions are what we want.
        if name != "p":
            continue

        for a in child.find_all("a", href=True):
            href = a.get("href", "")
            link = _normalize_wiki_link(href)
            if _should_skip(link):
                continue
            text = a.get_text(strip=True)
            if not text:
                continue
            # Deduplicate by wiki_link (same target may appear multiple times).
            if link in seen:
                continue
            seen.add(link)
            out.append({"mention_text": text, "wiki_link": link})
            if len(out) >= max_mentions:
                return out

    return out


def persist_mentions_for_entity(
    entity_type: str,
    entity_id: int,
    fetch: SourceFetch,
) -> int:
    """
    Extract and persist EntityMention rows for any entity's source content.

    Idempotent via unique_together(source_fetch, wiki_link).

    Returns count of newly-created mentions.
    """
    mentions = extract_mentions_from_lead(fetch.raw_content)
    if not mentions:
        return 0

    # Map entity_type -> EntityMention.context value.
    context_map = {
        "wrestler": "wrestler_about",
        "event": "event_about",
        "promotion": "promotion_about",
        "venue": "event_about",  # venue articles describe events held there
    }
    context = context_map.get(entity_type, "wrestler_about")

    created = 0
    for m in mentions:
        _, was_new = EntityMention.objects.get_or_create(
            source_fetch=fetch,
            wiki_link=m["wiki_link"],
            defaults={
                "source_entity_type": entity_type,
                "source_entity_id": entity_id,
                "mention_text": m["mention_text"][:255],
                "context": context,
            },
        )
        if was_new:
            created += 1

    logger.info(
        "Extracted %d mention(s) for %s#%d (SourceFetch#%d)",
        created, entity_type, entity_id, fetch.id,
    )
    return created


def persist_mentions_for_wrestler(wrestler_id: int, fetch: SourceFetch) -> int:
    """Back-compat shim for code that still calls the wrestler-specific name."""
    return persist_mentions_for_entity("wrestler", wrestler_id, fetch)
