"""
Bio generation stage — produce a source-grounded biography via Sonnet 4.6.

Two-step flow:

  1. Generate    — assemble verified facts + lead paragraphs from the source,
                   feed to Sonnet with a strict "no prior knowledge" prompt.
  2. Verify      — see pipeline/verify.py. Status starts 'pending'.

The LLM only ever sees text we fetched ourselves. Even with that constraint,
verification is mandatory before a bio is considered live.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

from ..claude_client import ClaudeClient, GenerateResult
from ..models import FieldProvenance, GeneratedBio, SourceFetch

logger = logging.getLogger(__name__)


# How many lead paragraphs to feed the LLM. More = more context but more
# noise; we cap so the model can't bury unsupported claims under bulk.
LEAD_PARAGRAPH_LIMIT = 4

# Bio length target (Sonnet's max_tokens budget).
BIO_MAX_TOKENS = 600


EVENT_SYSTEM_PROMPT = """You are a wrestling encyclopedia editor. Your job is to write a factual overview of a professional wrestling event using ONLY the source material provided in the user message.

STRICT RULES:
1. Use ONLY information from the "Verified facts" and "Source paragraphs" sections. No prior knowledge.
2. If a fact is not in the provided sources, omit it. No speculation, no inferred details, no plausible-sounding additions.
3. Do not invent attendance figures, match outcomes, exact dates, or quotes that aren't in the sources.
4. Cover: when, where, who promoted it, what made the event notable. Two paragraphs.
5. Target 120-200 words. Encyclopedic prose. No bullet points, no headers.

Output the overview text only. No preamble, no labels, no quotes around the output."""


VENUE_SYSTEM_PROMPT = """You are a wrestling encyclopedia editor. Your job is to write a factual overview of a venue (arena, stadium) using ONLY the source material provided in the user message.

STRICT RULES:
1. Use ONLY information from the "Verified facts" and "Source paragraphs" sections. No prior knowledge.
2. If a fact is not in the provided sources, omit it. No speculation, no plausible-sounding additions.
3. Do not invent capacities, locations, dates, owners, or events held there if not in the sources.
4. Cover: where the venue is, when it opened, its capacity, what makes it notable. Two paragraphs.
5. Target 100-180 words. Encyclopedic prose. No bullet points, no headers.

Output the overview text only. No preamble, no labels, no quotes around the output."""


STANDARD_SYSTEM_PROMPT = """You are an encyclopedia editor at a wrestling reference site. Your job is to write a factual, well-crafted biography of a professional wrestler using ONLY the source material provided in the user message.

STRICT RULES (accuracy-first):
1. Use ONLY information from the "Verified facts" and "Source paragraphs" sections. Do not use ANY prior knowledge, even if you recognize the wrestler.
2. If a fact is not in the provided sources, omit it. Never speculate, infer, or fill in plausible-sounding details.
3. Do not invent specific dates, numbers, championship counts, match outcomes, locations, relationships, or quotes that are not explicitly stated in the sources.
4. You may paraphrase the source paragraphs in your own words. You may combine facts from the verified-facts block with details from the source paragraphs.

STYLE RULES (encyclopedic prose):
5. Write in clear, neutral, third-person prose. Two well-constructed paragraphs are usually right.
6. The OPENING SENTENCE must lead with the subject's full real name (if known) followed by the stage name in parentheses (if known), then a tightly-worded "is/was a [nationality] professional wrestler" framing. Example: "Bret Sergeant Hart (born July 2, 1957), better known by his ring name Bret 'The Hitman' Hart, is a Canadian-American retired professional wrestler..."
7. Use precise dates over vague phrases ("on March 29, 1987" not "in the 1980s") only when the source provides them. Otherwise omit.
8. Vary sentence structure — avoid starting consecutive sentences with the same word.
9. Avoid hype words (legendary, iconic, greatest) UNLESS they appear in the source paragraphs as direct attribution (Sky Sports called him "the greatest" → keep, with attribution).
10. No bullet points, no headers, no markdown. Target 150-220 words.

CRITICAL DISAMBIGUATIONS:
- "Billed from" / "Hometown (in-character / stage location)" refers to a wrestler's stage location, NOT their actual birthplace. Do not write "born in [billed-from location]" unless the source paragraphs explicitly say the person was born there.
- "Debut Year" is the start of their pro wrestling career, not the year they were born.
- "Real Name" is the legal/birth name, distinct from ring/stage aliases.
- "Trained by" lists people who trained them — these are individuals, not schools. Schools/territories in this list (e.g., "Ohio Valley Wrestling", "WWE Performance Center") describe WHERE they trained, not WHO.

Output the biography text only. No preamble, no labels, no quotes around the output."""


STRICT_SYSTEM_PROMPT = """You are a wrestling encyclopedia editor writing in STRICT MODE. A previous attempt at this biography was rejected because you combined facts from different sources into relationships that no single source stated directly.

ABSOLUTELY-CRITICAL RULES (a prior attempt failed these):
1. Use ONLY information from the "Verified facts" and "Source paragraphs" sections. NO prior knowledge.
2. NEVER combine independent facts into a derived relationship unless that exact relationship is stated in the sources. Examples of forbidden inferences:
   - Don't write "trained by X at Y" unless one source connects X and Y.
   - Don't write "born in Y" unless a source explicitly says "born in Y" — never substitute "Hometown" / "Billed from" for birthplace.
   - Don't write "during his time in Z, he..." unless the source says the activity happened at Z.
3. If a sentence requires combining two separate facts, write each fact as its own sentence with no causal/locational/temporal bridge.
4. Prefer SHORTER bios over richer ones. It is better to omit a sentence than to risk an unsupported combination.
5. Write 2 paragraphs in clear encyclopedic prose. Target 120-180 words. No bullet points, no headers.

Output the biography text only. No preamble, no labels, no quotes around the output."""


@dataclass
class BioGenerationResult:
    bio: GeneratedBio
    skipped_reason: Optional[str] = None  # set if generation was a no-op


def extract_lead_paragraphs(raw_html: str, max_paragraphs: int = LEAD_PARAGRAPH_LIMIT) -> list[str]:
    """
    Pull the lead-section paragraphs from a Wikipedia article HTML.

    The lead is everything inside .mw-parser-output before the first <h2>.
    We strip <sup> (footnotes) and only keep <p> elements with substantive text.
    """
    if not raw_html:
        return []

    soup = BeautifulSoup(raw_html, "lxml")
    body = soup.find("div", class_=re.compile(r"mw-parser-output"))
    if body is None:
        return []

    for noisy in body.find_all(["sup", "style", "script"]):
        noisy.decompose()

    paragraphs: list[str] = []
    for child in body.children:
        name = getattr(child, "name", None)
        if name in ("h2", "h3"):
            break
        # Wikipedia's Vector 2022 skin wraps headings in <div class="mw-heading">.
        # Treat those as section boundaries too.
        classes = child.get("class", []) if hasattr(child, "get") else []
        if "mw-heading" in classes:
            break
        if name != "p":
            continue
        text = child.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) >= 60:  # skip empty/placeholder paragraphs
            paragraphs.append(text)
        if len(paragraphs) >= max_paragraphs:
            break

    return paragraphs


def _format_facts_block(facts: dict[str, str]) -> str:
    """Render the verified-facts dict as a clean bulleted list for the prompt."""
    if not facts:
        return "(none)"
    # Stable, human-readable ordering for the prompt.
    order = [
        "real_name", "aliases", "birth_date", "death_date", "nationality",
        "hometown", "height", "weight", "debut_year", "retirement_year",
        "trained_by", "finishers", "signature_moves",
    ]
    # Disambiguation: a few field names look like one thing but mean another.
    # "Hometown" comes from Wikipedia's "Billed from" infobox — it's the wrestler's
    # in-character stage location, NOT their birthplace. The LLM otherwise
    # conflates the two (e.g. wrote "Born in Hollywood" for Hulk Hogan, who
    # was actually born in Augusta GA but billed from Hollywood).
    custom_labels = {
        "hometown": "Billed from (in-character / stage location)",
    }
    lines: list[str] = []
    for key in order:
        if key in facts:
            label = custom_labels.get(key, key.replace("_", " ").title())
            lines.append(f"- {label}: {facts[key]}")
    # Append any unrecognised keys at the end (forward-compat).
    for key, value in facts.items():
        if key in order:
            continue
        label = custom_labels.get(key, key.replace("_", " ").title())
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def _latest_facts_for_wrestler(wrestler_id: int) -> dict[str, str]:
    """Latest provenance value per field for this wrestler."""
    facts: dict[str, str] = {}
    provs = (
        FieldProvenance.objects
        .filter(entity_type="wrestler", entity_id=wrestler_id)
        .order_by("field_name", "-extracted_at")
    )
    seen: set[str] = set()
    for p in provs:
        if p.field_name in seen:
            continue
        seen.add(p.field_name)
        facts[p.field_name] = p.value
    return facts


def _primary_source_fetch(wrestler_id: int) -> Optional[SourceFetch]:
    """Pick the SourceFetch we'll feed to the LLM. v3.0 = Wikipedia only."""
    return (
        SourceFetch.objects
        .filter(entity_type="wrestler", entity_id=wrestler_id, source="wikipedia", http_status=200)
        .order_by("-fetched_at")
        .first()
    )


def generate_bio_for_wrestler(
    wrestler,
    client: Optional[ClaudeClient] = None,
    mode: str = "standard",
    parent_bio: Optional[GeneratedBio] = None,
) -> Optional[BioGenerationResult]:
    """
    Generate (but do not yet verify) a bio for one Wrestler.

    Args:
        mode: "standard" (default) or "strict" (used after a prior bio was rejected).
        parent_bio: the previous attempt this one is retrying, if any.

    Returns:
        BioGenerationResult with a GeneratedBio row (status='pending') on success.
        None if Claude is unavailable or no source content exists.
    """
    if client is None:
        client = ClaudeClient()
    if not client.available:
        logger.info("Claude unavailable — skipping bio for Wrestler#%d", wrestler.id)
        return None

    fetch = _primary_source_fetch(wrestler.id)
    if fetch is None:
        logger.info("No source fetch for Wrestler#%d (%s)", wrestler.id, wrestler.name)
        return None

    paragraphs = extract_lead_paragraphs(fetch.raw_content)
    if not paragraphs:
        logger.info(
            "No lead paragraphs extractable for Wrestler#%d (%s)",
            wrestler.id, wrestler.name,
        )
        return None

    facts = _latest_facts_for_wrestler(wrestler.id)
    facts_block = _format_facts_block(facts)
    paragraphs_block = "\n\n".join(f'"""\n{p}\n"""' for p in paragraphs)

    user_prompt = (
        f"Subject: {wrestler.name}\n\n"
        f"Verified facts:\n{facts_block}\n\n"
        f"Source paragraphs (from Wikipedia):\n{paragraphs_block}\n\n"
        f"Write the biography."
    )

    system_prompt = STRICT_SYSTEM_PROMPT if mode == "strict" else STANDARD_SYSTEM_PROMPT

    result: Optional[GenerateResult] = client.generate(
        system=system_prompt,
        user=user_prompt,
        max_tokens=BIO_MAX_TOKENS,
        temperature=0.2 if mode == "standard" else 0.0,  # tighter for strict
    )
    if result is None or not result.text:
        logger.warning("Claude returned no text for Wrestler#%d", wrestler.id)
        return None

    # Compute attempt_number from prior attempts that haven't been permanently rejected.
    prior_count = GeneratedBio.objects.filter(
        entity_type="wrestler", entity_id=wrestler.id,
    ).count()

    # Mark any older bios for this wrestler as superseded (but preserve
    # permanently_rejected which we explicitly don't want re-tried).
    GeneratedBio.objects.filter(
        entity_type="wrestler", entity_id=wrestler.id, status__in=["pending", "verified"]
    ).update(status="superseded")

    bio = GeneratedBio.objects.create(
        entity_type="wrestler",
        entity_id=wrestler.id,
        text=result.text,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        status="pending",
        attempt_number=prior_count + 1,
        generation_mode=mode,
        parent_bio=parent_bio,
    )
    bio.source_fetches.add(fetch)

    logger.info(
        "Generated bio for Wrestler#%d (%s) mode=%s attempt=%d: %d chars, %d in / %d out tokens",
        wrestler.id, wrestler.name, mode, bio.attempt_number, len(result.text),
        result.input_tokens, result.output_tokens,
    )

    return BioGenerationResult(bio=bio)


def generate_and_verify_with_retry(
    wrestler,
    client: Optional[ClaudeClient] = None,
    max_attempts: int = 3,
) -> Optional[GeneratedBio]:
    """
    Run the full self-correcting bio pipeline for one wrestler.

    Strategy:
      attempt 1: standard prompt → generate + verify
      attempt 2 (if rejected): strict prompt → generate + verify
      attempt 3 (if still rejected): trim unsupported sentences from attempt 2 → verify
      else: mark permanently_rejected

    Returns the final bio (verified or permanently_rejected).
    """
    # Late import to avoid circular: verify imports from bio.
    from .verify import verify_bio

    if client is None:
        client = ClaudeClient()

    # Skip if this wrestler is permanently rejected.
    existing_permanent = GeneratedBio.objects.filter(
        entity_type="wrestler", entity_id=wrestler.id, status="permanently_rejected",
    ).exists()
    if existing_permanent:
        logger.info("Wrestler#%d (%s) already permanently_rejected; skipping", wrestler.id, wrestler.name)
        return None

    # ---- attempt 1: standard ----
    gen = generate_bio_for_wrestler(wrestler, client=client, mode="standard")
    if gen is None:
        return None
    vr = verify_bio(gen.bio, client=client)
    if vr is not None and vr.verified:
        return vr.bio

    if max_attempts < 2:
        _mark_permanently_rejected(gen.bio, "max_attempts=1, first attempt failed")
        return gen.bio

    # ---- attempt 2: strict ----
    strict_gen = generate_bio_for_wrestler(wrestler, client=client, mode="strict", parent_bio=gen.bio)
    if strict_gen is None:
        _mark_permanently_rejected(gen.bio, "strict generation failed")
        return gen.bio
    vr = verify_bio(strict_gen.bio, client=client)
    if vr is not None and vr.verified:
        return vr.bio

    if max_attempts < 3:
        _mark_permanently_rejected(strict_gen.bio, "max_attempts=2, strict attempt failed")
        return strict_gen.bio

    # ---- attempt 3: trim ----
    trimmed = trim_unsupported_sentences(strict_gen.bio)
    if trimmed is None:
        _mark_permanently_rejected(strict_gen.bio, "trim path could not produce a salvageable bio")
        return strict_gen.bio

    vr = verify_bio(trimmed, client=client)
    if vr is not None and vr.verified:
        return vr.bio

    _mark_permanently_rejected(trimmed, "all 3 attempts (standard, strict, trim) failed verification")
    return trimmed


def _latest_facts_for_entity(entity_type: str, entity_id: int) -> dict[str, str]:
    """Latest provenance value per field, generic over entity type."""
    facts: dict[str, str] = {}
    provs = (
        FieldProvenance.objects
        .filter(entity_type=entity_type, entity_id=entity_id)
        .order_by("field_name", "-extracted_at")
    )
    seen: set[str] = set()
    for p in provs:
        if p.field_name in seen:
            continue
        seen.add(p.field_name)
        facts[p.field_name] = p.value
    return facts


def _primary_source_fetch_for(entity_type: str, entity_id: int) -> Optional[SourceFetch]:
    """Latest successful Wikipedia fetch for any entity."""
    return (
        SourceFetch.objects
        .filter(entity_type=entity_type, entity_id=entity_id, source="wikipedia", http_status=200)
        .order_by("-fetched_at")
        .first()
    )


def generate_bio_for_event(event, client: Optional[ClaudeClient] = None) -> Optional[BioGenerationResult]:
    """Generate (but do not yet verify) a bio for one Event."""
    if client is None:
        client = ClaudeClient()
    if not client.available:
        return None

    fetch = _primary_source_fetch_for("event", event.id)
    if fetch is None:
        return None
    paragraphs = extract_lead_paragraphs(fetch.raw_content)
    if not paragraphs:
        return None

    facts = _latest_facts_for_entity("event", event.id)
    # Use a simple flat formatter — events don't have the same custom labels
    # as wrestlers (no 'hometown' disambig issue).
    fact_lines = [f"- {k.replace('_', ' ').title()}: {v}" for k, v in sorted(facts.items())]
    facts_block = "\n".join(fact_lines) if fact_lines else "(none)"
    paragraphs_block = "\n\n".join(f'"""\n{p}\n"""' for p in paragraphs)

    user_prompt = (
        f"Subject: {event.name}\n\n"
        f"Verified facts:\n{facts_block}\n\n"
        f"Source paragraphs (from Wikipedia):\n{paragraphs_block}\n\n"
        f"Write the event overview."
    )

    result = client.generate(
        system=EVENT_SYSTEM_PROMPT, user=user_prompt,
        max_tokens=BIO_MAX_TOKENS, temperature=0.2,
    )
    if result is None or not result.text:
        return None

    prior_count = GeneratedBio.objects.filter(entity_type="event", entity_id=event.id).count()
    GeneratedBio.objects.filter(
        entity_type="event", entity_id=event.id, status__in=["pending", "verified"],
    ).update(status="superseded")
    bio = GeneratedBio.objects.create(
        entity_type="event", entity_id=event.id,
        text=result.text, model=result.model,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        status="pending", attempt_number=prior_count + 1,
        generation_mode="standard",
    )
    bio.source_fetches.add(fetch)
    return BioGenerationResult(bio=bio)


def generate_bio_for_venue(venue, client: Optional[ClaudeClient] = None) -> Optional[BioGenerationResult]:
    """Generate (but do not yet verify) a bio for one Venue."""
    if client is None:
        client = ClaudeClient()
    if not client.available:
        return None

    fetch = _primary_source_fetch_for("venue", venue.id)
    if fetch is None:
        return None
    paragraphs = extract_lead_paragraphs(fetch.raw_content)
    if not paragraphs:
        return None

    facts = _latest_facts_for_entity("venue", venue.id)
    fact_lines = [f"- {k.replace('_', ' ').title()}: {v}" for k, v in sorted(facts.items())]
    facts_block = "\n".join(fact_lines) if fact_lines else "(none)"
    paragraphs_block = "\n\n".join(f'"""\n{p}\n"""' for p in paragraphs)

    user_prompt = (
        f"Subject: {venue.name}\n\n"
        f"Verified facts:\n{facts_block}\n\n"
        f"Source paragraphs (from Wikipedia):\n{paragraphs_block}\n\n"
        f"Write the venue overview."
    )

    result = client.generate(
        system=VENUE_SYSTEM_PROMPT, user=user_prompt,
        max_tokens=BIO_MAX_TOKENS, temperature=0.2,
    )
    if result is None or not result.text:
        return None

    prior_count = GeneratedBio.objects.filter(entity_type="venue", entity_id=venue.id).count()
    GeneratedBio.objects.filter(
        entity_type="venue", entity_id=venue.id, status__in=["pending", "verified"],
    ).update(status="superseded")
    bio = GeneratedBio.objects.create(
        entity_type="venue", entity_id=venue.id,
        text=result.text, model=result.model,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        status="pending", attempt_number=prior_count + 1,
        generation_mode="standard",
    )
    bio.source_fetches.add(fetch)
    return BioGenerationResult(bio=bio)


PROMOTION_SYSTEM_PROMPT = """You are a wrestling encyclopedia editor. Your job is to write a factual overview of a wrestling promotion using ONLY the source material provided in the user message.

STRICT RULES:
1. Use ONLY information from the "Verified facts" and "Source paragraphs" sections. No prior knowledge.
2. If a fact is not in the provided sources, omit it. No speculation, no plausible-sounding additions.
3. Do not invent founding dates, executives, viewership numbers, or events not in the sources.
4. Cover: when founded, by whom, where based, what makes the promotion notable. Two paragraphs.
5. Target 120-200 words. Encyclopedic prose. No bullet points, no headers.

Output the overview text only. No preamble, no labels, no quotes around the output."""


def generate_bio_for_promotion(promotion, client: Optional[ClaudeClient] = None) -> Optional[BioGenerationResult]:
    """Generate (but do not yet verify) a bio for one Promotion."""
    if client is None:
        client = ClaudeClient()
    if not client.available:
        return None
    fetch = _primary_source_fetch_for("promotion", promotion.id)
    if fetch is None:
        return None
    paragraphs = extract_lead_paragraphs(fetch.raw_content)
    if not paragraphs:
        return None
    facts = _latest_facts_for_entity("promotion", promotion.id)
    fact_lines = [f"- {k.replace('_', ' ').title()}: {v}" for k, v in sorted(facts.items())]
    facts_block = "\n".join(fact_lines) if fact_lines else "(none)"
    paragraphs_block = "\n\n".join(f'"""\n{p}\n"""' for p in paragraphs)
    user_prompt = (
        f"Subject: {promotion.name}\n\n"
        f"Verified facts:\n{facts_block}\n\n"
        f"Source paragraphs (from Wikipedia):\n{paragraphs_block}\n\n"
        f"Write the promotion overview."
    )
    result = client.generate(
        system=PROMOTION_SYSTEM_PROMPT, user=user_prompt,
        max_tokens=BIO_MAX_TOKENS, temperature=0.2,
    )
    if result is None or not result.text:
        return None
    prior_count = GeneratedBio.objects.filter(entity_type="promotion", entity_id=promotion.id).count()
    GeneratedBio.objects.filter(
        entity_type="promotion", entity_id=promotion.id, status__in=["pending", "verified"],
    ).update(status="superseded")
    bio = GeneratedBio.objects.create(
        entity_type="promotion", entity_id=promotion.id,
        text=result.text, model=result.model,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        status="pending", attempt_number=prior_count + 1,
        generation_mode="standard",
    )
    bio.source_fetches.add(fetch)
    return BioGenerationResult(bio=bio)


