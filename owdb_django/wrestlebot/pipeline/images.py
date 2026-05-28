"""
Image assignment pipeline with accuracy + legal-use gates.

Architecture (post-cascade):

  find_image_candidates(entity, entity_type)
      → generator yielding (filename, source_path, identity_confidence)
        in priority order, best first.
  assign_image_to_entity(entity, entity_type=…)
      → walks the cascade, applies legal + identity + dimension gates,
        persists the first candidate that passes, returns ImageAssignment.

Candidate sources, in priority order:

  P18 (Wikidata "image")             — identity confidence 100
      Structurally guaranteed: a curator manually attached this file to
      this entity in Wikidata. Same path the old single-shot extractor
      used. Most narrowly-applicable but highest signal.

  P109/P154 (signature/logo)         — identity confidence 100
      For promotions and titles where the appropriate Wikidata property
      is something other than P18.

  P373 Commons category              — confidence 85, or 95 with filename match
      Most notable wrestlers have a curated 'Category:<Name>' on Commons
      with dozens of files. We enumerate the category and treat any file
      in it as plausibly depicting the subject; bump confidence to 95 when
      the filename itself also mentions the wrestler's name.

  Wikipedia body images              — confidence 75 with strong identity, 60 otherwise
      Every image embedded in the Wikipedia article body. These are
      lower-confidence because Wikipedia articles often illustrate
      OPPONENTS of the subject too ("Bret Hart wrestling Shawn Michaels");
      we require either filename or description to mention the subject.

Legal-use gate (unchanged from the prior single-shot path):
  * License must normalise to one of {cc0, pd, cc-by, cc-by-sa}.
  * Dimensions ≥ entity-type minimum (with first-fill relaxation when
    entity has no image yet).
  * Attribution required when license demands it.
  * MIME must be image/*.

Anyone who wants to assign an image MUST use `assign_image_to_entity()`.
Direct writes to entity.image_url bypass the legal-compliance gate and
will be caught by Earl's `image_without_license` rule on the next audit.
"""

from __future__ import annotations

import logging
import re as _re
from dataclasses import asdict, dataclass, field
from typing import Iterator, Optional

from django.utils import timezone

from ..sources.commons import (
    P_IMAGE, P_LOGO, P_SIGNATURE,
    CommonsImageMeta,
    categories_contain,
    description_mentions_name,
    fetch_commons_category_files,
    fetch_image_for_qid,
    fetch_image_metadata,
    fetch_wikipedia_body_image_filenames,
    filename_mentions_name,
    resolve_commons_category_for_qid,
)
from ..sources.wikidata import resolve_qid_for_wikipedia_title
from ._provenance import record_provenance

logger = logging.getLogger(__name__)


# Per-entity-type config: Wikidata property + dimension floors.
#
# `min_dim` is the floor that ALWAYS applies — used when replacing an
# existing image with a better one, so we don't downgrade quality.
#
# `min_dim_first_fill` is the relaxed floor that applies ONLY when the
# entity has no image yet. The intuition: a 150 px photo of a 1970s
# territory wrestler is genuinely the best image that exists for them,
# and is far better than nothing.  Once we have any image, the regular
# floor kicks in so we don't downgrade quality on replacement.
ENTITY_IMAGE_PROPS = {
    "wrestler":   {"prop": P_IMAGE,  "min_dim": 200, "min_dim_first_fill": 120},
    "promotion":  {"prop": P_LOGO,   "min_dim": 100, "min_dim_first_fill": 80},
    "title":      {"prop": P_IMAGE,  "min_dim": 100, "min_dim_first_fill": 80},
    "venue":      {"prop": P_IMAGE,  "min_dim": 300, "min_dim_first_fill": 200},
    "event":      {"prop": P_IMAGE,  "min_dim": 200, "min_dim_first_fill": 150},
    "stable":     {"prop": P_LOGO,   "min_dim": 100, "min_dim_first_fill": 80},
    "tv_show":    {"prop": P_LOGO,   "min_dim": 100, "min_dim_first_fill": 80},
    # Cover art on a Wikipedia article uses P18 (image) — same as
    # wrestlers. Covers tend to be small thumbnails on Commons (often
    # 200-400px); use the relaxed first-fill floor so we don't reject
    # legitimate covers for being modest in size.
    "video_game": {"prop": P_IMAGE,  "min_dim": 200, "min_dim_first_fill": 150},
    "book":       {"prop": P_IMAGE,  "min_dim": 200, "min_dim_first_fill": 150},
}


