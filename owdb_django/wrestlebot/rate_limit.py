"""
Cross-process rate limiter using a Redis-backed token bucket.

Several source clients (MusicBrainz, Discogs, Brave, Tavily, ProFightDB)
used to throttle via a module-level ``_last_request_ts`` variable. Under
Celery prefork, each worker process gets its own copy of that state, so a
1 req/sec upstream limit can become N req/sec across N workers (plus the
web process). MusicBrainz bans aggressively and is slow to recover, so
the divergence between intended and actual rate is a real liability.

This module routes throttling through a single Redis-backed token bucket
shared by every process, falling back to a per-process limiter if Redis
is unreachable.

Usage:
    from owdb_django.wrestlebot.rate_limit import rate_limited

    with rate_limited("musicbrainz", per_second=1.0):
        do_http_request()

Each ``key`` gets its own bucket — different sources don't share quota.
Default ``burst=1`` (no bursting) preserves the existing min-interval
semantics; bumping burst allows short bursts up to that many tokens.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


_BUCKET_TTL_SECONDS = 3600
_KEY_PREFIX = "wrestlebot:ratelimit:"


# Atomic token-bucket evaluation. Runs inside a single Redis command so
# concurrent workers can't race past each other.
#
# KEYS[1] = bucket key
# ARGV[1] = rate (tokens/sec)
# ARGV[2] = burst (max tokens)
# ARGV[3] = now (unix seconds, float)
# ARGV[4] = ttl seconds
# Returns: wait_seconds (string)
_LUA_TOKEN_BUCKET = """
local key   = KEYS[1]
local rate  = tonumber(ARGV[1])
local burst = tonumber(ARGV[2])
local now   = tonumber(ARGV[3])
local ttl   = tonumber(ARGV[4])

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens  = tonumber(data[1])
local last_ts = tonumber(data[2])

if tokens == nil or last_ts == nil then
  tokens  = burst
  last_ts = now
end

local elapsed = math.max(0, now - last_ts)
tokens = math.min(burst, tokens + elapsed * rate)

local wait
if tokens >= 1 then
  tokens  = tokens - 1
  last_ts = now
  wait    = 0
else
  wait    = (1 - tokens) / rate
  tokens  = 0
  last_ts = now + wait
end

redis.call('HMSET', key, 'tokens', tostring(tokens), 'ts', tostring(last_ts))
redis.call('EXPIRE', key, ttl)
return tostring(wait)
"""


_redis_client = None
_redis_init_lock = threading.Lock()
_redis_unavailable = False
_warned_fallback = False

_fallback_lock = threading.Lock()
_fallback_next_available: dict[str, float] = {}


def _resolve_redis_url() -> Optional[str]:
    try:
        from django.conf import settings

        url = getattr(settings, "CELERY_BROKER_URL", None) or getattr(settings, "REDIS_URL", None)
        if url:
            return url
    except Exception:
        pass
    return os.environ.get("CELERY_BROKER_URL") or os.environ.get("REDIS_URL")


def _get_redis_client():
    """Lazy redis client. Returns None if redis is unavailable for this process."""
    global _redis_client, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis_client is not None:
        return _redis_client
    with _redis_init_lock:
        if _redis_unavailable:
            return None
        if _redis_client is not None:
            return _redis_client
        url = _resolve_redis_url()
        if not url:
            _redis_unavailable = True
            return None
        try:
            import redis

            client = redis.Redis.from_url(
                url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            client.ping()
        except Exception as e:
            _redis_unavailable = True
            logger.warning(
                "rate_limit: Redis unavailable (%s); using per-process "
                "fallback. Cross-worker rate limits will NOT be enforced.",
                e,
            )
            return None
        _redis_client = client
        return client


def _fallback_acquire(key: str, per_second: float) -> float:
    """Process-local serializer. Returns the wait time before this slot."""
    interval = 1.0 / per_second
    with _fallback_lock:
        now = time.monotonic()
        next_at = _fallback_next_available.get(key, now)
        wait = max(0.0, next_at - now)
        _fallback_next_available[key] = max(next_at, now) + interval
    return wait


def _redis_acquire(client, key: str, per_second: float, burst: float) -> float:
    res = client.eval(
        _LUA_TOKEN_BUCKET,
        1,
        _KEY_PREFIX + key,
        str(per_second),
        str(burst),
        str(time.time()),
        str(_BUCKET_TTL_SECONDS),
    )
    if isinstance(res, bytes):
        res = res.decode()
    return max(0.0, float(res))


@contextmanager
def rate_limited(
    key: str,
    per_second: float,
    burst: float = 1.0,
) -> Iterator[None]:
    """
    Block until a token is available for ``key``, then yield.

    Args:
        key: Per-source identifier (e.g. ``"musicbrainz"``). Different
            keys do NOT share quota.
        per_second: Sustained rate. ``1.0`` = 1 req/sec.
        burst: Maximum tokens the bucket can hold. Default 1 means no
            bursting — equivalent to a hard minimum interval of
            ``1/per_second``.

    Safe across processes when Redis is reachable. When Redis is down,
    falls back to a per-process limiter and logs a warning once.
    """
    if per_second <= 0:
        raise ValueError(f"per_second must be > 0, got {per_second!r}")
    if burst < 1:
        raise ValueError(f"burst must be >= 1, got {burst!r}")

    global _warned_fallback
    client = _get_redis_client()
    if client is None:
        if not _warned_fallback:
            logger.warning(
                "rate_limit: using process-local fallback (Redis missing) — "
                "cross-worker rate limits NOT enforced."
            )
            _warned_fallback = True
        wait = _fallback_acquire(key, per_second)
    else:
        try:
            wait = _redis_acquire(client, key, per_second, burst)
        except Exception as e:
            logger.warning(
                "rate_limit: Redis eval failed for %r (%s); using local fallback for this call.",
                key,
                e,
            )
            wait = _fallback_acquire(key, per_second)

    if wait > 0:
        time.sleep(wait)
    yield


def _reset_for_tests() -> None:
    """Clear cached state. Intended for unit tests only."""
    global _redis_client, _redis_unavailable, _warned_fallback
    with _redis_init_lock:
        _redis_client = None
        _redis_unavailable = False
        _warned_fallback = False
    with _fallback_lock:
        _fallback_next_available.clear()
