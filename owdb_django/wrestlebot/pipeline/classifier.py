"""
Wikipedia page classifier — what kind of wrestling entity is this article?

Used by the auto-discovery cycle: when an unresolved EntityMention points
at a /wiki/X target, we fetch the page and call classify_html() to decide
which pipeline to route it through (wrestler / event / venue / promotion).

Accuracy-first: if the classifier isn't confident, it returns None and the
page is skipped rather than wrongly typed.

Heuristics, in priority order:
  1. Infobox CSS classes hint at template type (e.g. "biography vcard").
  2. Infobox row labels reveal the schema:
     - "Real name" / "Ring name" / "Trained by"   -> wrestler
     - "Promotion" + "Date" + "Venue"             -> event
     - "Capacity" + "Location"                    -> venue
     - "Founded" + "Founder" / "Headquarters"     -> promotion
  3. Article categories (page lists "Category:...")
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Generic / concept pages that we deliberately never auto-discover.
# These show up in mentions because Wikipedia articles link to "Pay-per-view"
# every time they describe a PPV; they're not entities we want in the DB.
GENERIC_WIKI_TITLES = frozenset({
    # Concept / vocabulary pages — these get linked from every wrestling
    # article but they don't represent entities we want to index.
    "Professional wrestling",
    "Professional wrestler",
    "Wrestling promotion",
    "Wrestling promoter",
    "Wrestling match",
    "Pay-per-view",
    "Card (sports)",
    "Main event",
    "Main event (professional wrestling)",
    "Closed-circuit television",
    "Sports entertainment",
    "Professional wrestling match types",
    "Glossary of professional wrestling terms",
    "Ring name",
    "Ring name(s)",
    "Buyrate",
    "Singles match",
    "Tag team",
    "Tag team match",
    "Stable (professional wrestling)",
    "Promo (professional wrestling)",
    "Heel (professional wrestling)",
    "Face (professional wrestling)",
    "Submission hold",
    "Pinfall",
    "Disqualification",
    "Countout",
    "Championship belt",
    "Championship (professional wrestling)",
    "Multi-purpose stadium",
    "Multi-purpose arena",
    "Indoor arena",
    "Hall of fame",
    "1980s professional wrestling boom",
    "Monday Night War",
    "Attitude Era",
    "Ruthless Aggression Era",
    "PG Era",
    # Halls of fame are categories, not entity pages worth indexing.
    "WWE Hall of Fame",
    "WCW Hall of Fame",
    "Professional Wrestling Hall of Fame and Museum",
    "Wrestling Observer Newsletter Hall of Fame",
    "Wrestling Observer Newsletter",
    "WrestleCrap",
    # Currency / units linked by attendance/revenue paragraphs.
    "United States dollar",
    "Pound sterling",
    "Canadian dollar",
    "Mexican peso",
    "Japanese yen",
    # Sports leagues frequently linked from venue articles.
    "National Football League",
    "National Basketball Association",
    "National Hockey League",
    "Major League Baseball",
    # Meta-articles about event franchises (link to specific events, not entities).
    "WrestleMania",
    "Royal Rumble",
    "SummerSlam",
    "Survivor Series",
    "Starrcade",
    "King of the Ring",
    "Bash at the Beach",
    "Halloween Havoc",
    # Brand pages (not entities in our schema)
    "Raw (WWE brand)",
    "SmackDown",
    "NXT (WWE brand)",
    # Title pages — we don't have a Title pipeline yet. (When we add one,
    # remove these so they get classified as titles.)
    "WWE Championship",
    "WWE Universal Championship",
    "World Heavyweight Championship (WWE)",
    "WWE Intercontinental Championship",
    "WWE United States Championship",
    "World Tag Team Championship (WWE, 1971–2010)",
    "WWF Tag Team Championship",
    "WWE Tag Team Championship",
    "WWE Women's Championship",
    "WWE Raw Women's Championship",
    "WWE SmackDown Women's Championship",
    "WCW World Heavyweight Championship",
    "ECW World Heavyweight Championship",
    "NWA World Heavyweight Championship",
    "AEW World Championship",
    "IWGP Heavyweight Championship",
    "Triple Crown (professional wrestling)",
    "Grand Slam (professional wrestling)",
})


# Specific infobox-row labels that strongly indicate a type. Lower-cased.
WRESTLER_LABELS = {"real name", "birth name", "ring name", "ring names", "ring name(s)",
                   "trained by", "billed from", "billed weight", "billed height", "debut"}
EVENT_LABELS = {"promotion", "promotions", "tagline", "buyrate", "ppvchron", "attendance"}
VENUE_LABELS = {"capacity", "address", "owner", "operator", "construction broke ground",
                "opened", "tenants"}
PROMOTION_LABELS = {"founded", "founder", "founders", "headquarters", "headquarter",
                    "owner(s)", "key people", "parent", "industry"}


def is_generic_wiki_title(wiki_link: str) -> bool:
    """Block specific generic concept pages from auto-discovery."""
    if wiki_link in GENERIC_WIKI_TITLES:
        return True
    # Suffix-based filters — any "List of X" is a list page, not an entity.
    lowered = wiki_link.lower()
    if lowered.startswith(("list of ", "lists of ")):
        return True
    if lowered.endswith(" (disambiguation)"):
        return True
    return False


def _is_wrestling_relevant(soup: BeautifulSoup) -> bool:
    """
    Confirm a Wikipedia article is actually about pro wrestling.

    Why: the infobox-label-only classifier can't distinguish a wrestling
    promotion from a sports league (Canadian Football League, UFC) — both
    have Founded/Founder/Headquarters infobox rows. We need a content
    signal that the article subject is wrestling.

    Two checks, either passes:
      1. The article's leading prose mentions wrestling within the first
         few hundred characters.
      2. The page is in a wrestling-related Wikipedia category.
    """
    body = soup.find("div", class_=re.compile(r"mw-parser-output"))
    if body is None:
        return False

    # 1. Check leading paragraph text for wrestling keywords.
    first_paragraphs = []
    for child in body.children:
        name = getattr(child, "name", None)
        if name == "p":
            text = child.get_text(separator=" ", strip=True).lower()
            if text:
                first_paragraphs.append(text)
        if len(first_paragraphs) >= 3:
            break
    head_text = " ".join(first_paragraphs)
    head_text_short = head_text[:2000]  # only check the lead, not the whole article
    wrestling_keywords = (
        "professional wrestling", "professional wrestler", "wrestling promotion",
        "pro wrestling", "wrestling event", "pay-per-view",
        "wrestling federation", "pro-wrestling", "wrestling-related",
        "luchador", "lucha libre", "puroresu",
    )
    if any(kw in head_text_short for kw in wrestling_keywords):
        return True

    # 2. Check categories at the page footer.
    cat_links = soup.find_all("a", href=re.compile(r"^/wiki/Category:"))
    cat_text = " ".join(a.get_text(" ", strip=True).lower() for a in cat_links[:40])
    if any(kw in cat_text for kw in ("wrestling", "wrestler", "lucha libre", "puroresu")):
        return True

    return False


def _subject_is_wrestling_promotion(soup: BeautifulSoup, article_title: Optional[str] = None) -> bool:
    """
    Stricter check: the article's FIRST SENTENCE must describe ITS OWN
    SUBJECT as a wrestling promotion.

    Two-part test:
      1. The first sentence contains a promotion keyword pattern.
      2. The article's title (its <b> opener) appears in the first sentence.

    Without #2, articles like "WWE action figures" would slip through —
    that page's first sentence describes WWE (the parent) as a promotion,
    but the article's subject is action figures, not WWE itself.
    """
    body = soup.find("div", class_=re.compile(r"mw-parser-output"))
    if body is None:
        return False

    promotion_subject_patterns = (
        "wrestling promotion",
        "professional wrestling organization",
        "pro wrestling organization",
        "wrestling federation",
        "lucha libre promotion",
        "puroresu promotion",
    )

    for child in body.children:
        name = getattr(child, "name", None)
        if name != "p":
            continue
        text = child.get_text(separator=" ", strip=True)
        if len(text) < 30:
            continue

        first_sentence_raw = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
        first_sentence = first_sentence_raw.lower()
        if len(first_sentence) < 30:
            continue

        # Part 1: keyword check.
        if not any(p in first_sentence for p in promotion_subject_patterns):
            return False

        # Part 2: article-title sub-topic check. Reject articles whose
        # title indicates a sub-topic of a promotion rather than the
        # promotion itself ("WWE action figures", "WWE video games", etc.).
        # We deliberately only look at the article_title here, not at the
        # bold text — real promotion names contain "Championship" (WCW =
        # "World Championship Wrestling") so we can't use that word as a
        # blocklist marker.
        sub_topic_markers = (
            "action figure", "video game", "video games", "merchandise",
            "title history", "championship history", "list of",
            "trademark", "discography", "filmography", "broadcasters",
            "pay-per-view", " roster",
        )
        if article_title:
            t = article_title.lower()
            if any(marker in t for marker in sub_topic_markers):
                return False

        return True

    return False


def classify_html(raw_html: str, article_title: Optional[str] = None) -> Optional[str]:
    """
    Inspect a Wikipedia HTML page and return one of:
      "wrestler" | "event" | "venue" | "promotion" | None

    Returns None when the page doesn't look like any of our four supported
    entity types, when the signal is ambiguous, or when the article isn't
    actually about professional wrestling.
    """
    if not raw_html:
        return None

    soup = BeautifulSoup(raw_html, "lxml")

    # Wrestling-relevance gate: skip articles that aren't about wrestling
    # even if their infobox shape looks promotion/event/venue-like.
    if not _is_wrestling_relevant(soup):
        return None

    infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
    if not infobox:
        return None
    for noisy in infobox.find_all(["sup", "style", "script"]):
        noisy.decompose()

    # Collect lower-cased labels from infobox rows. Wikipedia uses non-
    # breaking spaces between words in some templates (e.g. "Ring\xa0name(s)",
    # "Trained\xa0by"); normalise those to regular space before matching.
    labels: set[str] = set()
    for row in infobox.find_all("tr"):
        th = row.find("th")
        if th:
            label = th.get_text(separator=" ", strip=True).lower()
            label = label.rstrip(":")
            label = re.sub(r"\s+", " ", label.replace("\xa0", " ")).strip()
            if label:
                labels.add(label)

    # Score each candidate type by label overlap.
    scores = {
        "wrestler": sum(1 for label in labels if label in WRESTLER_LABELS),
        "event":    sum(1 for label in labels if label in EVENT_LABELS),
        "venue":    sum(1 for label in labels if label in VENUE_LABELS),
        "promotion": sum(1 for label in labels if label in PROMOTION_LABELS),
    }
    top_type, top_score = max(scores.items(), key=lambda kv: kv[1])

    # Need at least 2 strong indicators to commit a classification — a single
    # "promotion" label (which event pages also have) shouldn't classify as
    # event by itself.
    if top_score < 2:
        return None

    # Ambiguity check: if two types tie or are within 1 point AND the runner-up
    # is itself >= 2, refuse to classify.
    ranked = sorted(scores.values(), reverse=True)
    if len(ranked) >= 2 and ranked[1] >= 2 and (ranked[0] - ranked[1]) < 2:
        # Special-case: events have "Promotion" + sometimes a venue label.
        # Disambiguate via the strongest single signal — "Tagline" is event-only,
        # "Capacity" is venue-only, "Trained by" is wrestler-only,
        # "Founded" is promotion-only.
        if "tagline" in labels or "ppvchron" in labels or "buyrate" in labels:
            return "event"
        if "capacity" in labels or "owner" in labels:
            return "venue"
        if "trained by" in labels or "real name" in labels or "birth name" in labels:
            return "wrestler"
        if "founded" in labels or "headquarters" in labels:
            top_type = "promotion"
        else:
            return None  # still ambiguous

    # Promotion-subject check: when classified as promotion, require the
    # article to actually describe its subject as a wrestling promotion.
    # Catches wrestling-adjacent entities (TKO Group Holdings, WWE Studios)
    # that pass the wrestling-relevance gate but aren't promotions themselves.
    if top_type == "promotion":
        if not _subject_is_wrestling_promotion(soup, article_title=article_title):
            return None

    return top_type