# Identity-confidence thresholds for accepting a candidate. We refuse
# anything below this score regardless of license — better to leave the
# slot empty than ship the wrong person's photo.
MIN_IDENTITY_CONFIDENCE = {
    "wrestler":   75,
    "promotion":  60,  # promotion logos are fungible (just need the right org)
    "title":      60,
    "venue":      70,
    "event":      75,
    "stable":     70,
    "tv_show":    60,
    # Covers carry the game/book TITLE as part of the design — filename
    # match is generally strong. Same floor as wrestlers because a
    # wrong-cover is a real accuracy problem (we'd be claiming THIS
    # game looks like THAT game).
    "video_game": 75,
    "book":       75,
}


# Identity-score buckets. Documented in the cascade narrative above.
IDENTITY_P18                  = 100  # Wikidata P18/P154/P109 — curator-attached
IDENTITY_COMMONS_CAT_NAMED    = 95   # in Commons category AND filename matches
IDENTITY_COMMONS_CAT          = 85   # in Commons category, filename neutral
IDENTITY_WIKI_BODY_NAMED      = 75   # body image whose filename or desc mentions subject
IDENTITY_WIKI_BODY_WEAK       = 60   # body image without name signal — usually rejected


@dataclass
class ImageCandidate:
    """One candidate image surfaced by the cascade."""
    filename: str
    source_path: str        # "wikidata_p18", "commons_category", "wikipedia_body"
    identity_confidence: int
    # Optional context the gate uses for additional verification.
    expected_category: str = ""       # Commons category name we found this in
    wrestler_name: str = ""           # name we'll match against filename/description

    def __str__(self) -> str:
        return (
            f"{self.source_path}:{self.filename!r} "
            f"(id-conf={self.identity_confidence})"
        )


@dataclass
class ImageAssignment:
    """Result of an `assign_image_to_entity()` call."""
    success: bool
    entity_type: str
    entity_id: int
    image_url: str = ""
    image_source_url: str = ""
    image_license: str = ""
    image_credit: str = ""
    qid: str = ""
    refusal_reason: str = ""
    identity_confidence: int = 0
    source_path: str = ""              # which cascade step yielded this
    meta: Optional[CommonsImageMeta] = None
    # Diagnostic: every candidate considered + why it was rejected (if so).
    # Useful for the sweep command's per-wrestler verdict output.
    considered: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "success": self.success,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "image_url": self.image_url,
            "image_source_url": self.image_source_url,
            "image_license": self.image_license,
            "image_credit": self.image_credit,
            "qid": self.qid,
            "refusal_reason": self.refusal_reason,
            "identity_confidence": self.identity_confidence,
            "source_path": self.source_path,
            "considered": self.considered,
        }
        if self.meta:
            d["dimensions"] = f"{self.meta.width}x{self.meta.height}"
            d["size_bytes"] = self.meta.size_bytes
            d["attribution_required"] = self.meta.attribution_required
        return d


# -------------------------------------------------------- identity / title


def _entity_wikipedia_url(entity) -> Optional[str]:
    """Return the entity's Wikipedia URL if it has one."""
    return (getattr(entity, "wikipedia_url", None) or "").strip() or None


def _wikipedia_title_for(entity) -> Optional[str]:
    """
    Best-effort lookup of the Wikipedia article title for this entity.

    Order:
      1. wikipedia_url field (canonical)
      2. fall back to the entity's `name` (Wikipedia's redirect handling
         will normalize across spelling variations)
    """
    url = _entity_wikipedia_url(entity)
    if url:
        from urllib.parse import unquote
        if "/wiki/" in url:
            title = url.split("/wiki/", 1)[1].split("#")[0].split("?")[0]
            return unquote(title).replace("_", " ")
    name = getattr(entity, "name", None) or getattr(entity, "title", None)
    return name


def _entity_name(entity) -> str:
    """Return the entity's display name (Wrestler.name, Title.name, etc.)."""
    return (getattr(entity, "name", None) or getattr(entity, "title", None) or "").strip()


# -------------------------------------------------------- legal/dim gate


