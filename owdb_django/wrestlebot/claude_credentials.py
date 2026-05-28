"""
Claude Code OAuth credential loader (Hermes-style).

Reads refreshable Claude Code OAuth credentials from:

  1. macOS Keychain entry "Claude Code-credentials" (Darwin, Claude Code >=2.1.114)
  2. ~/.claude/.credentials.json (Linux + older macOS Claude Code)

When the cached access_token is expired, refreshes against Anthropic's OAuth
token endpoint using the stored refresh_token, then writes the new tokens back
to whichever source we read them from. Same flow Hermes and Paperclip use.

This module is platform-aware but read-only as far as the caller is concerned:
just call `get_active_access_token()` and you get back a valid token (or None
if no creds are available / refresh failed).
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Public Claude Code OAuth client id. Same value Hermes, Paperclip, and the
# Claude CLI all use; this is not a secret.
ANTHROPIC_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

# Token endpoints, tried in order. console.anthropic.com is the older host;
# platform.claude.com is the current canonical one.
TOKEN_ENDPOINTS = (
    "https://platform.claude.com/v1/oauth/token",
    "https://console.anthropic.com/v1/oauth/token",
)

# Refresh when the cached token has less than this many seconds of life left.
EXPIRY_BUFFER_SECONDS = 60

# Path of the JSON-file credential store (used on Linux, and as a fallback on
# macOS Claude Code versions <2.1.114).
CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"

# Keychain service name (macOS, Claude Code >=2.1.114).
KEYCHAIN_SERVICE = "Claude Code-credentials"


@dataclass
class OAuthCredentials:
    access_token: str
    refresh_token: str
    expires_at_ms: int  # 0 if unknown
    source: str  # "macos_keychain" or "credentials_file"

    @property
    def is_valid(self) -> bool:
        if not self.access_token:
            return False
        if self.expires_at_ms == 0:
            # No expiry known; assume valid.
            return True
        now_ms = int(time.time() * 1000)
        return now_ms < (self.expires_at_ms - EXPIRY_BUFFER_SECONDS * 1000)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _read_from_keychain() -> Optional[OAuthCredentials]:
    if platform.system() != "Darwin":
        return None

    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return None

    oauth = payload.get("claudeAiOauth") or {}
    access = oauth.get("accessToken", "")
    if not access:
        return None

    return OAuthCredentials(
        access_token=access,
        refresh_token=oauth.get("refreshToken", ""),
        expires_at_ms=int(oauth.get("expiresAt", 0) or 0),
        source="macos_keychain",
    )


def _read_from_file() -> Optional[OAuthCredentials]:
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, IOError) as e:
        logger.debug("Failed to read %s: %s", CREDENTIALS_FILE, e)
        return None

    oauth = data.get("claudeAiOauth") or {}
    access = oauth.get("accessToken", "")
    if not access:
        return None

    return OAuthCredentials(
        access_token=access,
        refresh_token=oauth.get("refreshToken", ""),
        expires_at_ms=int(oauth.get("expiresAt", 0) or 0),
        source="credentials_file",
    )


def read_credentials() -> Optional[OAuthCredentials]:
    """Read OAuth credentials, preferring Keychain on macOS."""
    creds = _read_from_keychain()
    if creds is not None:
        return creds
    return _read_from_file()


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


def _refresh_via_endpoint(refresh_token: str) -> Optional[dict]:
    """POST to Anthropic OAuth token endpoints to exchange a refresh_token."""
    if not refresh_token:
        return None

    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": ANTHROPIC_OAUTH_CLIENT_ID,
        }
    ).encode()

    last_error: Optional[Exception] = None
    for endpoint in TOKEN_ENDPOINTS:
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode())
        except Exception as e:
            last_error = e
            logger.debug("OAuth refresh failed at %s: %s", endpoint, e)
            continue

        access = payload.get("access_token")
        if not access:
            logger.debug("OAuth response missing access_token at %s", endpoint)
            continue

        expires_in = int(payload.get("expires_in", 3600))
        return {
            "access_token": access,
            "refresh_token": payload.get("refresh_token", refresh_token),
            "expires_at_ms": int(time.time() * 1000) + expires_in * 1000,
        }

    if last_error is not None:
        logger.warning("All OAuth token endpoints failed; last error: %s", last_error)
    return None


# ---------------------------------------------------------------------------
# Write-back
# ---------------------------------------------------------------------------


def _write_to_keychain(access_token: str, refresh_token: str, expires_at_ms: int) -> bool:
    if platform.system() != "Darwin":
        return False

    payload = json.dumps(
        {
            "claudeAiOauth": {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "expiresAt": expires_at_ms,
                "scopes": ["user:inference", "user:profile"],
            }
        }
    )

    try:
        result = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",  # update if exists
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                _current_username(),
                "-w",
                payload,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.debug("Keychain write failed: %s", e)
        return False
    return result.returncode == 0


def _write_to_file(access_token: str, refresh_token: str, expires_at_ms: int) -> bool:
    try:
        existing: dict = {}
        if CREDENTIALS_FILE.exists():
            existing = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
        existing["claudeAiOauth"] = {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": expires_at_ms,
            "scopes": ["user:inference", "user:profile"],
        }
        CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return True
    except (OSError, IOError, json.JSONDecodeError) as e:
        logger.debug("File write-back failed: %s", e)
        return False


def _current_username() -> str:
    import os

    return os.environ.get("USER") or os.environ.get("LOGNAME") or ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_active_access_token() -> Optional[str]:
    """
    Returns a currently-valid access_token, refreshing if needed.
    Returns None if no creds are available or refresh failed.
    """
    creds = read_credentials()
    if creds is None:
        return None

    if creds.is_valid:
        return creds.access_token

    # Expired or near-expiry — refresh.
    logger.info("Claude Code OAuth token expired; refreshing")
    refreshed = _refresh_via_endpoint(creds.refresh_token)
    if refreshed is None:
        # Even if refresh failed, return the old token as a last resort.
        # The SDK will likely 401 and the caller will see the failure.
        logger.warning("OAuth refresh failed; returning stale token (likely will 401)")
        return creds.access_token

    # Persist refreshed tokens back to wherever we read them from.
    if creds.source == "macos_keychain":
        ok = _write_to_keychain(
            refreshed["access_token"],
            refreshed["refresh_token"],
            refreshed["expires_at_ms"],
        )
        if not ok:
            logger.debug("Keychain write-back failed; falling back to file")
            _write_to_file(
                refreshed["access_token"],
                refreshed["refresh_token"],
                refreshed["expires_at_ms"],
            )
    else:
        _write_to_file(
            refreshed["access_token"],
            refreshed["refresh_token"],
            refreshed["expires_at_ms"],
        )

    return refreshed["access_token"]
