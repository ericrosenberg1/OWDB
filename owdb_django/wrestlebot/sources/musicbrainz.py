"""
MusicBrainz adapter — open-license music database.

MusicBrainz is the canonical open-license source for music metadata
(artists, recordings, releases). For WrestleBot, it's used to verify
and enrich ThemeSong entities — pulling release dates, artist credits,
and album affiliations that Wikipedia frequently misses.

API:
    https://musicbrainz.org/ws/2/

No auth required, but a descriptive User-Agent is required by the MB
policy. Rate limit is 1 req/sec averaged over time. We cap ourselves at
that interval.

Accuracy contract:
    MusicBrainz returns confidence scores. We only trust hits with
    `score >= 90` and an exact title match (case-insensitive). Anything
    softer is returned to the agent for judgment, not auto-persisted.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from ..rate_limit import rate_limited

logger = logging.getLogger(__name__)


MB_BASE = "https://musicbrainz.org/ws/2"
USER_AGENT = "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org; admin@wrestlingdb.org)"
# MB policy: 1 req/sec averaged. Cap a hair under to leave headroom for clock skew.
RATE_LIMIT_PER_SEC = 1.0 / 1.05


@dataclass
class MBRecording:
    """One MusicBrainz recording hit."""

    mbid: str
    title: str
    artist: str
    artist_mbids: list[str] = field(default_factory=list)
    first_release_date: str = ""  # ISO date, may be partial (e.g. "1991-08")
    length_ms: int = 0
    score: int = 0  # MB's match confidence, 0..100
    isrcs: list[str] = field(default_factory=list)
    release_titles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "mbid": self.mbid,
            "title": self.title,
            "artist": self.artist,
            "artist_mbids": self.artist_mbids,
            "first_release_date": self.first_release_date,
            "length_ms": self.length_ms,
            "score": self.score,
            "isrcs": self.isrcs,
            "release_titles": self.release_titles[:5],
            "musicbrainz_url": f"https://musicbrainz.org/recording/{self.mbid}"
            if self.mbid
            else "",
        }


def _http_get_json(url: str, timeout: float = 15.0) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with rate_limited("musicbrainz", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 503:
                # MB busy — back off and retry once. The retry reuses our
                # token; we don't re-enter the limiter for the second send.
                time.sleep(2)
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        body = resp.read().decode("utf-8", errors="replace")
                except Exception as e2:
                    logger.warning("MusicBrainz HTTP %s for %s (after retry): %s", e.code, url, e2)
                    return None
            else:
                logger.warning("MusicBrainz HTTP %s for %s: %s", e.code, url, e.reason)
                return None
        except Exception as e:
            logger.warning("MusicBrainz request failed for %s: %s", url, e)
            return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        logger.warning("MusicBrainz returned non-JSON for %s: %s", url, e)
        return None


def _build_query(title: str, artist: Optional[str] = None) -> str:
    """Build a Lucene-style MB query string."""
    parts = [f'recording:"{title.strip()}"']
    if artist:
        parts.append(f'artist:"{artist.strip()}"')
    return " AND ".join(parts)


def search_recordings(
    title: str,
    artist: Optional[str] = None,
    limit: int = 10,
) -> list[MBRecording]:
    """
    Search MusicBrainz for recordings matching title (and optional artist).
    Returns hits in score-descending order.
    """
    if not title or not title.strip():
        return []
    query = _build_query(title, artist)
    url = (
        f"{MB_BASE}/recording/"
        f"?query={urllib.parse.quote(query)}"
        f"&fmt=json"
        f"&limit={max(1, min(limit, 25))}"
    )
    data = _http_get_json(url)
    if not data:
        return []
    out: list[MBRecording] = []
    for row in data.get("recordings", []) or []:
        if not isinstance(row, dict):
            continue
        artists = row.get("artist-credit") or []
        artist_names: list[str] = []
        artist_mbids: list[str] = []
        for a in artists:
            if not isinstance(a, dict):
                continue
            artist_obj = a.get("artist") or {}
            name = artist_obj.get("name") or a.get("name") or ""
            if name:
                artist_names.append(name)
            mbid = artist_obj.get("id") or ""
            if mbid:
                artist_mbids.append(mbid)
        releases = [r.get("title", "") for r in (row.get("releases") or []) if isinstance(r, dict)]
        out.append(
            MBRecording(
                mbid=row.get("id", "") or "",
                title=row.get("title", "") or "",
                artist=" & ".join(artist_names),
                artist_mbids=artist_mbids,
                first_release_date=row.get("first-release-date", "") or "",
                length_ms=int(row.get("length") or 0),
                score=int(row.get("score") or 0),
                isrcs=list(row.get("isrcs") or []),
                release_titles=[r for r in releases if r],
            )
        )
    return out


def get_recording_by_mbid(mbid: str) -> Optional[dict]:
    """Fetch full detail for one recording by MBID."""
    if not mbid:
        return None
    url = (
        f"{MB_BASE}/recording/{urllib.parse.quote(mbid)}?inc=artist-credits+releases+isrcs&fmt=json"
    )
    return _http_get_json(url)


if __name__ == "__main__":  # pragma: no cover
    import sys

    args = sys.argv[1:] or ["Cult of Personality"]
    title = args[0]
    artist = args[1] if len(args) > 1 else None
    hits = search_recordings(title, artist=artist, limit=5)
    print(f"{len(hits)} hits for {title!r}{f' by {artist!r}' if artist else ''}:")
    for h in hits:
        print(json.dumps(h.to_dict(), indent=2))