def _violates_minimum_dimensions(
    meta: CommonsImageMeta, min_dim: int,
) -> bool:
    if meta.width and meta.height:
        return meta.width < min_dim or meta.height < min_dim
    return False  # unknown dimensions — don't refuse on that alone


def _build_credit_string(
    meta: CommonsImageMeta, *, entity_type: str = "",
) -> str:
    """
    Attribution text + Commons file-page URL (for legal-review trail).

    For promotion-class entities, we append a nominative fair-use notice
    because the file is by definition a trademark we're using to refer
    to the trademark holder. Photo licensing (the Commons CC/PD chain)
    is separately handled by the license whitelist; trademark law gives
    a separate analysis path (15 U.S.C. § 1125 / nominative-fair-use
    doctrine — same shield Wikipedia, ESPN, and every reference DB use).

    The notice is appended to `image_credit`, which renders on every
    page that displays the image. A user (or a trademark holder's
    counsel) following the trail lands on the Commons file page + the
    explicit nominative-use claim.
    """
    base = meta.attribution_string()
    out = f"{base} ({meta.file_page_url})"
    if entity_type in ("promotion", "stable", "tv_show", "title"):
        out += " | Logo used for identification (nominative fair use)."
    return out[:500]


def _entity_already_has_image(entity) -> bool:
    return bool((getattr(entity, "image_url", None) or "").strip())


# ---------- promotional-art guard ---------------------------------------------
#
# An "events" image is the hard case for copyright. Many events have:
#   * the actual EVENT POSTER / KEYART — a copyrighted promotional design
#     (e.g. the WrestleMania XL poster). These are usually uploaded to
#     Wikipedia under "non-free media" claims, which our license gate
#     already refuses. But occasionally an event's poster gets re-uploaded
#     to Commons by someone who confused the licenses, or a photographer
#     shoots the poster on a billboard, uploads the photo as CC-BY-SA,
#     and the photo IS legitimately CC-BY-SA — but the poster INSIDE is
#     still copyright-protected. Third-party reuse there is dicey.
#
# This filter catches the latter case. It refuses files where the
# filename, description, or Commons categories signal that the primary
# subject of the image IS a promotional artwork piece. Plain photos of
# the arena, the venue, the crowd, or in-ring action remain accepted.

# Single-word tokens we tokenise the filename / description into. Multi-word
# phrases below run a plain substring check against the normalised text.
_PROMO_ART_SINGLE_WORD_TOKENS = (
    "poster", "keyart", "presskit", "promotional", "advertisement",
    "billboard", "wallpaper",
)

_PROMO_ART_FILENAME_SUBSTRINGS = (
    "key art", "press kit", "promo art", "movie poster", "film poster",
    # Round-2 codex/claude fix: book and video-game cover photographs
    # are usually CC-licensed by the photographer but the cover design
    # underneath is still copyrighted by the publisher / game studio.
    "box art", "cover art", "dust jacket", "book cover", "video game cover",
    "game cover", "boxart", "coverart",
)

_PROMO_ART_DESCRIPTION_PHRASES = (
    "promotional poster", "promotional artwork", "press kit",
    "official poster", "event poster", "ppv poster",
    "promotional artwork for", "promotional material",
    "movie poster", "film poster", "show poster", "wallpaper for",
    "the poster for", "poster for the",
    # Cover-art phrases for book/game guard.
    "book cover", "dust jacket", "box art", "cover art",
    "video game cover", "game cover", "official cover",
    "the cover of", "cover of the",
)

_PROMO_ART_CATEGORY_TOKENS = (
    "posters", "advertisement", "advertisements", "billboards",
    "promotional material", "press kits", "wallpapers", "keyart",
    # Cover-art categories on Commons.
    "book covers", "video game covers", "box art", "album covers",
    "dust jackets",
)

_WORD_RE = _re.compile(r"[A-Za-z0-9]+")


def _normalise_with_word_boundaries(s: str) -> tuple[str, set[str]]:
    """
    Lowercase + normalise s into (joined_text, word_set). The joined text
    preserves order with single-space separators (so multi-word phrase
    substring matches work); the word set is for cheap whole-word checks.

    File extensions, punctuation, and digits-only runs all become word
    boundaries so 'Poster_2024.jpg' tokenises to {'poster', '2024', 'jpg'}.
    """
    s = s or ""
    words = [m.group(0).lower() for m in _WORD_RE.finditer(s)]
    return " ".join(words), set(words)


