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
from typing import Optional
from urllib.parse import unquote

from bs4 import BeautifulSoup

from ..models import EntityMention, SourceFetch

logger = logging.getLogger(__name__)


# Patterns we deliberately exclude — Wikipedia infrastructure pages that are
# never standalone entities in our DB.
EXCLUDED_WIKI_PREFIXES = (
    "Help:",
    "Special:",
    "Wikipedia:",
    "Portal:",
    "Category:",
    "File:",
    "Template:",
    "Talk:",
    "User:",
    "Image:",
    "Module:",
)
# Disambiguation suffixes we strip — e.g. "Calgary,_Alberta" -> "Calgary, Alberta"
_DISAMBIG_RE = re.compile(
    r"_\((?:disambiguation|wrestler|wrestling|wrestling_promotion|wrestler\)\b)"
)


def _normalize_wiki_link(href: str) -> str:
    """
    Turn a raw href like '/wiki/Stampede_Wrestling#History' into the canonical
    page identifier 'Stampede Wrestling'. Returns '' for non-/wiki/ hrefs.
    """
    if not href.startswith("/wiki/"):
        return ""
    name = href[len("/wiki/") :]
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
    out = extract_mentions_with_sections(raw_html, max_mentions=max_mentions)
    return [
        {"mention_text": m["mention_text"], "wiki_link": m["wiki_link"]}
        for m in out
        if m["section_label"] is None
    ]


def _section_label_from_heading(node) -> Optional[str]:
    """
    Return a lower-cased section title from an h2/h3 element OR from a
    Vector-2022 `<div class="mw-heading">` wrapper, or None if not a heading.
    """
    name = getattr(node, "name", None)
    if name in ("h2", "h3", "h4"):
        return (node.get_text(" ", strip=True) or "").strip().lower() or None
    if name == "div":
        classes = node.get("class", []) or []
        if "mw-heading" in classes:
            inner = node.find(["h2", "h3", "h4"])
            if inner is not None:
                return (inner.get_text(" ", strip=True) or "").strip().lower() or None
    return None


def extract_mentions_with_sections(
    raw_html: str,
    max_mentions: int = 200,
) -> list[dict]:
    """
    Walk the whole article body, tracking which section each `<a>` lives in.

    Returns deduplicated `[{mention_text, wiki_link, section_label}]` where
    `section_label` is None for lede mentions (before the first heading)
    and the lower-cased heading text otherwise. Used by media linkers that
    need to require e.g. ==Roster== scoping rather than relying on
    "mentioned 2+ times" as a proxy.

    Same as `extract_mentions_from_lead`, this only inspects prose `<p>`
    children — not tables / lists — so navboxes don't pollute the result.
    """
    if not raw_html:
        return []

    soup = BeautifulSoup(raw_html, "lxml")
    body = soup.find("div", class_=re.compile(r"mw-parser-output"))
    if body is None:
        return []

    for noisy in body.find_all(["sup", "style", "script"]):
        noisy.decompose()

    out: list[dict] = []
    seen: set[str] = set()
    current_section: Optional[str] = None

    for child in body.children:
        # Heading? Update the current section context and move on.
        new_section = _section_label_from_heading(child)
        if new_section is not None:
            current_section = new_section
            continue

        # Only inspect prose paragraphs (same rationale as the lede-only
        # version — tables/lists/navboxes inflate mentions with anything
        # Wikipedia thought worth cross-listing).
        if getattr(child, "name", None) != "p":
            continue

        for a in child.find_all("a", href=True):
            href = a.get("href", "")
            link = _normalize_wiki_link(href)
            if _should_skip(link):
                continue
            text = a.get_text(strip=True)
            if not text:
                continue
            # Dedupe per (link, section) — same wiki target appearing in
            # both the lede and a Roster section is two distinct mentions
            # with different semantic weight.
            key = (link, current_section)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "mention_text": text,
                    "wiki_link": link,
                    "section_label": current_section,
                }
            )
            if len(out) >= max_mentions:
                return out

    return out


def persist_mentions_for_entity(
    entity_type: str,
    entity_id: int,
    fetch: SourceFetch,
    section_aware: bool = False,
) -> int:
    """
    Extract and persist EntityMention rows for any entity's source content.

    Idempotent via unique_together(source_fetch, wiki_link).

    When `section_aware=True`, walks the whole article tracking section
    headers and stamps each mention's `section_label`. Use this for book /
    video-game / TV-show articles where the linker needs to require
    `==Roster==` or `==Cast==` scoping. Defaults to lede-only extraction
    (the prior behavior) to avoid inflating wrestler/event/promotion
    mention counts with navigational sections.

    Returns count of newly-created mentions.
    """
    if section_aware:
        mentions = extract_mentions_with_sections(fetch.raw_content)
    else:
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
        section_label = m.get("section_label") if section_aware else None
        _, was_new = EntityMention.objects.get_or_create(
            source_fetch=fetch,
            wiki_link=m["wiki_link"],
            defaults={
                "source_entity_type": entity_type,
                "source_entity_id": entity_id,
                "mention_text": m["mention_text"][:255],
                "context": context,
                "section_label": section_label,
            },
        )
        if was_new:
            created += 1

    logger.info(
        "Extracted %d mention(s) for %s#%d (SourceFetch#%d)",
        created,
        entity_type,
        entity_id,
        fetch.id,
    )
    return created


def persist_mentions_for_wrestler(wrestler_id: int, fetch: SourceFetch) -> int:
    """Back-compat shim for code that still calls the wrestler-specific name."""
    return persist_mentions_for_entity("wrestler", wrestler_id, fetch)
