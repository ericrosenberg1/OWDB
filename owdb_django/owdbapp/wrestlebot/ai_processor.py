"""
Ollama AI Processor for WrestleBot.

This module integrates with a self-hosted Ollama instance to:
1. Verify extracted data is factual and accurate
2. Enhance data by inferring missing fields
3. Detect and flag potentially copyrighted content
4. Generate proper entity linking suggestions

The AI is used to PROCESS data, not to GENERATE content.
All data originates from Wikipedia's factual records.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Circuit breaker state - shared across all instances
_circuit_breaker = {
    'failures': 0,
    'last_failure': 0,
    'open_until': 0,
}
CIRCUIT_BREAKER_THRESHOLD = 3  # Open circuit after 3 failures
CIRCUIT_BREAKER_RESET_TIME = 300  # 5 minutes before trying again


class OllamaProcessor:
    """
    Self-hosted AI processor using Ollama.

    Ollama runs locally and provides fast inference for:
    - Data verification and validation
    - Entity recognition and linking
    - Duplicate detection
    - Content classification
    """

    DEFAULT_MODEL = "llama3.2"
    DEFAULT_URL = "http://localhost:11434"

    # Timeouts - shorter to prevent freezing
    CONNECT_TIMEOUT = 5  # seconds to establish connection
    GENERATE_TIMEOUT = 60  # seconds for AI to generate response (was 120)
    HEALTH_CHECK_TIMEOUT = 3  # seconds for health check

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.3
    ):
        self.model = model or getattr(
            settings, 'WRESTLEBOT_AI_MODEL', self.DEFAULT_MODEL
        )
        self.base_url = base_url or getattr(
            settings, 'OLLAMA_URL', self.DEFAULT_URL
        )
        self.temperature = temperature
        self.session = requests.Session()
        # Configure session with timeouts
        self.session.timeout = (self.CONNECT_TIMEOUT, self.GENERATE_TIMEOUT)
        self._available = None
        self._last_check = 0

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (blocking requests)."""
        global _circuit_breaker
        now = time.time()

        if now < _circuit_breaker['open_until']:
            return True

        # Reset failures if enough time has passed since last failure
        if now - _circuit_breaker['last_failure'] > CIRCUIT_BREAKER_RESET_TIME:
            _circuit_breaker['failures'] = 0

        return False

    def _record_failure(self):
        """Record a failure for circuit breaker."""
        global _circuit_breaker
        now = time.time()
        _circuit_breaker['failures'] += 1
        _circuit_breaker['last_failure'] = now

        if _circuit_breaker['failures'] >= CIRCUIT_BREAKER_THRESHOLD:
            _circuit_breaker['open_until'] = now + CIRCUIT_BREAKER_RESET_TIME
            logger.warning(
                f"Circuit breaker OPEN - Ollama unavailable. "
                f"Will retry in {CIRCUIT_BREAKER_RESET_TIME}s"
            )

    def _record_success(self):
        """Record a success - reset circuit breaker."""
        global _circuit_breaker
        _circuit_breaker['failures'] = 0
        _circuit_breaker['open_until'] = 0

    def is_available(self, force_check: bool = False) -> bool:
        """
        Check if Ollama is running and the model is available.

        Uses cached result unless force_check=True or cache is stale (>60s).
        Also respects circuit breaker state.
        """
        # Check circuit breaker first
        if self._is_circuit_open():
            logger.debug("Circuit breaker is open, skipping Ollama check")
            return False

        now = time.time()

        # Use cached result if recent (within 60 seconds)
        if not force_check and self._available is not None:
            if now - self._last_check < 60:
                return self._available

        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=self.HEALTH_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    model_names = [m['name'].split(':')[0] for m in models]
                    self._available = self.model.split(':')[0] in model_names
                else:
                    # Ollama running but no models - still mark as unavailable
                    self._available = False
                self._last_check = now
                if self._available:
                    self._record_success()
                return self._available
        except requests.RequestException as e:
            logger.warning(f"Ollama health check failed: {e}")
            self._record_failure()

        self._available = False
        self._last_check = now
        return False

    def fallback_verify(self, data: dict) -> tuple:
        """
        Fallback verification when AI is not available.
        Uses simple heuristic checks instead of AI.
        """
        # Basic validation - check for required fields and reasonable values
        issues = []

        name = data.get('name') or data.get('title', '')
        if not name or len(name) < 2:
            return False, 0.0, "Name too short"

        if len(name) > 200:
            issues.append("Name unusually long")

        # Check for suspicious patterns
        if any(bad in name.lower() for bad in ['test', 'example', 'xxx', 'null']):
            return False, 0.3, "Name contains suspicious pattern"

        # Year validation
        for field in ['debut_year', 'founded_year', 'release_year', 'retirement_year']:
            if field in data and data[field]:
                year = data[field]
                if not (1900 <= year <= 2030):
                    issues.append(f"Invalid {field}: {year}")

        # Confidence based on data completeness
        field_count = sum(1 for v in data.values() if v and v != '')
        confidence = min(0.9, 0.5 + (field_count * 0.05))

        if issues:
            return True, confidence * 0.8, f"Minor issues: {', '.join(issues)}"

        return True, confidence, "Passed basic validation (AI unavailable)"

    def _generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate a response from Ollama.

        Args:
            prompt: The prompt to send
            system: Optional system message
            json_mode: Whether to request JSON output
            timeout: Optional custom timeout (uses GENERATE_TIMEOUT by default)
        """
        # Check circuit breaker first
        if self._is_circuit_open():
            logger.debug("Circuit breaker open, using fallback")
            return None

        if not self.is_available():
            logger.warning("Ollama not available, skipping AI processing")
            return None

        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': self.temperature,
            }
        }

        if system:
            payload['system'] = system

        if json_mode:
            payload['format'] = 'json'

        request_timeout = timeout or self.GENERATE_TIMEOUT

        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=(self.CONNECT_TIMEOUT, request_timeout)
            )
            response.raise_for_status()
            self._record_success()
            return response.json().get('response', '')

        except requests.Timeout as e:
            logger.error(f"Ollama request timed out after {request_timeout}s: {e}")
            self._record_failure()
            return None

        except requests.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            self._record_failure()
            return None

    def verify_wrestler_data(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, str]:
        """
        Verify wrestler data is accurate and complete.

        Returns:
            Tuple of (is_valid, confidence, reasoning)
        """
        system = """You are a wrestling data verification assistant.
