"""
Extract third-party profile URLs from a Wikipedia page's "External links"
section. Used to populate Wrestler.cagematch_url / profightdb_url etc. so
the next pipeline cycle can fetch from those sources to cross-validate.

Pure HTML parsing. No network, no LLM.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Recognised external-link source hosts.
# Map host suffix -> entity field name on Wrestler/Promotion.
EXTERNAL_LINK_HOSTS = {
    "cagematch.net": "cagematch_url",
    "profightdb.com": "profightdb_url",
}


def extract_external_links(raw_html: str) -> dict[str, str]:
    """
    Walk the entire Wikipedia article (not just the lead) for `<a>` tags
    that match known external-source hosts. Returns the first match per
    host as a dict { entity_field_name: url }.

    For each matched host the FIRST <a> wins — Wikipedia typically lists
    the canonical profile first.
    """
    if not raw_html:
        return {}

    soup = BeautifulSoup(raw_html, "lxml")

    # Search the whole document body. External links can appear in the
    # infobox row "Worked for / Notable feuds" or, more typically, in the
    # "External links" section near the bottom.
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith(("http://", "https://")):
            continue
        host = urlparse(href).netloc.lower()
        # Strip leading "www." for matching.
        if host.startswith("www."):
            host = host[4:]
        for known_host, field_name in EXTERNAL_LINK_HOSTS.items():
            if host.endswith(known_host) and field_name not in found:
                found[field_name] = href
                break

    return found


# Cagematch URLs of interest take the form:
#   https://www.cagematch.net/?id=2&nr=NNN[&...]    (workers/wrestlers, id=2)
#   https://www.cagematch.net/?id=1&nr=NNN[&...]    (events, id=1)
# We only persist URLs that match a wrestler-style pattern.
_CAGEMATCH_WRESTLER_URL_RE = re.compile(
    r"https?://(?:www\.)?cagematch\.net/.*?[?&]id=2(?:[&]|$)",
    re.IGNORECASE,
)


def is_cagematch_wrestler_url(url: str) -> bool:
    """Return True iff the URL points at Cagematch's wrestler-profile route."""
    return bool(url and _CAGEMATCH_WRESTLER_URL_RE.match(url))


def apply_external_links_to_wrestler(wrestler, raw_html: str) -> dict:
    """
    Walk a wrestler's Wikipedia HTML for external links and write the
    discovered profile URLs onto the wrestler. Only populates fields that
    are currently empty (never overwrites).

    Returns dict of fields that were newly set.
    """
    found = extract_external_links(raw_html)
    if not found:
        return {}

    changed: dict[str, str] = {}
    for field_name, url in found.items():
        # Only persist the wrestler-form of the cagematch URL; an event
        # link would mislead the downstream Cagematch adapter.
        if field_name == "cagematch_url" and not is_cagematch_wrestler_url(url):
            continue

        existing = getattr(wrestler, field_name, "") or ""
        if existing:
            continue
        setattr(wrestler, field_name, url[:500])
        changed[field_name] = url

    if changed:
        wrestler.save(update_fields=list(changed.keys()) + ["updated_at"])

    return changed
