"""
Resolve EntityMention rows to actual database entities and create cross-links.

v3.0 scope: wrestler -> promotion linking only. Approach:

  1. Maintain a curated registry of known promotion wiki-titles + acronyms.
     Anything not in the registry stays unresolved (no false positives).
  2. For each unresolved mention of a known promotion, create a Promotion
     stub (name + wikipedia_url, no fetch) and link via WrestlerPromotionHistory.
  3. Mark the mention resolved.

Later sessions can:
  - Add wrestler-to-wrestler links (trainer relationships)
  - Add venue resolution
  - Replace the registry with infobox-class auto-detection
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from ..models import EntityMention

logger = logging.getLogger(__name__)


# Curated mapping of wiki link -> (canonical name, abbreviation).
# All keys match the normalised wiki_link form ("Stampede_Wrestling" -> "Stampede Wrestling").
# Acronyms are convenience aliases; the resolver checks them too.
KNOWN_PROMOTIONS: dict[str, dict[str, str]] = {
    # Active majors
    "WWE": {"name": "WWE", "abbreviation": "WWE"},
    "World Wrestling Entertainment": {"name": "WWE", "abbreviation": "WWE"},
    "World Wrestling Federation": {"name": "World Wrestling Federation", "abbreviation": "WWF"},
    "WWF": {"name": "World Wrestling Federation", "abbreviation": "WWF"},
    "AEW": {"name": "All Elite Wrestling", "abbreviation": "AEW"},
    "All Elite Wrestling": {"name": "All Elite Wrestling", "abbreviation": "AEW"},
    "Impact Wrestling": {"name": "Impact Wrestling", "abbreviation": "IMPACT"},
    "Total Nonstop Action Wrestling": {"name": "Impact Wrestling", "abbreviation": "TNA/IMPACT"},
    "TNA": {"name": "Impact Wrestling", "abbreviation": "TNA/IMPACT"},
    "Ring of Honor": {"name": "Ring of Honor", "abbreviation": "ROH"},
    "ROH": {"name": "Ring of Honor", "abbreviation": "ROH"},
    "New Japan Pro-Wrestling": {"name": "New Japan Pro-Wrestling", "abbreviation": "NJPW"},
    "NJPW": {"name": "New Japan Pro-Wrestling", "abbreviation": "NJPW"},
    "All Japan Pro Wrestling": {"name": "All Japan Pro Wrestling", "abbreviation": "AJPW"},
    "AJPW": {"name": "All Japan Pro Wrestling", "abbreviation": "AJPW"},
    "Pro Wrestling Noah": {"name": "Pro Wrestling Noah", "abbreviation": "NOAH"},
    "Pro Wrestling NOAH": {"name": "Pro Wrestling Noah", "abbreviation": "NOAH"},
    "World Wonder Ring Stardom": {"name": "Stardom", "abbreviation": "STARDOM"},
    "Stardom (wrestling)": {"name": "Stardom", "abbreviation": "STARDOM"},
    "Major League Wrestling": {"name": "Major League Wrestling", "abbreviation": "MLW"},
    "MLW": {"name": "Major League Wrestling", "abbreviation": "MLW"},
    "Game Changer Wrestling": {"name": "Game Changer Wrestling", "abbreviation": "GCW"},
    "Consejo Mundial de Lucha Libre": {"name": "CMLL", "abbreviation": "CMLL"},
    "CMLL": {"name": "CMLL", "abbreviation": "CMLL"},
    "Asistencia Asesoría y Administración": {"name": "AAA", "abbreviation": "AAA"},
    "AAA": {"name": "AAA", "abbreviation": "AAA"},
    "Lucha Libre AAA Worldwide": {"name": "AAA", "abbreviation": "AAA"},
    # Defunct historicals
    "World Championship Wrestling": {"name": "World Championship Wrestling", "abbreviation": "WCW"},
    "WCW": {"name": "World Championship Wrestling", "abbreviation": "WCW"},
    "Extreme Championship Wrestling": {
        "name": "Extreme Championship Wrestling",
        "abbreviation": "ECW",
    },
    "ECW": {"name": "Extreme Championship Wrestling", "abbreviation": "ECW"},
    "Stampede Wrestling": {"name": "Stampede Wrestling", "abbreviation": "Stampede"},
    "American Wrestling Association": {
        "name": "American Wrestling Association",
        "abbreviation": "AWA",
    },
    "AWA": {"name": "American Wrestling Association", "abbreviation": "AWA"},
    "National Wrestling Alliance": {"name": "National Wrestling Alliance", "abbreviation": "NWA"},
    "NWA": {"name": "National Wrestling Alliance", "abbreviation": "NWA"},
    "Mid-South Wrestling": {"name": "Mid-South Wrestling", "abbreviation": "Mid-South"},
    "World Class Championship Wrestling": {
        "name": "World Class Championship Wrestling",
        "abbreviation": "WCCW",
    },
    "Universal Wrestling Federation (Bill Watts)": {
        "name": "Universal Wrestling Federation",
        "abbreviation": "UWF",
    },
    # WWE sub-brands often appear as separate links
    "WWE NXT": {"name": "WWE NXT", "abbreviation": "NXT"},
    "WWE Raw": {"name": "WWE Raw (brand)", "abbreviation": "Raw"},
    "WWE SmackDown": {"name": "WWE SmackDown (brand)", "abbreviation": "SmackDown"},
}


def _get_or_create_promotion_stub(spec: dict[str, str], wiki_link: str):
    """
    Create or return a lightweight Promotion entity for this canonical entry.

    Stubs are created with a synthetic FieldProvenance(name) row tied to a
    synthetic "linking_registry" SourceFetch so the accuracy contract still
    sees the required `name` field as covered. Before this fix the stub
    had zero provenance, which left every promotion created via this path
    permanently stuck at verification_state='candidate'.
    """
    from owdb_django.owdbapp.models import Promotion
    from ..models import SourceFetch
    from ._provenance import record_provenance

    canonical_name = spec["name"]
    canonical_abbr = spec["abbreviation"]
    slug = slugify(canonical_name)[:255]

    # Prefer existing by abbreviation; fall back to slug.
    promo = (
        Promotion.objects.filter(abbreviation=canonical_abbr).first()
        or Promotion.objects.filter(slug=slug).first()
    )

    wikipedia_url = f"https://en.wikipedia.org/wiki/{wiki_link.replace(' ', '_')}"

    if promo is None:
        promo = Promotion.objects.create(
            name=canonical_name,
            abbreviation=canonical_abbr,
            slug=slug,
            wikipedia_url=wikipedia_url,
        )
        logger.info("Created Promotion stub: %s (%s)", canonical_name, canonical_abbr)

        # Write minimal provenance so the accuracy contract sees the
        # required `name` field as covered. We cite a synthetic
        # SourceFetch keyed by the canonical wiki link so two stub
        # creations for the same wiki target dedupe.
        try:
            sentinel_url = wikipedia_url[:500]
            sf, _ = SourceFetch.objects.get_or_create(
                source="linking_registry",
                content_hash=f"linking_promotion_{slug}"[:64],
                defaults=dict(
                    url=sentinel_url,
                    entity_type="promotion",
                    entity_id=promo.id,
                    candidate_name=canonical_name[:255],
                    http_status=200,
                    raw_content=(
                        f"KNOWN_PROMOTIONS registry stub for {wiki_link!r}; "
                        f"canonical name {canonical_name!r}, abbr {canonical_abbr!r}."
                    ),
                ),
            )
            # Make sure the sentinel points at this newly-minted promo.
            if sf.entity_id != promo.id:
                sf.entity_type = "promotion"
                sf.entity_id = promo.id
                sf.save(update_fields=["entity_type", "entity_id"])
            record_provenance(
                entity_type="promotion",
                entity_id=promo.id,
                field_name="name",
                value=canonical_name,
                source_fetch=sf,
                snippet=f"KNOWN_PROMOTIONS[{wiki_link!r}]",
                confidence=85,  # curated registry — high but not direct extract
            )
        except Exception as e:  # never let provenance fail block creation
            logger.warning(
                "Couldn't record name-provenance for promotion stub %s: %s",
                canonical_name,
                e,
            )
    else:
        # Backfill the wikipedia_url if missing.
        if not promo.wikipedia_url:
            promo.wikipedia_url = wikipedia_url
            promo.save(update_fields=["wikipedia_url"])
    return promo


def resolve_wrestler_mentions_to_wrestlers(wrestler_id: int) -> dict:
    """
    For one wrestler, look at their unresolved EntityMentions and resolve
    any whose wiki_link matches an existing Wrestler's Wikipedia title.

    This produces the wrestler↔wrestler "mentioned in" graph organically —
    no schema change needed; just sets resolved_entity_type='wrestler' on
    the mention row.

    Returns {"resolved": N, "skipped": M}.
    """
    from owdb_django.owdbapp.models import Wrestler

    mentions = EntityMention.objects.filter(
        source_entity_type="wrestler",
        source_entity_id=wrestler_id,
        resolved_entity_id__isnull=True,
    )
    if not mentions.exists():
        return {"resolved": 0, "skipped": 0}

    # Build wiki-link -> wrestler_id index for existing wrestlers. We compare
    # against Wikipedia titles derived from each wrestler's wikipedia_url.
    candidates = Wrestler.objects.exclude(wikipedia_url="").exclude(wikipedia_url__isnull=True)
    wiki_to_wrestler: dict[str, int] = {}
    for w in candidates:
        url = w.wikipedia_url or ""
        # Convert https://en.wikipedia.org/wiki/Bret_Hart -> "Bret Hart"
        if "/wiki/" in url:
            title = url.split("/wiki/", 1)[1].split("#", 1)[0]
            from urllib.parse import unquote as _unquote

            title = _unquote(title).replace("_", " ")
            if title and w.id != wrestler_id:  # don't resolve to self
                wiki_to_wrestler[title] = w.id

    resolved = 0
    skipped = 0
    for mention in mentions:
        target_id = wiki_to_wrestler.get(mention.wiki_link)
        if target_id is None:
            skipped += 1
            continue
        mention.resolved_entity_type = "wrestler"
        mention.resolved_entity_id = target_id
        mention.resolved_at = timezone.now()
        mention.save(update_fields=["resolved_entity_type", "resolved_entity_id", "resolved_at"])
        resolved += 1

    return {"resolved": resolved, "skipped": skipped}


def resolve_all_mentions_to_wrestlers() -> dict:
    """
    Sweep ALL unresolved EntityMention rows (regardless of source entity
    type) and resolve any whose wiki_link matches an existing Wrestler's
    canonical Wikipedia title.

    This is the type-agnostic version — it picks up event-sourced and
    venue-sourced mentions that point at wrestlers we have. The per-wrestler
    resolver (used at persist time) only sees wrestler-sourced mentions.

    Returns {"resolved": N, "checked": M}.
    """
    from urllib.parse import unquote as _unquote
    from owdb_django.owdbapp.models import Wrestler

    # Build wiki-title -> wrestler_id index once.
    wiki_to_wrestler: dict[str, int] = {}
    for w in (
        Wrestler.objects.exclude(wikipedia_url="")
        .exclude(wikipedia_url__isnull=True)
        .only("id", "wikipedia_url")
    ):
        url = w.wikipedia_url or ""
        if "/wiki/" in url:
            title = url.split("/wiki/", 1)[1].split("#", 1)[0]
            title = _unquote(title).replace("_", " ")
            if title:
                wiki_to_wrestler[title] = w.id

    if not wiki_to_wrestler:
        return {"resolved": 0, "checked": 0}

    unresolved = EntityMention.objects.filter(
        resolved_entity_id__isnull=True,
        wiki_link__in=list(wiki_to_wrestler.keys()),
    )
    checked = unresolved.count()
    resolved = 0
    for mention in unresolved:
        target = wiki_to_wrestler.get(mention.wiki_link)
        if target is None or target == mention.source_entity_id:
            continue
        mention.resolved_entity_type = "wrestler"
        mention.resolved_entity_id = target
        mention.resolved_at = timezone.now()
        mention.save(update_fields=["resolved_entity_type", "resolved_entity_id", "resolved_at"])
        resolved += 1
    return {"resolved": resolved, "checked": checked}


def resolve_all_mentions_to_events() -> dict:
    """Same sweep as wrestlers, but for events."""
    from urllib.parse import unquote as _unquote
    from owdb_django.wrestlebot.models import SourceFetch

    # Events don't have a wikipedia_url column, but we can recover their
    # canonical title from the Wikipedia SourceFetch.url.
    wiki_to_event: dict[str, int] = {}
    fetches = SourceFetch.objects.filter(
        source="wikipedia", entity_type="event", entity_id__isnull=False
    ).only("entity_id", "url")
    for f in fetches:
        if "/wiki/" in f.url:
            title = f.url.split("/wiki/", 1)[1].split("#", 1)[0]
            title = _unquote(title).replace("_", " ")
            if title and f.entity_id not in wiki_to_event.values():
                wiki_to_event[title] = f.entity_id

    if not wiki_to_event:
        return {"resolved": 0, "checked": 0}

    unresolved = EntityMention.objects.filter(
        resolved_entity_id__isnull=True,
        wiki_link__in=list(wiki_to_event.keys()),
    )
    checked = unresolved.count()
    resolved = 0
    for mention in unresolved:
        target = wiki_to_event.get(mention.wiki_link)
        if target is None:
            continue
        mention.resolved_entity_type = "event"
        mention.resolved_entity_id = target
        mention.resolved_at = timezone.now()
        mention.save(update_fields=["resolved_entity_type", "resolved_entity_id", "resolved_at"])
        resolved += 1
    return {"resolved": resolved, "checked": checked}


def resolve_all_mentions_to_venues() -> dict:
    """Same sweep for venues."""
    from urllib.parse import unquote as _unquote
    from owdb_django.owdbapp.models import Venue

    wiki_to_venue: dict[str, int] = {}
    for v in (
        Venue.objects.exclude(wikipedia_url="")
        .exclude(wikipedia_url__isnull=True)
        .only("id", "wikipedia_url")
    ):
        url = v.wikipedia_url or ""
        if "/wiki/" in url:
            title = url.split("/wiki/", 1)[1].split("#", 1)[0]
            title = _unquote(title).replace("_", " ")
            if title:
                wiki_to_venue[title] = v.id

    if not wiki_to_venue:
        return {"resolved": 0, "checked": 0}

    unresolved = EntityMention.objects.filter(
        resolved_entity_id__isnull=True,
        wiki_link__in=list(wiki_to_venue.keys()),
    )
    checked = unresolved.count()
    resolved = 0
    for mention in unresolved:
        target = wiki_to_venue.get(mention.wiki_link)
        if target is None:
            continue
        mention.resolved_entity_type = "venue"
        mention.resolved_entity_id = target
        mention.resolved_at = timezone.now()
        mention.save(update_fields=["resolved_entity_type", "resolved_entity_id", "resolved_at"])
        resolved += 1
    return {"resolved": resolved, "checked": checked}


def resolve_all_mentions() -> dict:
    """Run all three resolver sweeps and return combined stats."""
    w = resolve_all_mentions_to_wrestlers()
    e = resolve_all_mentions_to_events()
    v = resolve_all_mentions_to_venues()
    return {
        "wrestler_resolved": w["resolved"],
        "event_resolved": e["resolved"],
        "venue_resolved": v["resolved"],
        "total_resolved": w["resolved"] + e["resolved"] + v["resolved"],
    }


def link_trainers_sweep() -> dict:
    """
    Re-evaluate every wrestler's trained_by field and create any missing
    TrainerRelationship rows. Call this after new wrestlers are persisted
    so older trainees auto-link to the newcomer if they listed them as a
    trainer.

    Returns {"checked": N, "linked": M, "missing_names": sorted list of
    trainer names referenced but not yet in the DB — good discovery candidates}.
    """
    from owdb_django.owdbapp.models import Wrestler

    existing_names = {w.name.lower() for w in Wrestler.objects.only("name")}

    checked = 0
    linked = 0
    missing_names: set[str] = set()
    for w in Wrestler.objects.exclude(trained_by="").exclude(trained_by__isnull=True):
        checked += 1
        result = link_trainers_for_wrestler(w)
        linked += result["linked"]
        for name in (n.strip() for n in (w.trained_by or "").split(",") if n.strip()):
            if name.lower() in _NON_PERSON_TRAINERS:
                continue
            if name.lower() not in existing_names:
                missing_names.add(name)
    return {"checked": checked, "linked": linked, "missing_names": sorted(missing_names)}


def link_trainers_for_wrestler(wrestler) -> dict:
    """
    Parse `wrestler.trained_by` (comma-separated names) and create
    TrainerRelationship rows linking to any matching Wrestler in the DB.

    Names that don't match an existing wrestler are skipped silently
    (a future discovery cycle could pick them up).

    Returns {"parsed": N, "linked": M, "missing": K}.
    """
    from owdb_django.owdbapp.models import Wrestler, TrainerRelationship

    if not wrestler.trained_by:
        return {"parsed": 0, "linked": 0, "missing": 0}

    names = [n.strip() for n in wrestler.trained_by.split(",") if n.strip()]
    if not names:
        return {"parsed": 0, "linked": 0, "missing": 0}

    linked = 0
    missing = 0
    for name in names:
        # Skip generic training school names; only link individual wrestlers.
        if name.lower() in _NON_PERSON_TRAINERS:
            continue
        # Look up by exact match first, then case-insensitive name.
        trainer = (
            Wrestler.objects.filter(name=name).first()
            or Wrestler.objects.filter(name__iexact=name).first()
        )
        if trainer is None or trainer.id == wrestler.id:
            missing += 1
            continue
        _, was_new = TrainerRelationship.objects.get_or_create(
            trainee=wrestler,
            trainer=trainer,
        )
        if was_new:
            linked += 1

    return {"parsed": len(names), "linked": linked, "missing": missing}


# These are training schools / institutions, not individual wrestlers. We
# don't want to create a trainer-relationship row for them — they'd need
# their own entity type (school/academy) which we don't model yet.
_NON_PERSON_TRAINERS = {
    "wwe performance center",
    "ovw",
    "wwe nxt",
    "nwa uk hammerlock",
    "the moondogs",
    "monster factory",
    "kowalski's wrestling school",
    "killer kowalski's wrestling school",
    "memphis wrestling school",
    "doa pro wrestling",
    "school of hard knocks",
    "shawn michaels' wrestling academy",
}


def resolve_wrestler_mentions_to_promotions(wrestler_id: int) -> dict:
    """
    For one wrestler, walk their unresolved EntityMention rows and turn the
    ones pointing at known-promotion wiki titles into WrestlerPromotionHistory
    links (creating Promotion stubs as needed).

    Returns {"resolved": N, "linked": M, "skipped": K}.
    """
    from owdb_django.owdbapp.models import Wrestler, WrestlerPromotionHistory

    try:
        wrestler = Wrestler.objects.get(id=wrestler_id)
    except Wrestler.DoesNotExist:
        return {"resolved": 0, "linked": 0, "skipped": 0}

    mentions = EntityMention.objects.filter(
        source_entity_type="wrestler",
        source_entity_id=wrestler_id,
        resolved_entity_id__isnull=True,
    )

    resolved = 0
    linked = 0
    skipped = 0
    for mention in mentions:
        spec = KNOWN_PROMOTIONS.get(mention.wiki_link)
        if spec is None:
            skipped += 1
            continue

        with transaction.atomic():
            promo = _get_or_create_promotion_stub(spec, mention.wiki_link)

            # Create the link if not present. v3.0 doesn't infer years.
            existing = WrestlerPromotionHistory.objects.filter(
                wrestler=wrestler,
                promotion=promo,
                start_year__isnull=True,
            ).first()
            if existing is None:
                WrestlerPromotionHistory.objects.create(
                    wrestler=wrestler,
                    promotion=promo,
                    start_year=None,
                    end_year=None,
                    notes="auto-linked from Wikipedia mention",
                )
                linked += 1

            mention.resolved_entity_type = "promotion"
            mention.resolved_entity_id = promo.id
            mention.resolved_at = timezone.now()
            mention.save(
                update_fields=["resolved_entity_type", "resolved_entity_id", "resolved_at"]
            )
            resolved += 1

    return {"resolved": resolved, "linked": linked, "skipped": skipped}