Your job is to verify that wrestler data is accurate and factual.
You should check:
1. The name appears to be a valid wrestling ring name
2. Dates are reasonable (debut year should be after birth year, etc.)
3. Locations are real places
4. The data is consistent

Respond in JSON format with:
{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of any issues found"],
    "reasoning": "brief explanation"
}"""

        prompt = f"""Verify this wrestler data extracted from Wikipedia:

{json.dumps(data, indent=2)}

Is this data accurate and consistent? Respond in JSON format."""

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            # If AI unavailable, accept data with lower confidence
            return True, 0.5, "AI verification unavailable"

        try:
            result = json.loads(response)
            return (
                result.get('valid', True),
                result.get('confidence', 0.7),
                result.get('reasoning', 'Verified by AI')
            )
        except json.JSONDecodeError:
            return True, 0.5, "Could not parse AI response"

    def verify_promotion_data(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, str]:
        """Verify promotion data is accurate."""
        system = """You are a wrestling data verification assistant.
Verify that wrestling promotion data is accurate and factual.
Check that:
1. The promotion name is valid
2. Founded/closed years are reasonable
3. Abbreviations match the promotion name
4. Website URLs look legitimate

Respond in JSON format with:
{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of any issues found"],
    "reasoning": "brief explanation"
}"""

        prompt = f"""Verify this wrestling promotion data:

