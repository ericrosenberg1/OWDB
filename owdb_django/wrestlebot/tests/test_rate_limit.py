"""
Tests for the cross-process rate limiter.

The core promise of ``rate_limited()`` is: no matter how many concurrent
callers race on the same key, the acquires come out spaced by at least
``1/per_second``. The big concurrent test below is the headline check —
it's what protects the MusicBrainz client from a worker-count-multiplied
request rate that gets us IP-banned.
"""

from __future__ import annotations

import threading
import time
from unittest import mock

from django.test import SimpleTestCase

from owdb_django.wrestlebot import rate_limit


class RateLimiterConcurrencyTests(SimpleTestCase):
    """The headline guarantee: spacing is enforced under contention."""

    def setUp(self):
        rate_limit._reset_for_tests()

    def test_concurrent_acquires_are_spaced_by_at_least_one_interval(self):
        per_second = 10.0
        # 10% tolerance for clock granularity; tighter than that is flaky.
        min_gap = (1.0 / per_second) * 0.9
        n_threads = 4
        per_thread = 4
        expected_total = n_threads * per_thread

        timestamps: list[float] = []
        ts_lock = threading.Lock()

        def worker():
            for _ in range(per_thread):
                with rate_limit.rate_limited(
                    "limiter-concurrency-test", per_second=per_second,
                ):
                    now = time.monotonic()
                    with ts_lock:
                        timestamps.append(now)

        # Force the in-process fallback path so the test is hermetic.
        # The Redis path is exercised separately below via a fake client.
        with mock.patch.object(rate_limit, "_get_redis_client",
                               return_value=None):
            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(len(timestamps), expected_total)
        timestamps.sort()
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            self.assertGreaterEqual(
                gap, min_gap,
                f"Saw a {gap * 1000:.1f}ms gap between acquires {i - 1} and "
                f"{i}; limiter at {per_second}/s must enforce "
                f">= {min_gap * 1000:.1f}ms.",
            )

    def test_distinct_keys_do_not_share_quota(self):
        per_second = 0.5  # 2-second interval; obvious if shared.
        with mock.patch.object(rate_limit, "_get_redis_client",
                               return_value=None):
            t0 = time.monotonic()
            with rate_limit.rate_limited("limiter-key-A",
                                         per_second=per_second):
                pass
            with rate_limit.rate_limited("limiter-key-B",
                                         per_second=per_second):
                pass
            elapsed = time.monotonic() - t0

        self.assertLess(
            elapsed, 1.0,
            f"Distinct keys took {elapsed:.3f}s; should be near-zero. "
            "Keys appear to share a bucket.",
        )


class RateLimiterRedisPathTests(SimpleTestCase):
    """Verify the Redis call shape without depending on a real Redis."""

    def setUp(self):
        rate_limit._reset_for_tests()

    def test_redis_eval_called_with_per_source_key_and_args(self):
        fake_client = mock.MagicMock()
        fake_client.eval.return_value = b"0"

        with mock.patch.object(rate_limit, "_get_redis_client",
                               return_value=fake_client):
            with rate_limit.rate_limited("musicbrainz", per_second=1.0):
                pass

        self.assertEqual(fake_client.eval.call_count, 1)
        args = fake_client.eval.call_args.args
        # (lua_script, numkeys, key, rate, burst, now, ttl)
        self.assertEqual(args[1], 1, "exactly one KEYS entry")
        self.assertEqual(args[2], "wrestlebot:ratelimit:musicbrainz")
        self.assertEqual(args[3], "1.0")  # per_second
        self.assertEqual(args[4], "1.0")  # default burst

    def test_redis_failure_falls_back_to_local_lock(self):
        fake_client = mock.MagicMock()
        fake_client.eval.side_effect = RuntimeError("connection reset")

        with mock.patch.object(rate_limit, "_get_redis_client",
                               return_value=fake_client):
            # Must not raise; should silently fall back to the local limiter.
            with rate_limit.rate_limited("limiter-recovery-test",
                                         per_second=100.0):
                pass


class RateLimiterArgValidationTests(SimpleTestCase):
    def setUp(self):
        rate_limit._reset_for_tests()

    def test_zero_or_negative_per_second_raises(self):
        with self.assertRaises(ValueError):
            with rate_limit.rate_limited("x", per_second=0):
                pass
        with self.assertRaises(ValueError):
            with rate_limit.rate_limited("x", per_second=-1.0):
                pass

    def test_burst_below_one_raises(self):
        with self.assertRaises(ValueError):
            with rate_limit.rate_limited("x", per_second=1.0, burst=0.5):
                pass