def is_likely_promotional_art(meta: CommonsImageMeta) -> tuple[bool, str]:
    """
    Detect Commons files whose primary subject is a copyrighted
    promotional design (poster, key art, press kit, billboard ad).

    Returns (is_promo, reason). When True, the caller should refuse the
    candidate for `event`-class entities regardless of the photo's own
    CC license. Promotion-class entities are allowed because their use
    of a logo is the trademark itself (handled by nominative fair use);
    event-class entities use posters as a stand-in for the event, which
    has neither nominative-fair-use protection nor the Commons-photo
    license clearing the underlying poster.

    Heuristics, in order of confidence:
      1. Filename contains an unambiguous promotional-art token (whole
         word, so 'blockbuster' doesn't trip 'buster').
      2. Commons file lives in a "*posters*" / "*billboards*" /
         "promotional material" category.
      3. Description explicitly calls the file "promotional artwork",
         "official poster", "press kit", etc.
    """
    # 1. Filename: tokenise to defeat extension-sticking and punctuation.
    fname_joined, fname_words = _normalise_with_word_boundaries(meta.filename)
    for token in _PROMO_ART_SINGLE_WORD_TOKENS:
        if token in fname_words:
            return True, f"filename token {token!r} signals promotional artwork"
    for phrase in _PROMO_ART_FILENAME_SUBSTRINGS:
        if phrase in fname_joined:
            return True, f"filename phrase {phrase!r} signals promotional artwork"

    # 2. Categories — substring on lowercased category name. Multi-word
    # category tokens ("promotional material") need substring; the
    # category-name format means a whole-word match would miss
    # "Posters of WrestleMania".
    for cat in meta.categories or ():
        cat_low = (cat or "").lower()
        for token in _PROMO_ART_CATEGORY_TOKENS:
            if token in cat_low:
                return True, (
                    f"Commons category {cat!r} signals promotional artwork"
                )

    # 3. Description phrases. Use the joined-words form so periods /
    # commas don't break phrases like "official poster for".
    desc_joined, _ = _normalise_with_word_boundaries(meta.description)
    for phrase in _PROMO_ART_DESCRIPTION_PHRASES:
        if phrase in desc_joined:
            return True, (
                f"description phrase {phrase!r} signals promotional artwork"
            )

    return False, ""


# -------------------------------------------------------- cascade


def find_image_candidates(
    entity, *, entity_type: str, prop: Optional[str] = None,
) -> Iterator[ImageCandidate]:
    """
    Yield candidate images for `entity` in priority order, best first.

    The caller (assign_image_to_entity) walks this iterator and accepts
    the first candidate that passes the legal + dimension + identity
    gates. Each candidate carries an `identity_confidence` that records
    HOW we know this file depicts the subject:

      100 — Wikidata P18 (curator-attached)
       95 — in the subject's Commons category AND filename mentions them
       85 — in the subject's Commons category, filename neutral
       75 — Wikipedia body image whose filename or description names them
       60 — Wikipedia body image without name signal (usually rejected by
            the identity-confidence floor)

    The generator is lazy: each step only runs when the cascade reaches
    it. Wikidata + Commons calls go through the rate_limit module via the
    underlying HTTP helpers.
    """
    title = _wikipedia_title_for(entity)
    if not title:
        return  # no Wikipedia title, no path forward
    name = _entity_name(entity)

    # Step 1: Wikidata QID → P18 (or the entity-type-specific property).
    qid = resolve_qid_for_wikipedia_title(title)
    if not qid:
        return  # without a QID we have no identity anchor at all

    requested_prop = prop or ENTITY_IMAGE_PROPS.get(entity_type, {}).get("prop", P_IMAGE)
    p18 = fetch_image_for_qid(qid, prop=requested_prop)
    if p18:
        yield ImageCandidate(
            filename=p18["filename"],
            source_path=f"wikidata_{requested_prop.lower()}",
            identity_confidence=IDENTITY_P18,
            wrestler_name=name,
        )

    # Step 2: Commons category (P373) — enumerate every file in the
    # subject's curated category. We yield filename-matched candidates
    # FIRST so the cascade tries the most identity-verifiable ones early.
    category = resolve_commons_category_for_qid(qid)
    if category:
        files = fetch_commons_category_files(category, limit=50)
        # Sort: named files first (confidence 95), unnamed second (85).
        named, unnamed = [], []
        for fname in files:
            if filename_mentions_name(fname, name):
                named.append(fname)
            else:
                unnamed.append(fname)
        for fname in named:
            yield ImageCandidate(
                filename=fname,
                source_path="commons_category_named",
                identity_confidence=IDENTITY_COMMONS_CAT_NAMED,
                expected_category=category,
                wrestler_name=name,
            )
        for fname in unnamed:
            yield ImageCandidate(
                filename=fname,
                source_path="commons_category",
                identity_confidence=IDENTITY_COMMONS_CAT,
                expected_category=category,
                wrestler_name=name,
            )

    # Step 3: Wikipedia body images — fallback for subjects without a
    # P373 category. Lower default confidence; the gate bumps it to 75
    # once we confirm filename or description mentions the subject.
    body_files = fetch_wikipedia_body_image_filenames(title, limit=30)
    for fname in body_files:
        # Initial confidence: only bump to NAMED if the filename itself
        # mentions the subject. Description-based bump happens in the
        # gate once we have full metadata.
        if filename_mentions_name(fname, name):
            conf = IDENTITY_WIKI_BODY_NAMED
        else:
            conf = IDENTITY_WIKI_BODY_WEAK
        yield ImageCandidate(
            filename=fname,
            source_path="wikipedia_body",
            identity_confidence=conf,
            wrestler_name=name,
            # Body images don't ship with a category context, but we still
            # store the wrestler's Commons category if we found one so the
            # gate can use it as an extra verification signal.
            expected_category=category or "",
        )


