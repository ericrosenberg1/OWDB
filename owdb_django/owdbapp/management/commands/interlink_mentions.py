"""
Scan text fields for unlinked mentions and create/link missing entries.

Usage:
    python manage.py interlink_mentions --types=events,matches,media
    python manage.py interlink_mentions --dry-run
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from django.core.management.base import BaseCommand
from owdb_django.owdbapp.models import (
    Book,
    Event,
    Match,
    Podcast,
    PodcastEpisode,
    Special,
    Title,
    Wrestler,
)


MATCH_VS_PATTERN = re.compile(
    r"(?P<left>.+?)\s+(?:vs\.?|v\.?)\s+(?P<right>.+)",
    re.IGNORECASE,
)
MATCH_DEF_PATTERN = re.compile(
    r"(?P<winner>.+?)\s+(?:defeated|defeats|def\.|def|beat|beats|pinned|pins)\s+(?P<loser>.+)",
    re.IGNORECASE,
)
TITLE_PATTERN = re.compile(
    r"for the (?P<title>.+?(?:Championships?|Titles?|Belts?))",
    re.IGNORECASE,
)
MATCH_TYPE_PATTERN = re.compile(r"in (?:a|an) (?P<type>.+?) match", re.IGNORECASE)


STOP_WORDS = {
    "match",
    "championship",
    "title",
    "belt",
    "main event",
    "event",
    "night",
    "winner",
}


@dataclass
class MatchMention:
    participants: List[str]
    winner: Optional[str]
    match_text: str
    result_text: Optional[str]
    match_type: Optional[str]
    title_name: Optional[str]


class Command(BaseCommand):
    help = "Scan text fields for unlinked mentions and create/link entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--types",
            type=str,
            default="all",
            help="Comma-separated list: events, matches, media, all",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Max number of records per type to scan",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show actions without saving changes",
        )

    def handle(self, *args, **options):
        self.dry_run = options.get("dry_run", False)
        types = set(
            t.strip().lower() for t in options.get("types", "all").split(",") if t.strip()
        )
        limit = options.get("limit", 200)

        if "all" in types:
            types = {"events", "matches", "media"}

        self.stdout.write(self.style.SUCCESS("\n=== Interlinking Mentions ===\n"))
        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        self._build_wrestler_index()

        total_links = 0
        total_created = 0

        if "matches" in types:
            links, created = self.link_matches_from_match_text(limit)
            total_links += links
            total_created += created

        if "events" in types:
            links, created = self.link_matches_from_event_about(limit)
            total_links += links
            total_created += created

        if "media" in types:
            links = self.link_wrestlers_in_media(limit)
            total_links += links

        self.stdout.write(self.style.SUCCESS("\n=== Interlinking Complete ==="))
        self.stdout.write(f"Links added: {total_links}")
        self.stdout.write(f"Records created: {total_created}")

    def _build_wrestler_index(self):
        """Build a lookup index for wrestler names and aliases."""
        self.wrestler_name_pairs = []
        seen = set()

        for wrestler in Wrestler.objects.all():
            names = [wrestler.name]
            names.extend(wrestler.get_aliases_list())
            for name in names:
                if not name:
                    continue
                key = name.strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                self.wrestler_name_pairs.append((key, wrestler))

        self.wrestler_name_pairs.sort(key=lambda item: len(item[0]), reverse=True)

    def link_matches_from_match_text(self, limit: int):
        """Ensure match text has linked wrestlers and title references."""
        self.stdout.write("\n--- Linking wrestlers from match text ---")
        links = 0
        created = 0

        matches = Match.objects.select_related("event", "title").all()[:limit]

        for match in matches:
            mention = self._parse_match_line(match.match_text)
            if not mention:
                continue

            participants = self._get_or_create_wrestlers(mention.participants)
            if not participants:
                continue

            new_links = 0
            for wrestler in participants:
                if not match.wrestlers.filter(pk=wrestler.pk).exists():
                    new_links += 1
                    if not self.dry_run:
                        match.wrestlers.add(wrestler)
            links += new_links

            if mention.title_name and match.title is None and match.event and match.event.promotion:
                title, title_created = Title.objects.get_or_create(
                    name=mention.title_name.strip(),
                    defaults={"promotion": match.event.promotion},
                )
                if title_created:
                    created += 1
                if not self.dry_run:
                    match.title = title
                    match.save(update_fields=["title"])
                links += 1

            if mention.winner and match.winner_id is None:
                winner = Wrestler.objects.filter(name__iexact=mention.winner).first()
                if winner:
                    if not self.dry_run:
                        match.winner = winner
                        match.save(update_fields=["winner"])
                    links += 1

            if mention.result_text and not match.result:
                if not self.dry_run:
                    match.result = mention.result_text
                    match.save(update_fields=["result"])
                links += 1

            if new_links > 0:
                self.stdout.write(f"  + {match.match_text} ({new_links} wrestlers linked)")

        return links, created

    def link_matches_from_event_about(self, limit: int):
        """Create and link matches found in event descriptions."""
        self.stdout.write("\n--- Linking matches from event descriptions ---")
        links = 0
        created = 0

        events = Event.objects.select_related("promotion").all()[:limit]

        for event in events:
            if not event.about:
                continue

            for mention in self._extract_match_mentions(event.about):
                if not mention.participants:
                    continue

                existing = Match.objects.filter(
                    event=event, match_text__iexact=mention.match_text
                ).first()
                if existing:
                    continue

                participants = self._get_or_create_wrestlers(mention.participants)
                if not participants:
                    continue

                winner = None
                if mention.winner:
                    winner = Wrestler.objects.filter(name__iexact=mention.winner).first()

                title = None
                if mention.title_name and event.promotion:
                    title, title_created = Title.objects.get_or_create(
                        name=mention.title_name.strip(),
                        defaults={"promotion": event.promotion},
                    )
                    if title_created:
                        created += 1

                if not self.dry_run:
                    match = Match.objects.create(
                        event=event,
                        match_text=mention.match_text,
                        result=mention.result_text,
                        winner=winner,
                        match_type=mention.match_type,
                        title=title,
                        match_order=event.matches.count() + 1,
                    )
                    match.wrestlers.add(*participants)
                created += 1
                links += len(participants)
                self.stdout.write(f"  + {event.name}: {mention.match_text}")

        return links, created

    def link_wrestlers_in_media(self, limit: int):
        """Link wrestlers mentioned in media descriptions."""
        self.stdout.write("\n--- Linking wrestlers in media ---")
        links = 0

        for book in Book.objects.all()[:limit]:
            links += self._link_related_wrestlers(book, book.about, book.related_wrestlers)

        for special in Special.objects.all()[:limit]:
            links += self._link_related_wrestlers(special, special.about, special.related_wrestlers)

        for podcast in Podcast.objects.all()[:limit]:
            links += self._link_related_wrestlers(podcast, podcast.about, podcast.related_wrestlers)
            links += self._link_host_wrestlers(podcast)

        for episode in PodcastEpisode.objects.select_related("podcast").all()[:limit]:
            links += self._link_related_wrestlers(episode, episode.description, episode.guests)

        return links

    def _link_related_wrestlers(self, obj, text: Optional[str], relation):
        if not text:
            return 0

        wrestlers = self._find_wrestlers_in_text(text)
        links = 0
        for wrestler in wrestlers:
            if relation.filter(pk=wrestler.pk).exists():
                continue
            if not self.dry_run:
                relation.add(wrestler)
            links += 1
        if links:
            self.stdout.write(f"  + {obj}: {links} wrestler links")
        return links

    def _link_host_wrestlers(self, podcast: Podcast):
        if not podcast.hosts:
            return 0

        links = 0
        for host in [h.strip() for h in podcast.hosts.split(",") if h.strip()]:
            wrestler = Wrestler.objects.filter(name__iexact=host).first()
            if not wrestler:
                wrestler = self._create_wrestler(host)
            if wrestler and not podcast.host_wrestlers.filter(pk=wrestler.pk).exists():
                if not self.dry_run:
                    podcast.host_wrestlers.add(wrestler)
                links += 1
        if links:
            self.stdout.write(f"  + {podcast.name}: {links} host links")
        return links

    def _find_wrestlers_in_text(self, text: str) -> List[Wrestler]:
        text_norm = f" {self._normalize_text(text)} "
        found = []
        for name, wrestler in self.wrestler_name_pairs:
            if name in STOP_WORDS:
                continue
            if len(name) < 3:
                continue
            pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
            if re.search(pattern, text_norm):
                found.append(wrestler)
        return self._dedupe(found)

    def _extract_match_mentions(self, text: str) -> Iterable[MatchMention]:
        for line in re.split(r"[\n;]+", text):
            mention = self._parse_match_line(line)
            if mention:
                yield mention

    def _parse_match_line(self, line: str) -> Optional[MatchMention]:
        line = line.strip()
        if not line:
            return None

        line = re.sub(r"\(.*?\)", "", line).strip()
        title_name = None
        title_match = TITLE_PATTERN.search(line)
        if title_match:
            title_name = title_match.group("title").strip()
            line = line.replace(title_match.group(0), "").strip()

        match_type = None
        match_type_match = MATCH_TYPE_PATTERN.search(line)
        if match_type_match:
            match_type = match_type_match.group("type").strip().title()

        def_match = MATCH_DEF_PATTERN.search(line)
        if def_match:
            winners = self._split_participants(def_match.group("winner"))
            losers = self._split_participants(def_match.group("loser"))
            participants = winners + losers
            if not participants:
                return None
            winner_name = winners[0] if len(winners) == 1 else None
            match_text = f"{' & '.join(winners)} vs {' & '.join(losers)}"
            result_text = f"{' & '.join(winners)} def. {' & '.join(losers)}"
            return MatchMention(
                participants=participants,
                winner=winner_name,
                match_text=match_text,
                result_text=result_text,
                match_type=match_type,
                title_name=title_name,
            )

        vs_match = MATCH_VS_PATTERN.search(line)
        if vs_match:
            left = self._split_participants(vs_match.group("left"))
            right = self._split_participants(vs_match.group("right"))
            participants = left + right
            if not participants:
                return None
            match_text = f"{' & '.join(left)} vs {' & '.join(right)}"
            return MatchMention(
                participants=participants,
                winner=None,
                match_text=match_text,
                result_text=None,
                match_type=match_type,
                title_name=title_name,
            )

        return None

    def _split_participants(self, text: str) -> List[str]:
        text = self._cleanup_side(text)
        if not text:
            return []
        parts = re.split(r"\s*(?:&|and|,|\+)\s*", text)
        cleaned = [self._normalize_name(part) for part in parts]
        return [name for name in cleaned if name]

    def _cleanup_side(self, text: str) -> str:
        text = re.sub(r"\s+(?:in|for|with|at|on)\s+.+$", "", text, flags=re.IGNORECASE)
        return text.strip(" -,:")

    def _normalize_name(self, text: str) -> str:
        cleaned = re.sub(r"[^0-9a-zA-Z\s'\-\.]", "", text).strip()
        if not cleaned:
            return ""
        lowered = cleaned.lower()
        if lowered in STOP_WORDS:
            return ""
        return cleaned

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"[^0-9a-zA-Z\s'\-\.]", " ", text.lower())

    def _get_or_create_wrestlers(self, names: List[str]) -> List[Wrestler]:
        wrestlers = []
        for name in names:
            wrestler = Wrestler.objects.filter(name__iexact=name).first()
            if not wrestler:
                wrestler = self._create_wrestler(name)
            if wrestler:
                wrestlers.append(wrestler)
        return self._dedupe(wrestlers)

    def _create_wrestler(self, name: str) -> Optional[Wrestler]:
        cleaned = name.strip()
        if not cleaned or cleaned.lower() in STOP_WORDS:
            return None
        if self.dry_run:
            self.stdout.write(f"  + Would create wrestler: {cleaned}")
            return Wrestler(name=cleaned)
        wrestler = Wrestler.objects.create(name=cleaned)
        self.stdout.write(f"  + Created wrestler: {cleaned}")
        self.wrestler_name_pairs.append((cleaned.lower(), wrestler))
        self.wrestler_name_pairs.sort(key=lambda item: len(item[0]), reverse=True)
        return wrestler

    @staticmethod
    def _dedupe(items: Iterable[Wrestler]) -> List[Wrestler]:
        seen = set()
        unique = []
        for item in items:
            key = item.pk if item.pk is not None else id(item)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique
