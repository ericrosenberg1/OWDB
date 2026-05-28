"""
Claim verification stage — check every factual statement in a generated bio
against the source snippets that were fed to the LLM at generation time.

Strategy:

  - Read the bio text and the source paragraphs (re-extracted from the
    SourceFetch rows linked to the GeneratedBio).
  - One LLM call asks: "List every sentence in the BIO that is NOT directly
    supported by the SOURCES." Returns a JSON array.
  - If the array is empty -> status='verified', the bio can be promoted.
  - Otherwise -> status='rejected' with the unsupported sentences logged.

Why a single batched call vs per-sentence: cheaper, faster, and the LLM
can compare sentences in context (which helps catch hedging). Output is
constrained to JSON to keep parsing deterministic.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from ..claude_client import ClaudeClient, GenerateResult
from ..models import GeneratedBio
from .bio import (
    _format_facts_block,
    _latest_facts_for_wrestler,
    extract_lead_paragraphs,
)

logger = logging.getLogger(__name__)


VERIFY_SYSTEM_PROMPT = """You are a strict fact-checker. You will be given a biography and a set of source paragraphs.

Your job: identify every sentence in the BIOGRAPHY that is NOT directly supported by the SOURCES. A sentence is "supported" if its factual claims appear in or can be straightforwardly paraphrased from the sources. A sentence is "unsupported" if it asserts a fact (date, number, location, relationship, championship, match, quote, etc.) that the sources do not state.

Be conservative: when in doubt, mark a sentence as unsupported.

Generic descriptive language ("known for his charisma", "popular wrestler") without specific facts is acceptable if it is consistent with the sources.

Output ONLY a JSON object of the form:
  {"unsupported": ["sentence 1...", "sentence 2..."]}

If every sentence is supported, output:
  {"unsupported": []}

Do not include explanations. Do not use markdown fences. Just the JSON."""


@dataclass
class VerificationResult:
    bio: GeneratedBio
    verified: bool
    unsupported: list[str]
    input_tokens: int
    output_tokens: int


def _split_sentences(text: str) -> list[str]:
    """
    Very simple sentence splitter. Good enough for the kind of prose our
    biographies emit. Avoids dragging in NLTK / spacy for a single use.
    """
    text = text.strip()
    # Split on sentence-end followed by whitespace or end-of-string.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)
    return [p.strip() for p in parts if p.strip()]


def _parse_unsupported(response_text: str) -> Optional[list[str]]:
    """
    Pull the unsupported-sentence list out of the LLM's JSON response.

    Returns None if parsing failed entirely (caller should treat as
    rejection — accuracy-first means we never publish a bio we couldn't
    verify).
    """
    text = response_text.strip()
    # Tolerate stray code fences if the model adds them.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Last-ditch: try to extract the first {...} object.
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    if not isinstance(data, dict):
        return None
    arr = data.get("unsupported")
    if not isinstance(arr, list):
        return None
    return [str(s) for s in arr if isinstance(s, str)]


def verify_bio(
    bio: GeneratedBio,
    client: Optional[ClaudeClient] = None,
) -> Optional[VerificationResult]:
    """
    Verify all claims in a pending bio. Updates the GeneratedBio row in place.

    Returns:
        VerificationResult with the bio (status='verified' or 'rejected').
        None if Claude is unavailable.
    """
    if client is None:
        client = ClaudeClient()
    if not client.available:
        logger.info("Claude unavailable — cannot verify GeneratedBio#%d", bio.id)
        return None

    # Reassemble the exact material the LLM was given at generation time:
    # the structured Verified-facts block PLUS the source paragraphs.
    # Both are legitimate evidence; if a sentence in the bio paraphrases
    # something from either, it's "supported".
    snippets: list[str] = []
    for fetch in bio.source_fetches.all():
        snippets.extend(extract_lead_paragraphs(fetch.raw_content))

    if not snippets:
        logger.warning(
            "Cannot verify GeneratedBio#%d: source paragraphs no longer available", bio.id,
        )
        bio.status = "rejected"
        bio.rejection_reason = "No source paragraphs available for verification"
        bio.save()
        return VerificationResult(bio=bio, verified=False, unsupported=[], input_tokens=0, output_tokens=0)

    sentences = _split_sentences(bio.text)
    if not sentences:
        bio.status = "rejected"
        bio.rejection_reason = "Bio text could not be split into sentences"
        bio.save()
        return VerificationResult(bio=bio, verified=False, unsupported=[], input_tokens=0, output_tokens=0)

    # Include the verified-facts block too — it's part of the "ground truth"
    # the bio was allowed to draw from. Works for any entity type because
    # FieldProvenance is keyed by (entity_type, entity_id).
    facts: dict[str, str] = {}
    if bio.entity_type == "wrestler":
        facts = _latest_facts_for_wrestler(bio.entity_id)
        facts_block = _format_facts_block(facts)
    else:
        from .bio import _latest_facts_for_entity
        facts = _latest_facts_for_entity(bio.entity_type, bio.entity_id)
        # Generic flat format — no need for wrestler-specific label remapping.
        fact_lines = [f"- {k.replace('_', ' ').title()}: {v}" for k, v in sorted(facts.items())]
        facts_block = "\n".join(fact_lines) if fact_lines else "(none)"
    sources_block = "\n\n".join(f'"""\n{s}\n"""' for s in snippets)
    bio_block = bio.text

    user_prompt = (
        "VERIFIED FACTS (treat these as supported source material):\n"
        f"{facts_block}\n\n"
        "SOURCE PARAGRAPHS:\n"
        f"{sources_block}\n\n"
        "BIOGRAPHY:\n"
        f"{bio_block}\n\n"
        "Return the JSON object listing unsupported sentences."
    )

    result: Optional[GenerateResult] = client.generate(
        system=VERIFY_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=600,
        temperature=0.0,  # determinism for fact-checking
    )

    if result is None or not result.text:
        logger.warning("Claude returned no verification response for GeneratedBio#%d", bio.id)
        return None

    unsupported = _parse_unsupported(result.text)
    if unsupported is None:
        # Parse failed -> reject (accuracy-first default).
        bio.status = "rejected"
        bio.rejection_reason = f"Verifier response could not be parsed: {result.text[:200]!r}"
        bio.claims_total = len(sentences)
        bio.claims_verified = 0
        bio.claims_unsupported = []
        bio.save()
        return VerificationResult(
            bio=bio, verified=False, unsupported=[],
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        )

    bio.claims_total = len(sentences)
    bio.claims_verified = max(0, len(sentences) - len(unsupported))
    bio.claims_unsupported = unsupported

    if not unsupported:
        bio.status = "verified"
        bio.rejection_reason = ""
    else:
        bio.status = "rejected"
        bio.rejection_reason = f"{len(unsupported)} unsupported sentence(s)"

    bio.save()

    logger.info(
        "Verified GeneratedBio#%d (%s): %d/%d claims supported",
        bio.id, bio.status, bio.claims_verified, bio.claims_total,
    )

    return VerificationResult(
        bio=bio,
        verified=(bio.status == "verified"),
        unsupported=unsupported,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