{json.dumps(data, indent=2)}

Is this data accurate? Respond in JSON format."""

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            return True, 0.5, "AI verification unavailable"

        try:
            result = json.loads(response)
            return (
                result.get('valid', True),
                result.get('confidence', 0.7),
                result.get('reasoning', 'Verified by AI')
            )
        except json.JSONDecodeError:
            return True, 0.5, "Could not parse AI response"

    def verify_event_data(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, str]:
        """Verify event data is accurate."""
        system = """You are a wrestling data verification assistant.
Verify that wrestling event data is accurate and factual.
Check that:
1. The event name looks like a valid wrestling event
2. The date is reasonable
3. Venue and location are real places
4. Attendance figures are plausible

Respond in JSON format with:
{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of any issues found"],
    "reasoning": "brief explanation"
}"""

        prompt = f"""Verify this wrestling event data:

{json.dumps(data, indent=2)}

Is this data accurate? Respond in JSON format."""

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            return True, 0.5, "AI verification unavailable"

        try:
            result = json.loads(response)
            return (
                result.get('valid', True),
                result.get('confidence', 0.7),
                result.get('reasoning', 'Verified by AI')
            )
        except json.JSONDecodeError:
            return True, 0.5, "Could not parse AI response"

    def suggest_entity_links(
        self,
        entity_type: str,
        entity_data: Dict[str, Any],
        existing_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Suggest links between a new entity and existing entities.

        For example, link a wrestler to promotions they've worked for.
        """
        if not existing_entities:
            return []

        system = """You are a wrestling data linking assistant.
Your job is to identify connections between wrestling entities.
Given a new entity and a list of existing entities, identify which
existing entities should be linked to the new one.

Only suggest links that are clearly supported by the data.
Do not guess or make assumptions.

Respond in JSON format with:
{
    "links": [
        {
            "entity_id": <id of existing entity>,
            "entity_name": "<name>",
            "relationship": "<type of relationship>",
            "confidence": 0.0-1.0
        }
    ]
}"""

        # Limit existing entities to avoid token limits
        existing_sample = existing_entities[:50]

        prompt = f"""Find connections for this {entity_type}:

New entity:
{json.dumps(entity_data, indent=2)}

Existing entities:
{json.dumps(existing_sample, indent=2)}

What connections exist? Respond in JSON format."""

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            return []

        try:
            result = json.loads(response)
            return result.get('links', [])
        except json.JSONDecodeError:
            return []

    def extract_nationality(self, birth_place: str) -> Optional[str]:
        """Infer nationality from birth place."""
        system = """You are a geography assistant. Given a birthplace,
determine the nationality. Respond in JSON format with:
{
    "nationality": "<nationality or null if unclear>",
    "confidence": 0.0-1.0
}"""

        prompt = f'What nationality is someone born in "{birth_place}"?'

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            return None

        try:
            result = json.loads(response)
            if result.get('confidence', 0) >= 0.8:
                return result.get('nationality')
        except json.JSONDecodeError:
            pass
        return None

    def check_for_copyrighted_content(self, text: str) -> Tuple[bool, str]:
        """
        Check if text contains potentially copyrighted content.

        Returns (is_safe, reason).
        """
        system = """You are a copyright compliance assistant.
Analyze text to determine if it contains copyrighted content.

Factual data is NOT copyrightable:
- Names, dates, numbers
- Lists of facts
- Short phrases

Copyrightable content includes:
- Original prose descriptions
- Creative narrative
- Unique expressions
- Long quoted passages

Respond in JSON format with:
{
    "is_safe": true/false,
    "reason": "explanation",
    "copyrighted_portions": ["list of potentially copyrighted text"]
}"""

        prompt = f"""Analyze this text for copyright concerns:

"{text}"

Is this text safe to use (factual data only)? Respond in JSON format."""

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            # If AI unavailable, be conservative
            return len(text) < 100, "AI unavailable, applying length limit"

        try:
            result = json.loads(response)
            return (
                result.get('is_safe', False),
                result.get('reason', 'Unknown')
            )
        except json.JSONDecodeError:
            return len(text) < 100, "Could not parse AI response"

    def classify_entity_type(
        self,
        title: str,
        summary: Optional[str] = None
    ) -> Optional[str]:
        """
        Classify what type of wrestling entity a Wikipedia article is about.

        Returns one of: wrestler, promotion, event, title, venue, or None.
        """
        system = """You are a wrestling entity classifier.
Given a Wikipedia article title and optional summary, classify it as:
- wrestler: A professional wrestler
- promotion: A wrestling promotion/company
- event: A wrestling event or PPV
- title: A championship belt/title
- venue: An arena or venue
- other: Not a wrestling entity

Respond in JSON format with:
{
    "entity_type": "<type or null>",
    "confidence": 0.0-1.0
}"""

        prompt = f'Title: "{title}"'
        if summary:
            prompt += f'\nSummary: "{summary[:500]}"'
        prompt += "\n\nWhat type of wrestling entity is this?"

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            return None

        try:
            result = json.loads(response)
            if result.get('confidence', 0) >= 0.7:
                entity_type = result.get('entity_type')
                if entity_type in ['wrestler', 'promotion', 'event', 'title', 'venue']:
                    return entity_type
        except json.JSONDecodeError:
            pass
        return None

    def deduplicate_check(
        self,
        new_entity: Dict[str, Any],
        existing_entities: List[Dict[str, Any]],
        entity_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a new entity is a duplicate of an existing one.

        Returns the matching existing entity, or None if no duplicate.
        """
        if not existing_entities:
            return None

        system = f"""You are a {entity_type} deduplication assistant.
Determine if the new {entity_type} is a duplicate of any existing ones.
Consider:
- Alternate spellings or names
- Aliases and ring names
- Different formatting of the same entity

Respond in JSON format with:
{{
    "is_duplicate": true/false,
    "matching_id": <id of matching entity or null>,
    "confidence": 0.0-1.0,
    "reasoning": "explanation"
}}"""

        # Sample existing entities to avoid token limits
        sample = existing_entities[:30]

        prompt = f"""Is this new {entity_type} a duplicate?

New:
{json.dumps(new_entity, indent=2)}

Existing:
{json.dumps(sample, indent=2)}

Respond in JSON format."""

        response = self._generate(prompt, system=system, json_mode=True)
        if not response:
            return None

        try:
            result = json.loads(response)
            if result.get('is_duplicate') and result.get('matching_id'):
                matching_id = result['matching_id']
                for entity in existing_entities:
                    if entity.get('id') == matching_id:
                        return entity
        except json.JSONDecodeError:
            pass
        return None

    def enrich_wrestler_data(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich wrestler data with inferred information.

        Only adds information that can be reliably inferred from
        existing data - does not fabricate new facts.
        """
        enriched = data.copy()

        # Infer nationality from birth place if missing
        if not enriched.get('nationality') and enriched.get('birth_place'):
            nationality = self.extract_nationality(enriched['birth_place'])
            if nationality:
                enriched['nationality'] = nationality

        return enriched

    def generate_entity_summary(
        self,
        entity_type: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Generate a brief, factual summary for an entity.

        This creates a short description from factual data only,
        not copying any copyrighted prose.
        """
        system = f"""You are a wrestling database assistant.
Create a brief, factual summary for a {entity_type} using ONLY
the provided data. Do not add any information not in the data.
Keep it under 150 words and focus on key facts."""

        prompt = f"""Create a factual summary for this {entity_type}:

{json.dumps(data, indent=2)}

Write a brief, factual summary using only this data."""

        response = self._generate(prompt, system=system)
        if response:
            # Ensure it's not too long and remove any potential issues
            summary = response.strip()[:500]
            return summary
        return ""
