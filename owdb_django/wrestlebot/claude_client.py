"""
Thin Anthropic SDK wrapper for WrestleBot v3.

Auth supports two paths, detected by the credential's prefix (logic borrowed
from hermes-agent's anthropic_adapter):

    CLAUDE_CODE_OAUTH_TOKEN (preferred) — your Claude Code / Max subscription.
        Tokens look like 'cc-...', 'sk-ant-oat-...', 'sk-ant-...' (NOT -api),
        or 'eyJ...' JWTs. Sent via auth_token= which routes through the
        OAuth-2025-04-20 beta endpoint. No per-call API spend.

    ANTHROPIC_API_KEY (fallback) — standard Console pay-per-use API key,
        prefix 'sk-ant-api-...'. Sent via api_key= (x-api-key header).

Without either, .generate() returns None — the rest of the pipeline degrades
gracefully (no bio is generated rather than a hallucinated one).

Throttling is intentionally minimal here; the pipeline orchestrates batching.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


_claude_code_version_cache: Optional[str] = None


def _detect_claude_code_version() -> str:
    """Detect installed Claude Code version. Used in the OAuth user-agent."""
    global _claude_code_version_cache
    if _claude_code_version_cache is not None:
        return _claude_code_version_cache

    for cmd in ("claude", "claude-code"):
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip().split()[0]
                if version and version[0].isdigit():
                    _claude_code_version_cache = version
                    return version
        except Exception:
            continue

    _claude_code_version_cache = CLAUDE_CODE_VERSION_FALLBACK
    return CLAUDE_CODE_VERSION_FALLBACK


# Model used for bio generation. The system prompt for accuracy-first WrestleBot
# explicitly forbids using prior knowledge, so Sonnet 4.6 should treat the
# provided source snippets as the sole ground truth.
DEFAULT_MODEL = "claude-sonnet-4-6"

# Beta headers Anthropic requires for OAuth-token traffic. Matches what Claude
# Code itself sends — without the full set, Anthropic throttles or 500s
# requests that pass OAuth auth but don't look like Claude Code. Source:
# hermes-agent/agent/anthropic_adapter.py:_COMMON_BETAS + _OAUTH_ONLY_BETAS.
OAUTH_BETA_HEADERS = (
    "claude-code-20250219",
    "oauth-2025-04-20",
    "interleaved-thinking-2025-05-14",
    "fine-grained-tool-streaming-2025-05-14",
)

# OAuth requests must start the system prompt with this exact text block, or
# Anthropic's edge rejects them as "not Claude Code". The real instructions
# follow as a second block.
CLAUDE_CODE_SYSTEM_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude."

# Fallback Claude Code version when `claude --version` isn't on PATH. Must be
# kept reasonably current — Anthropic rejects stale-version OAuth traffic.
CLAUDE_CODE_VERSION_FALLBACK = "2.1.74"


def _is_oauth_token(key: str) -> bool:
    """
    Detect whether a credential is an OAuth/setup token rather than a Console API key.

    Logic mirrored from hermes-agent/agent/anthropic_adapter.py:_is_oauth_token.

    - 'sk-ant-api...'   -> Console API key (use api_key=)
    - 'sk-ant-oat-...'  -> OAuth setup token (use auth_token=)
    - 'sk-ant-...'      -> Other Anthropic-issued OAuth (use auth_token=)
    - 'eyJ...'          -> JWT from OAuth flow (use auth_token=)
    - 'cc-...'          -> Claude Code OAuth (CLAUDE_CODE_OAUTH_TOKEN)
    """
    if not key:
        return False
    if key.startswith("sk-ant-api"):
        return False
    if key.startswith("sk-ant-"):
        return True
    if key.startswith("eyJ"):
        return True
    if key.startswith("cc-"):
        return True
    return False


@dataclass
class Credential:
    token: str
    is_oauth: bool
    source: str  # "CLAUDE_CODE_OAUTH_TOKEN" or "ANTHROPIC_API_KEY"


def discover_credential() -> Optional[Credential]:
    """
    Pick the best available credential.

    Preference order:
      1. CLAUDE_CODE_OAUTH_TOKEN env var (manual override, e.g. CI)
      2. Claude Code OAuth via macOS Keychain or ~/.claude/.credentials.json
         — Hermes/Paperclip flow; auto-refreshes expired access tokens.
      3. ANTHROPIC_API_KEY env var (pay-per-use Console API key)
    """
    # 1. Manual env override (CI, docker)
    oauth_env = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    if oauth_env:
        return Credential(token=oauth_env, is_oauth=True, source="CLAUDE_CODE_OAUTH_TOKEN")

    # 2. Native Claude Code credentials (Keychain / file), with auto-refresh.
    try:
        from . import claude_credentials

        token = claude_credentials.get_active_access_token()
        if token:
            return Credential(token=token, is_oauth=True, source="claude_code_credentials")
    except Exception as e:
        logger.debug("Claude Code credential lookup failed: %s", e)

    # 3. Pay-per-use API key.
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        return Credential(
            token=api_key,
            is_oauth=_is_oauth_token(api_key),
            source="ANTHROPIC_API_KEY",
        )

    return None


@dataclass
class GenerateResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class ClaudeClient:
    """
    Single-purpose wrapper around the Anthropic Python SDK.

    Use:
        client = ClaudeClient()
        if not client.available:
            ...  # skip LLM step
        result = client.generate(system=..., user=..., max_tokens=800)
        if result is None:  # transient failure
            ...
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        min_call_interval_seconds: float = 0.5,
    ):
        self.model = model
        self.min_call_interval = min_call_interval_seconds
        self._last_call_ts: float = 0.0

        self.credential = discover_credential()
        self._sdk_client = None
        if self.credential is None:
            logger.info(
                "ClaudeClient: no credentials in env "
                "(CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY). "
                "Bio generation will be skipped."
            )

    @property
    def available(self) -> bool:
        return self.credential is not None

    def _ensure_client(self):
        if self._sdk_client is not None:
            return self._sdk_client
        if not self.credential:
            return None

        import anthropic

        kwargs: dict = {}
        if self.credential.is_oauth:
            # OAuth path: auth_token= routes via Bearer. We also need the full
            # Claude Code identity fingerprint, or Anthropic's edge throttles
            # / 500s OAuth traffic that doesn't look like Claude Code.
            version = _detect_claude_code_version()
            kwargs["auth_token"] = self.credential.token
            kwargs["default_headers"] = {
                "anthropic-beta": ",".join(OAUTH_BETA_HEADERS),
                "user-agent": f"claude-cli/{version} (external, cli)",
                "x-app": "cli",
            }
            logger.info(
                "ClaudeClient: using OAuth auth (source=%s, claude-cli/%s)",
                self.credential.source,
                version,
            )
        else:
            kwargs["api_key"] = self.credential.token
            logger.info(
                "ClaudeClient: using API key auth (source=%s)",
                self.credential.source,
            )

        self._sdk_client = anthropic.Anthropic(**kwargs)
        return self._sdk_client

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_call_ts
        if elapsed < self.min_call_interval:
            time.sleep(self.min_call_interval - elapsed)
        self._last_call_ts = time.time()

    def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 800,
        temperature: float = 0.2,
    ) -> Optional[GenerateResult]:
        """
        One-shot completion. Returns None on transient failure / unavailable.
        Does not retry — caller decides retry policy.
        """
        sdk = self._ensure_client()
        if sdk is None:
            return None

        self._throttle()

        # OAuth requests must prepend the Claude Code identity block to the
        # system prompt as a separate text block. API-key path can pass a
        # plain string.
        system_param: object
        if self.credential and self.credential.is_oauth:
            system_param = [
                {"type": "text", "text": CLAUDE_CODE_SYSTEM_PREFIX},
                {"type": "text", "text": system},
            ]
        else:
            system_param = system

        try:
            resp = sdk.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_param,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as e:
            logger.error("Anthropic API call failed: %s", e)
            return None

        # Concatenate any text blocks (typically just one).
        text_parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "\n".join(text_parts).strip()

        usage = getattr(resp, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

        return GenerateResult(
            text=text,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def create_message(
        self,
        *,
        system: str,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        """
        Lower-level entry point used by the agent runner. Returns the raw
        Anthropic response so callers can inspect tool_use blocks.

        Handles the OAuth identity prefix automatically (Claude Code system
        block is prepended on OAuth credentials).

        Returns None if the client is unavailable or the call raises.
        """
        sdk = self._ensure_client()
        if sdk is None:
            return None

        self._throttle()

        if self.credential and self.credential.is_oauth:
            system_param: object = [
                {"type": "text", "text": CLAUDE_CODE_SYSTEM_PREFIX},
                {"type": "text", "text": system},
            ]
        else:
            system_param = system

        kwargs: dict = dict(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_param,
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools

        try:
            return sdk.messages.create(**kwargs)
        except Exception as e:
            logger.error("Anthropic create_message failed: %s", e)
            return None
