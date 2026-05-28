"""
Wikimedia Commons adapter — fetch image URLs for entities via Wikidata P18.

Commons hosts the canonical free-license images for most Wikipedia subjects.
Wikidata's P18 property links an entity (by QID) to its representative
Commons file. We follow that chain:

    entity name -> Wikipedia title -> Wikidata QID -> P18 filename
                                                  -> Commons file URL

The Commons URL is the stable redirector:

    https://commons.wikimedia.org/wiki/Special:FilePath/<filename>?width=N

That endpoint returns the actual image bytes (or 302s to them), so we can
also build a thumbnail URL at any width.

Accuracy guarantee:
    Every image URL is recorded as a FieldProvenance row pointing back to
    the Wikidata claim. We never invent image URLs or guess from search.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote
from urllib.request import Request, urlopen

from .wikidata import (
    USER_AGENT, WIKIDATA_ENTITY_URL,
    resolve_qid_for_wikipedia_title,
)

logger = logging.getLogger(__name__)


COMMONS_FILEPATH_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_FILE_PAGE = "https://commons.wikimedia.org/wiki/File:{filename}"

P_IMAGE = "P18"
P_LOGO = "P154"        # used for promotion logos
P_SIGNATURE = "P109"   # signatures (occasionally useful)


# Whitelist of licenses we can legally use on a public commercial-ish site.
# Anything OUTSIDE this set must be refused — including all NonCommercial
# (NC), NoDerivs (ND), and any "fair use" / "non-free" Wikipedia uploads.
#
# Maps the raw `License` metadata key (lowercase) to our canonical short
# code stored in `image_license` on the entity.
ALLOWED_LICENSES = {
    # Public domain / CC0
    "pd":                "pd",
    "public domain":     "pd",
    "public-domain":     "pd",
    "publicdomain":      "pd",
    "cc0":               "cc0",
    "cc-zero":           "cc0",
    "cczero":            "cc0",
    # CC-BY family (attribution required, commercial use OK)
    "cc-by-1.0":         "cc-by",
    "cc-by-2.0":         "cc-by",
    "cc-by-2.5":         "cc-by",
    "cc-by-3.0":         "cc-by",
    "cc-by-3.0-us":      "cc-by",
    "cc-by-4.0":         "cc-by",
    # CC-BY-SA family (attribution + share-alike)
    "cc-by-sa-1.0":      "cc-by-sa",
    "cc-by-sa-2.0":      "cc-by-sa",
    "cc-by-sa-2.5":      "cc-by-sa",
    "cc-by-sa-3.0":      "cc-by-sa",
    "cc-by-sa-3.0-us":   "cc-by-sa",
    "cc-by-sa-4.0":      "cc-by-sa",
}


# Licenses that LOOK like CC but include restrictions we cannot honor.
EXPLICITLY_BLOCKED_LICENSES = {
    "cc-by-nc",     # NonCommercial
    "cc-by-nc-sa",
    "cc-by-nc-nd",
    "cc-by-nd",     # NoDerivs (we resize/crop, so we make derivatives)
    "cc-by-nd-nc",
    "non-free",
    "fair-use",
    "fair use",
}


def _http_get_json(url: str, timeout: float = 10.0) -> Optional[dict]:
    try:
        req = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug("Commons HTTP failure for %s: %s", url, e)
        return None


def _extract_first_filename(entity: dict, prop: str) -> Optional[str]:
    """Pull the first datavalue.value (a filename string) for a given property."""
    if not entity:
        return None
    claims = entity.get("claims", {}) or {}
    rows = claims.get(prop) or []
    for row in rows:
        mainsnak = row.get("mainsnak", {}) or {}
        if mainsnak.get("snaktype") != "value":
            continue
        dv = mainsnak.get("datavalue", {}) or {}
        v = dv.get("value")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def commons_url_for_filename(filename: str, width: Optional[int] = None) -> str:
    """Build a Commons FilePath URL (optionally with thumbnail width)."""
    if not filename:
        return ""
    # Strip a leading "File:" prefix if present.
    if filename.lower().startswith("file:"):
        filename = filename.split(":", 1)[1]
    # Commons stores filenames with underscores, but Special:FilePath accepts
    # spaces too. URL-encode to be safe.
    url = COMMONS_FILEPATH_URL.format(filename=quote(filename))
    if width and width > 0:
        url += f"?width={int(width)}"
    return url


def fetch_image_for_qid(qid: str, prop: str = P_IMAGE) -> Optional[dict]:
    """
    Resolve a Wikidata QID to a Commons image URL.

    Returns a dict with:
        qid:        the input QID
        filename:   the raw Commons filename (e.g. 'Bret Hart 2009.jpg')
        url:        full-resolution Commons URL
        thumb_url:  400px-wide thumbnail URL
        property:   which Wikidata property was followed (P18, P154, P109)

    Returns None if the QID has no claim for `prop`.
    """
    if not qid:
        return None
    entity_url = WIKIDATA_ENTITY_URL.format(qid=qid)
    data = _http_get_json(entity_url)
    if not data:
        return None
    entity = (data.get("entities") or {}).get(qid)
    if not entity:
        return None
    filename = _extract_first_filename(entity, prop)
    if not filename:
        return None
    return {
        "qid": qid,
        "filename": filename,
        "url": commons_url_for_filename(filename),
        "thumb_url": commons_url_for_filename(filename, width=400),
        "property": prop,
    }


def fetch_image_for_wikipedia_title(
    title: str, prop: str = P_IMAGE,
) -> Optional[dict]:
    """
    End-to-end helper: Wikipedia title -> QID -> Commons image URL.
    Returns same dict shape as `fetch_image_for_qid`, plus 'wikipedia_title'.
    """
    qid = resolve_qid_for_wikipedia_title(title)
    if not qid:
        return None
    out = fetch_image_for_qid(qid, prop=prop)
    if out is None:
        return None
    out["wikipedia_title"] = title
    return out


# ---------------------------------------------------------------- metadata


import html as _html
import re as _re
import urllib.parse as _urlparse


def _strip_html(s: str) -> str:
    """Strip HTML tags from a Commons metadata field — keeps the text content."""
    if not s:
        return ""
    out = _re.sub(r"<[^>]+>", "", s)
    return _html.unescape(out).strip()


def _normalize_license(license_str: str) -> str:
    """
    Return our canonical license code (or '' if not allowed).

    Accepts Commons' raw `License` metadata values like 'cc-by-sa-3.0'
    or 'CC BY 4.0' or 'PD' and maps them through `ALLOWED_LICENSES`.

    Matching is strict: exact match against ALLOWED_LICENSES, or exact
    match after a small set of safe regional/version suffixes ('-us',
    '-au', etc.) are trimmed. The previous prefix-match would approve
    strings like 'cc-by-3.0-bogus-restriction' as plain 'cc-by'; with
    "100% accuracy first" we'd rather reject and re-check than risk a
    forgery.
    """
    if not license_str:
        return ""
    raw = license_str.strip().lower()
    # Normalise spaces + 'CC BY-SA 3.0' → 'cc-by-sa-3.0'.
    norm = raw.replace(" ", "-").replace("_", "-")
    norm = _re.sub(r"-+", "-", norm)
    if norm in EXPLICITLY_BLOCKED_LICENSES:
        return ""
    # Cheap belt-and-braces: if any blocked token appears as a hyphen-
    # delimited segment (e.g. "cc-by-nc-4.0" → segments include "nc"),
    # refuse. This guards against weird upstream formats Commons might
    # one day emit.
    segments = set(norm.split("-"))
    if segments & {"nc", "nd", "non", "fair"}:
        return ""
    if norm in ALLOWED_LICENSES:
        return ALLOWED_LICENSES[norm]
    # Trim known regional / port suffixes (.0-us, .0-au, etc.) and retry
    # exact match. We deliberately do NOT do open-ended prefix matching.
    SAFE_SUFFIXES = (
        "-us", "-au", "-ca", "-uk", "-de", "-fr", "-jp", "-nl", "-es",
    )
    for suf in SAFE_SUFFIXES:
        if norm.endswith(suf):
            trimmed = norm[: -len(suf)]
            if trimmed in ALLOWED_LICENSES:
                return ALLOWED_LICENSES[trimmed]
    return ""


@dataclass
class CommonsImageMeta:
    """Normalized metadata for one Commons file."""
    filename: str
    original_url: str
    thumb_url_400: str
    file_page_url: str
    width: int
    height: int
    size_bytes: int
    mime: str

    # License + legal
    license_code: str            # our canonical: cc0/cc-by/cc-by-sa/pd or ''
    license_short: str           # 'CC BY-SA 3.0' for display
    license_url: str             # CC's deed URL
    usage_terms: str
    attribution_required: bool
    artist: str                  # human-readable author (HTML-stripped)
    credit: str                  # 'Own work', or the source page
    permission: str

    # Content
    description: str
    categories: list[str]
    restrictions: str            # any extra restrictions (rare)

    # Audit signals
    is_allowed: bool             # True iff license_code in our whitelist AND not blocked
    rejection_reason: str        # populated iff is_allowed=False

    def attribution_string(self) -> str:
        """
        Build the legal-attribution text to display.

        Format (per Creative Commons best practice):
          '<author> — <license_short> via Wikimedia Commons'
        """
        author = self.artist or "Unknown author"
        lic = self.license_short or self.license_code.upper()
        return f"{author} — {lic} via Wikimedia Commons" if lic else author


def fetch_image_metadata(filename: str) -> Optional[CommonsImageMeta]:
    """
    Pull the full Commons metadata for one file. Returns a populated
    `CommonsImageMeta`, or None on network/parse failure.

    The returned object includes a precomputed `is_allowed` boolean —
    callers should refuse to use any image where this is False.
    """
    if not filename:
        return None
    if filename.lower().startswith("file:"):
        filename = filename.split(":", 1)[1]

    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iimetadataversion": "2",
        "format": "json",
        "formatversion": "2",
    }
    url = COMMONS_API + "?" + _urlparse.urlencode(params)
    data = _http_get_json(url, timeout=15)
    if not data:
        return None
    try:
        page = data["query"]["pages"][0]
        info = page["imageinfo"][0]
    except (KeyError, IndexError, TypeError):
        return None

    em = info.get("extmetadata", {}) or {}
    def _v(key: str) -> str:
        node = em.get(key) or {}
        return _strip_html(node.get("value", "")) if isinstance(node, dict) else ""

    raw_license = _v("License")
    license_code = _normalize_license(raw_license)
    license_short = _v("LicenseShortName")

    # Failure modes — refuse if anything looks wrong. We compare against
    # the *normalised* form here so e.g. "CC BY-NC 4.0" (spaces) is
    # caught the same as "cc-by-nc-4.0".
    _norm_raw = (
        _re.sub(r"-+", "-",
                raw_license.strip().lower().replace(" ", "-").replace("_", "-"))
        if raw_license else ""
    )
    rejection: str = ""
    if not raw_license:
        rejection = "No License field in Commons metadata"
    elif _norm_raw in EXPLICITLY_BLOCKED_LICENSES:
        rejection = f"License {raw_license!r} is explicitly blocked (NC/ND/non-free)"
    elif not license_code:
        rejection = f"License {raw_license!r} not in OWDB allow-list"

    restrictions = _v("Restrictions")
    if restrictions and "trademarked" not in restrictions.lower():
        # Trademark notes are fine; other restrictions are warning signs.
        rejection = rejection or f"Restrictions noted: {restrictions[:80]}"

    return CommonsImageMeta(
        filename=filename,
        original_url=(info.get("url") or "")[:1000],
        thumb_url_400=commons_url_for_filename(filename, width=400),
        file_page_url=COMMONS_FILE_PAGE.format(filename=_urlparse.quote(filename)),
        width=int(info.get("width") or 0),
        height=int(info.get("height") or 0),
        size_bytes=int(info.get("size") or 0),
        mime=info.get("mime", "") or "",
        license_code=license_code,
        license_short=license_short,
        license_url=_v("LicenseUrl"),
        usage_terms=_v("UsageTerms"),
        attribution_required=_v("AttributionRequired").lower() == "true",
        artist=_v("Artist"),
        credit=_v("Credit"),
        permission=_v("Permission"),
        description=_v("ImageDescription")[:1000],
        categories=[c.strip() for c in _v("Categories").split("|") if c.strip()],
        restrictions=restrictions,
        is_allowed=(rejection == ""),
        rejection_reason=rejection,
    )


# ===========================================================================
# Candidate generators — for cascading image discovery (Lever 1).
#
# `fetch_image_for_qid` (above) gets us exactly one filename from P18. That's
# fine when P18 is set and points at a usable file, but covers ~10% of our
# wrestlers. The functions below expand the candidate pool dramatically:
#
#   resolve_commons_category_for_qid(qid)
#       → Wikidata P373 ("Commons category"), e.g. "Bret Hart". Most notable
#         wrestlers have a curated category with multiple usable images.
#
#   fetch_commons_category_files(category)
#       → enumerate every file in that category.
#
#   fetch_wikipedia_body_image_filenames(title)
#       → enumerate every image embedded in the Wikipedia article body
#         (not just the infobox).
#
# Each generator returns plain filenames; the calling code (pipeline/images.py)
# wraps them in `ImageCandidate` objects, assigns identity_confidence based on
# WHICH generator yielded them, and feeds them through the legal-use gate.
# ===========================================================================


P_COMMONS_CATEGORY = "P373"
WIKIPEDIA_PAGE_IMAGES_API = (
    "https://en.wikipedia.org/w/api.php"
    "?action=query&prop=images&imlimit=200&titles={title}&format=json"
)


def resolve_commons_category_for_qid(qid: str) -> Optional[str]:
    """
    Look up a Wikidata entity's Commons category (P373).

    Returns the category name (without the 'Category:' prefix), e.g.
    'Bret Hart'. Returns None if the entity has no P373 claim — which
    is fine; many wrestlers don't have a curated category, and the
    cascade simply moves on to other candidate sources.

    We deliberately do NOT fall back to sitelinks here — sitelinks to
    commonswiki are sometimes the wrestler's *talk page* or a redirect
    chain, and we want to avoid surfacing accidental matches.
    """
    if not qid:
        return None
    entity_url = WIKIDATA_ENTITY_URL.format(qid=qid)
    data = _http_get_json(entity_url)
    if not data:
        return None
    entity = (data.get("entities") or {}).get(qid)
    if not entity:
        return None
    name = _extract_first_filename(entity, P_COMMONS_CATEGORY)
    if not name:
        return None
    # Strip any leading 'Category:' just in case.
    if name.lower().startswith("category:"):
        name = name.split(":", 1)[1]
    return name.strip()


def fetch_commons_category_files(
    category: str, *, limit: int = 50,
) -> list[str]:
    """
    Enumerate every File: member of a Commons category.

    Returns a list of filenames (without 'File:' prefix), in the order
    Commons returns them (which is roughly upload-date descending — fresh
    photos surface first, which is usually what we want for currently
    active wrestlers).

    The cap defaults to 50. A 5,000-image category like 'WWE wrestlers'
    is too broad to be useful for a single-wrestler lookup; the caller
    is expected to pass the wrestler-specific category like 'Bret Hart',
    where 50 covers the entire archive.
    """
    if not category:
        return []
    if category.lower().startswith("category:"):
        category = category.split(":", 1)[1]
    cm_title = "Category:" + category
    url = (
        COMMONS_API
        + "?action=query&list=categorymembers"
        + f"&cmtitle={_urlparse.quote(cm_title)}"
        + "&cmtype=file"
        + f"&cmlimit={max(1, min(int(limit), 500))}"
        + "&format=json&formatversion=2"
    )
    data = _http_get_json(url, timeout=15)
    if not data:
        return []
    try:
        members = data["query"]["categorymembers"]
    except (KeyError, TypeError):
        return []

    out: list[str] = []
    for m in members:
        title = (m.get("title") or "").strip()
        if not title.lower().startswith("file:"):
            continue
        fname = title.split(":", 1)[1].strip()
        if not fname:
            continue
        # Skip non-image extensions — Commons categories can contain SVGs,
        # OGG audio, PDFs, etc. We accept the common image types here so
        # the caller doesn't waste an API call on a clearly-wrong file.
        lower = fname.lower()
        if not any(lower.endswith(ext) for ext in (
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".tif",
        )):
            continue
        out.append(fname)
    return out


def fetch_wikipedia_body_image_filenames(
    title: str, *, limit: int = 30,
) -> list[str]:
    """
    Enumerate every image embedded in a Wikipedia article (lead + body).

    Returns Commons filenames (without the 'File:' prefix). The Wikipedia
    API `prop=images` lists every image transcluded into the page,
    including the infobox image and any in-line photos. The order is
    roughly the order they appear in the article.

    Caller filters with identity verification (filename match,
    category membership, description text) before trusting any hit.
    """
    if not title:
        return []
    url = WIKIPEDIA_PAGE_IMAGES_API.format(title=_urlparse.quote(title))
    data = _http_get_json(url)
    if not data:
        return []
    pages = (data.get("query") or {}).get("pages") or {}
    out: list[str] = []
    for _, page in pages.items():
        for entry in (page.get("images") or []):
            t = (entry.get("title") or "").strip()
            if not t.lower().startswith("file:"):
                continue
            fname = t.split(":", 1)[1].strip()
            if not fname:
                continue
            # Same image-extension filter as the category enumerator —
            # avoids burning a metadata call on Edit-pencil-blue.svg etc.
            lower = fname.lower()
            if not any(lower.endswith(ext) for ext in (
                ".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".tif",
            )):
                continue
            # Wikipedia chrome appears on every page — skip the
            # well-known ornamental files so we don't waste API calls.
            if _is_chrome_filename(fname):
                continue
            out.append(fname)
            if len(out) >= limit:
                break
    return out


# Wikipedia-chrome filenames that appear on essentially every article.
# We blacklist them so the body-image enumerator doesn't waste a metadata
# round-trip — these never depict the subject.
_WIKIPEDIA_CHROME_FILENAMES = {
    "Commons-logo.svg", "Wiki letter w.svg", "Wiki letter w cropped.svg",
    "Question book-new.svg", "Editing icon.svg", "Edit-clear.svg",
    "Symbol category class.svg", "Symbol portal class.svg",
    "Symbol star silver.svg",
}


def _is_chrome_filename(fname: str) -> bool:
    return fname.strip() in _WIKIPEDIA_CHROME_FILENAMES


# --------------------------------------------------------- identity scoring


def _normalize_for_match(s: str) -> str:
    """Strip punctuation/extension, lowercase, collapse whitespace."""
    if not s:
        return ""
    s = s.strip()
    # Drop file extension.
    if "." in s:
        s = s.rsplit(".", 1)[0]
    # Replace separators with spaces.
    s = s.replace("_", " ").replace("-", " ")
    # Drop trailing date-style numbers.
    s = _re.sub(r"\b(19|20)\d{2}\b", " ", s)
    # Drop punctuation.
    s = _re.sub(r"[^A-Za-z\s]", " ", s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s


def filename_mentions_name(filename: str, wrestler_name: str) -> bool:
    """
    True iff the (normalized) filename matches the wrestler name with
    word-boundary confidence — never via raw substring on a short name.

    Used by the identity scorer to bump a Commons-category hit from
    confidence 85 (in-category) to 95 (in-category AND name-matched),
    and a Wikipedia-body candidate from 60 to 75.

    Three accept paths:
      1. Full normalized name appears as a contiguous run of whole
         tokens in the filename ("bret hart" inside "bret hart 2009").
      2. Last name appears as a whole token AND at least one OTHER name
         token also appears as a whole token (catches "Hart family with
         Bret"; rejects "Hart family with Owen").
      3. Single-token names require an EXACT whole-token match — never
         a substring. Otherwise "Edge" → "edge" would match
         "ledger.jpg", and "2point0" → "point" matches "three points".
         This is the bug that put a "3.0 Three Points" photo on the
         2point0 tag-team page in the first batch.

    Multi-token short last names (e.g. "Hart") still rely on path #2
    requiring another corroborating token, so the Hart-family Commons
    category can't conflate Bret / Owen / Stu.
    """
    nf = _normalize_for_match(filename)
    nw = _normalize_for_match(wrestler_name)
    if not nf or not nw:
        return False

    nf_tokens = nf.split()
    nf_token_set = set(nf_tokens)
    nw_tokens = nw.split()
    if not nw_tokens:
        return False

    # Path 3 — single-token name. Require an EXACT whole-token match in
    # the filename. Substring match here is the dangerous case ("edge"
    # in "ledger", "point" in "points").
    if len(nw_tokens) == 1:
        return nw_tokens[0] in nf_token_set

    # Path 1 — full normalized name appears as a contiguous run of
    # tokens in the filename.
    name_run = nw  # already space-normalized
    # Join filename tokens with single spaces and look for the full name
    # as a substring of that joined string. Since both sides are
    # whitespace-normalized, this matches token boundaries.
    if (" " + name_run + " ") in (" " + " ".join(nf_tokens) + " "):
        return True

    # Path 2 — last name as a whole token + at least one other name
    # token also present as a whole token.
    last_name = nw_tokens[-1]
    other_tokens = set(nw_tokens[:-1])
    if last_name in nf_token_set and (other_tokens & nf_token_set):
        return True
    return False


def description_mentions_name(description: str, wrestler_name: str) -> bool:
    """
    True iff the Commons image description contains the wrestler's name.

    Two accept paths, in order:
      1. The raw (lowercased) wrestler name appears as a substring of
         the raw (lowercased) description. This preserves digits and
         punctuation, so "2point0" inside "members of 2point0" matches
         legitimately. This is the cleanest signal.
      2. The normalized name appears in the normalized description —
         but for single-token normalized names we require a whole-word
         match (same defense as `filename_mentions_name`). Otherwise
         a wrestler named "Edge" (normalized: "edge") would be matched
         by descriptions mentioning "ledger" or "edging".
    """
    if not description or not wrestler_name:
        return False
    # Path 1: raw name in raw description.
    if wrestler_name.strip().lower() in description.lower():
        return True
    # Path 2: normalized fallback.
    nd = _normalize_for_match(description)
    nw = _normalize_for_match(wrestler_name)
    if not nw or not nd:
        return False
    nw_tokens = nw.split()
    if len(nw_tokens) == 1:
        # Single-token normalized name → require whole-word match.
        return nw_tokens[0] in set(nd.split())
    # Multi-token name → substring (already aligned to word boundaries
    # in practice because both sides are space-normalized).
    return nw in nd


def categories_contain(meta_categories: list[str], category_name: str) -> bool:
    """
    True iff the Commons file's `categories` list contains `category_name`
    (case-insensitive, with or without 'Category:' prefix).
    """
    target = category_name.strip()
    if target.lower().startswith("category:"):
        target = target.split(":", 1)[1]
    target_l = target.lower()
    for c in meta_categories or []:
        c = c.strip()
        if c.lower().startswith("category:"):
            c = c.split(":", 1)[1]
        if c.lower() == target_l:
            return True
    return False


if __name__ == "__main__":  # pragma: no cover
    import sys
    name = " ".join(sys.argv[1:]) or "Bret Hart"
    r = fetch_image_for_wikipedia_title(name)
    if not r:
        print(f"no P18 image for {name!r}")
    else:
        meta = fetch_image_metadata(r["filename"])
        print(json.dumps({"p18_lookup": r, "metadata": meta.__dict__ if meta else None},
                          indent=2, default=str))
    # Show the cascade reach too.
    qid = resolve_qid_for_wikipedia_title(name)
    if qid:
        cat = resolve_commons_category_for_qid(qid)
        print(f"\nCommons category for {qid}: {cat or '(none)'}")
        if cat:
            files = fetch_commons_category_files(cat, limit=10)
            print(f"  first {len(files)} files: {files}")
    body = fetch_wikipedia_body_image_filenames(name, limit=10)
    print(f"\nWikipedia body images for {name!r}: {len(body)} found")
    for f in body[:10]:
        print(f"  - {f}")