def generate_and_verify_for_promotion(promotion, client: Optional[ClaudeClient] = None) -> Optional[GeneratedBio]:
    from .verify import verify_bio
    if client is None:
        client = ClaudeClient()
    gen = generate_bio_for_promotion(promotion, client=client)
    if gen is None:
        return None
    verify_bio(gen.bio, client=client)
    return gen.bio


def generate_and_verify_for_event(event, client: Optional[ClaudeClient] = None) -> Optional[GeneratedBio]:
    """Single-attempt generate+verify for an event (no retry passes for v3.0)."""
    from .verify import verify_bio
    if client is None:
        client = ClaudeClient()
    gen = generate_bio_for_event(event, client=client)
    if gen is None:
        return None
    verify_bio(gen.bio, client=client)
    return gen.bio


def generate_and_verify_for_venue(venue, client: Optional[ClaudeClient] = None) -> Optional[GeneratedBio]:
    """Single-attempt generate+verify for a venue."""
    from .verify import verify_bio
    if client is None:
        client = ClaudeClient()
    gen = generate_bio_for_venue(venue, client=client)
    if gen is None:
        return None
    verify_bio(gen.bio, client=client)
    return gen.bio


def _mark_permanently_rejected(bio: GeneratedBio, reason: str) -> None:
    """Update bio in place to status='permanently_rejected'."""
    bio.status = "permanently_rejected"
    bio.rejection_reason = (bio.rejection_reason or "") + f" | permanent: {reason}"
    bio.save(update_fields=["status", "rejection_reason"])
    logger.warning(
        "Bio#%d for %s#%d permanently rejected: %s",
        bio.id, bio.entity_type, bio.entity_id, reason,
    )


def trim_unsupported_sentences(rejected_bio: GeneratedBio) -> Optional[GeneratedBio]:
    """
    Last-resort self-correction: take a rejected bio and produce a 'trim'
    version that drops the sentences the verifier could not support.

    Creates a new GeneratedBio with mode='trim', status='pending' so the next
    verifier pass can confirm the trimmed version. Returns None if there's
    nothing salvageable (e.g. all sentences were unsupported, or list missing).
    """
    if not rejected_bio.claims_unsupported:
        return None

    from .verify import _split_sentences
    sentences = _split_sentences(rejected_bio.text)
    if not sentences:
        return None

    # The verifier reports unsupported sentences as full strings — match by
    # case-sensitive prefix or substring rather than exact equality, since the
    # LLM sometimes quotes truncated/normalised versions.
    unsupported_set = {u.strip().rstrip('.').lower() for u in rejected_bio.claims_unsupported if u}

    kept: list[str] = []
    for sent in sentences:
        norm = sent.strip().rstrip('.').lower()
        # Drop if any reported unsupported sentence is a prefix of, equal to,
        # or substring of this sentence (or vice versa).
        is_flagged = any(
            u == norm or u in norm or norm in u
            for u in unsupported_set
        )
        if not is_flagged:
            kept.append(sent)

    if not kept:
        # Nothing left — the bio was almost entirely unsupported.
        return None

    if len(kept) == len(sentences):
        # Verifier said something was unsupported but we couldn't identify
        # which sentence to drop. Don't ship the original as-is.
        return None

    trimmed_text = " ".join(kept)

    # Carry over the same sources, same model, but mode='trim'.
    GeneratedBio.objects.filter(
        entity_type=rejected_bio.entity_type,
        entity_id=rejected_bio.entity_id,
        status__in=["pending", "verified"],
    ).update(status="superseded")

    trimmed = GeneratedBio.objects.create(
        entity_type=rejected_bio.entity_type,
        entity_id=rejected_bio.entity_id,
        text=trimmed_text,
        model=rejected_bio.model,
        input_tokens=0,  # no LLM call
        output_tokens=0,
        status="pending",
        attempt_number=rejected_bio.attempt_number + 1,
        generation_mode="trim",
        parent_bio=rejected_bio,
    )
    for sf in rejected_bio.source_fetches.all():
        trimmed.source_fetches.add(sf)

    logger.info(
        "Trimmed bio for %s#%d: kept %d of %d sentences",
        rejected_bio.entity_type, rejected_bio.entity_id, len(kept), len(sentences),
    )

    return trimmed