def _evaluate_candidate(
    candidate: ImageCandidate,
    *,
    entity_type: str,
    min_dim: int,
) -> tuple[Optional[CommonsImageMeta], str, int]:
    """
    Apply the legal + identity + dimension gates to one candidate.

    Returns (meta, refusal_reason, final_identity_confidence).
      meta is None iff the candidate is rejected.
      refusal_reason is empty on accept, populated on reject.
      final_identity_confidence may be HIGHER than the candidate's seed
        score if the gate confirms an extra identity signal (e.g. the
        Commons description mentions the wrestler).
    """
    meta = fetch_image_metadata(candidate.filename)
    if meta is None:
        return None, f"Commons metadata unavailable for {candidate.filename!r}", 0

    # Legal gate — unchanged from the pre-cascade path.
    if not meta.is_allowed:
        return None, f"License check failed: {meta.rejection_reason}", 0

    if not meta.mime.startswith("image/"):
        return None, f"Not an image MIME: {meta.mime!r}", 0

    if _violates_minimum_dimensions(meta, min_dim):
        return None, (
            f"Image too small: {meta.width}×{meta.height} < {min_dim}px on shortest side"
        ), 0

    # Attribution gate. Round-2 fix: the literal strings 'unknown' and
    # 'anonymous' are NOT attribution under CC-BY / CC-BY-SA — they
    # signal that the uploader didn't know the author, which doesn't
    # satisfy the license's attribution requirement. Treat these as if
    # the field were empty.
    _NULL_ATTRIBUTION_STRINGS = {
        "", "unknown", "anonymous", "n/a", "na", "none",
        "no machine-readable author provided", "self-published",
    }
    artist_normalized = (meta.artist or "").strip().lower()
    if meta.attribution_required and artist_normalized in _NULL_ATTRIBUTION_STRINGS:
        return None, (
            f"License requires attribution but Artist field is "
            f"{meta.artist!r} (treated as missing)"
        ), 0

    # Promotional-art guard. Refuse files whose primary subject is a
    # copyrighted promotional design (poster, keyart, press kit, book
    # cover, game cover, box art). The photo may be CC-licensed but
    # the design / artwork underneath isn't, and using it as the entity's
    # canonical image is the use that draws cease-and-desists.
    #
    # Promotion / stable / tv_show entities are EXEMPT — for those, the
    # logo IS the entity's identifier and nominative fair use applies.
    #
    # Round-2 expansion: VG + Book covers now share this guard. Previously
    # only events were guarded, so a Commons photo of a copyrighted game
    # box could leak through for VideoGame.image_url.
    if entity_type in ("event", "video_game", "book", "special"):
        promo, reason = is_likely_promotional_art(meta)
        if promo:
            return None, f"Promotional-art guard: {reason}", 0

    # Identity verification — possibly bump the score upward if metadata
    # gives us another corroborating signal.
    final_conf = candidate.identity_confidence
    if candidate.source_path == "wikipedia_body":
        # Caption-text bump: if the Commons description mentions the
        # subject, treat this as a NAMED body image (75) even if the
        # filename didn't match.
        if description_mentions_name(meta.description, candidate.wrestler_name):
            final_conf = max(final_conf, IDENTITY_WIKI_BODY_NAMED)
        # Category-membership bump: a body image that's ALSO in the
        # subject's Commons category is essentially a category hit.
        if candidate.expected_category and categories_contain(
            meta.categories, candidate.expected_category,
        ):
            final_conf = max(final_conf, IDENTITY_COMMONS_CAT)
            if filename_mentions_name(candidate.filename, candidate.wrestler_name):
                final_conf = max(final_conf, IDENTITY_COMMONS_CAT_NAMED)

    elif candidate.source_path == "commons_category":
        # Category candidate without filename match: bump to NAMED if the
        # description mentions the subject (sometimes Commons uploaders
        # name the subject in the file description but use a generic
        # filename like "WrestleMania 2009 photo.jpg").
        if description_mentions_name(meta.description, candidate.wrestler_name):
            final_conf = max(final_conf, IDENTITY_COMMONS_CAT_NAMED)

    # Identity threshold check.
    floor = MIN_IDENTITY_CONFIDENCE.get(entity_type, 75)
    if final_conf < floor:
        return None, (
            f"Identity confidence {final_conf} below floor {floor} "
            f"for {entity_type!r}"
        ), final_conf

    return meta, "", final_conf


def _refusal(
    reason: str, *, entity_type: str, entity_id: int,
    qid: str = "", meta=None, considered: Optional[list[dict]] = None,
) -> ImageAssignment:
    return ImageAssignment(
        success=False, entity_type=entity_type, entity_id=entity_id,
        qid=qid, refusal_reason=reason, meta=meta,
        considered=considered or [],
    )


# -------------------------------------------------------- main entry point


def assign_image_to_entity(
    entity, *, entity_type: str,
    source_fetch=None,
    prop: Optional[str] = None,
    force: bool = False,
) -> ImageAssignment:
    """
    Find the best available image for `entity`, gate it through legal-use +
    identity + accuracy checks, persist it (with provenance) if it passes.

    `source_fetch` is the SourceFetch that triggered this — required so we
    can write FieldProvenance for the image fields. If omitted, we use the
    entity's most recent Wikipedia fetch.

    Returns an ImageAssignment recording the outcome — `refusal_reason` is
    populated when we refused (license, dimensions, identity, etc.), and
    `considered` lists every candidate the cascade tried so the sweep
    command can show a useful per-wrestler verdict.
    """
    from ..models import SourceFetch
    from owdb_django.owdbapp.models import ImageHistory

    entity_id = entity.id

    # Refuse to clobber an existing image unless force=True.
    if not force and _entity_already_has_image(entity):
        return _refusal(
            "Entity already has an image (pass force=True to replace)",
            entity_type=entity_type, entity_id=entity_id,
        )

    # Dimension floor: relaxed for first-fill, strict for replacement.
    cfg = ENTITY_IMAGE_PROPS.get(entity_type, {})
    if _entity_already_has_image(entity):
        min_dim = int(cfg.get("min_dim", 100))
    else:
        min_dim = int(cfg.get("min_dim_first_fill", cfg.get("min_dim", 100)))

    # Resolve QID up-front for two reasons:
    #   1) Diagnostic — the result carries qid so the sweep command can
    #      show why an entity failed.
    #   2) Pre-cascade short-circuit: if we have no title or no QID,
    #      report THAT specifically (better than a confusing "0 candidates
    #      considered" from the cascade walker).
    title = _wikipedia_title_for(entity)
    if not title:
        return _refusal(
            "No Wikipedia title available for entity",
            entity_type=entity_type, entity_id=entity_id,
        )
    qid = resolve_qid_for_wikipedia_title(title)
    if not qid:
        return _refusal(
            f"Could not resolve Wikidata QID for {title!r}",
            entity_type=entity_type, entity_id=entity_id,
        )

    considered: list[dict] = []

    # Walk the cascade.
    accepted_meta: Optional[CommonsImageMeta] = None
    accepted_candidate: Optional[ImageCandidate] = None
    accepted_conf: int = 0

    for candidate in find_image_candidates(
        entity, entity_type=entity_type, prop=prop,
    ):
        meta, reason, final_conf = _evaluate_candidate(
            candidate, entity_type=entity_type, min_dim=min_dim,
        )
        considered.append({
            "filename": candidate.filename,
            "source_path": candidate.source_path,
            "seed_confidence": candidate.identity_confidence,
            "final_confidence": final_conf,
            "accepted": meta is not None,
            "refusal_reason": reason,
        })
        if meta is not None:
            accepted_meta = meta
            accepted_candidate = candidate
            accepted_conf = final_conf
            break  # cascade rule: first passing candidate wins

    if accepted_meta is None or accepted_candidate is None:
        return _refusal(
            "No candidate image passed the cascade gates "
            f"(tried {len(considered)} candidate(s))",
            entity_type=entity_type, entity_id=entity_id,
            qid=qid or "", considered=considered,
        )

    # ----- Persist + provenance ---------------------------------------
    if not source_fetch:
        source_fetch = (SourceFetch.objects
                        .filter(entity_type=entity_type, entity_id=entity_id,
                                source="wikipedia", http_status=200)
                        .order_by("-fetched_at").first())
    if not source_fetch:
        # Fall back to a manual-backfill sentinel so provenance still has
        # something to point at. The sentinel records all the legally-
        # relevant fields from the Commons metadata.
        source_fetch, _ = SourceFetch.objects.get_or_create(
            source="wikimedia_commons",
            content_hash=f"commons_{accepted_meta.filename}"[:64],
            defaults=dict(
                url=accepted_meta.file_page_url,
                entity_type=entity_type,
                entity_id=entity_id,
                candidate_name=accepted_meta.filename[:255],
                http_status=200,
                raw_content=(
                    f"License: {accepted_meta.license_short}\n"
                    f"Artist: {accepted_meta.artist}\n"
                    f"Description: {accepted_meta.description}\n"
                    f"Source path: {accepted_candidate.source_path}\n"
                    f"Identity confidence: {accepted_conf}\n"
                )[:65_000],
            ),
        )

    credit = _build_credit_string(accepted_meta, entity_type=entity_type)

    # Archive the prior image (if any) into ImageHistory before overwriting.
    if _entity_already_has_image(entity):
        try:
            ImageHistory.archive_current_image(entity, reason="better_image_found")
        except Exception as e:
            logger.warning(
                "ImageHistory archive failed for %s#%s: %s",
                entity_type, entity_id, e,
            )

    # Write the four image fields.
    entity.image_url = accepted_meta.original_url[:500]
    entity.image_source_url = accepted_meta.file_page_url[:500]
    entity.image_original_url = accepted_meta.original_url[:500]
    entity.image_license = accepted_meta.license_code
    entity.image_credit = credit
    entity.image_fetched_at = timezone.now()
    entity.save(update_fields=[
        "image_url", "image_source_url", "image_original_url",
        "image_license", "image_credit", "image_fetched_at",
    ])

    # Provenance rows for the four legally-significant fields.
    snippet = (
        f"Commons {accepted_meta.filename} | "
        f"License: {accepted_meta.license_short or accepted_meta.license_code} | "
        f"Artist: {accepted_meta.artist or 'unknown'} | "
        f"Dims: {accepted_meta.width}x{accepted_meta.height} | "
        f"Source: {accepted_candidate.source_path} | "
        f"Identity conf: {accepted_conf}"
    )[:8000]
    for field_name, value in (
        ("image_url",         entity.image_url),
        ("image_source_url",  entity.image_source_url),
        ("image_license",     entity.image_license),
        ("image_credit",      entity.image_credit),
    ):
        if not value:
            continue
        record_provenance(
            entity_type=entity_type, entity_id=entity_id,
            field_name=field_name, value=value,
            snippet=snippet, confidence=accepted_conf,
            source_fetch=source_fetch,
        )

    return ImageAssignment(
        success=True, entity_type=entity_type, entity_id=entity_id,
        image_url=entity.image_url, image_source_url=entity.image_source_url,
        image_license=entity.image_license, image_credit=entity.image_credit,
        qid=qid or "", meta=accepted_meta,
        identity_confidence=accepted_conf,
        source_path=accepted_candidate.source_path,
        considered=considered,
    )
