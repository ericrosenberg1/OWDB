"""
Utilities for surfacing how each entity is connected across the database.

Used to enrich the "about" field with linked-from context such as podcasts,
movies, PPVs, and other cross-media mentions.
"""

from typing import Iterable, List, Sequence, Tuple

from .models import (
    Book,
    Event,
    Match,
    Podcast,
    Promotion,
    Special,
    Title,
    Venue,
    VideoGame,
    Wrestler,
)


def _display_name(obj) -> str:
    """Get a human-friendly display name for an object."""
    for field in ("name", "title", "match_text"):
        value = getattr(obj, field, None)
        if value:
            return value
    return str(obj)


def _limit_objects(items: Iterable, limit: int = 5) -> Tuple[List[str], bool]:
    """
    Limit an iterable of model instances to a handful of names and report if more exist.
    """
    items_list = list(items[: limit + 1] if hasattr(items, "__getitem__") else items)
    has_more = len(items_list) > limit
    names = [_display_name(item) for item in items_list[:limit]]
    return _dedupe(names), has_more


def _limit_values(values: Sequence[str], limit: int = 5) -> Tuple[List[str], bool]:
    """Limit a sequence of strings and report if more exist."""
    value_list = list(values[: limit + 1] if hasattr(values, "__getitem__") else values)
    has_more = len(value_list) > limit
    names = [v for v in value_list[:limit] if v]
    return _dedupe(names), has_more


def _dedupe(items: List[str]) -> List[str]:
    """Preserve order while removing duplicates."""
    seen = set()
    unique_items = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique_items.append(item)
    return unique_items


def _format_sources(sources: List[Tuple[str, List[str], bool]]) -> str:
    """Build a readable summary string from collected sources."""
    parts = []
    for label, names, has_more in sources:
        if not names:
            continue

        summary = ", ".join(names)
        if has_more:
            summary = f"{summary} + more"
        parts.append(f"{label}: {summary}")

    if not parts:
        return ""

    return "Linked from " + "; ".join(parts)


def build_linked_from_summary(obj, limit: int = 5) -> str:
    """
    Collect linked-from context for a given model instance.

    Returns a human-friendly string (or empty string) that can be appended
    to "about" content.
    """
    sources: List[Tuple[str, List[str], bool]] = []

    if isinstance(obj, Wrestler):
        promotions, promo_more = _limit_objects(obj.get_promotions(), limit)
        events, events_more = _limit_values(
            obj.matches.values_list("event__name", flat=True).distinct(), limit
        )
        titles, titles_more = _limit_objects(obj.get_titles_won(), limit)
        podcasts, podcasts_more = _limit_values(
            obj.podcasts.values_list("name", flat=True), limit
        )
        books, books_more = _limit_values(
            obj.books.values_list("title", flat=True), limit
        )
        specials, specials_more = _limit_values(
            obj.specials.values_list("title", flat=True), limit
        )
        games, games_more = _limit_values(
            VideoGame.objects.filter(
                promotions__events__matches__wrestlers=obj
            )
            .distinct()
            .values_list("name", flat=True),
            limit,
        )

        sources.extend(
            [
                ("Promotions", promotions, promo_more),
                ("Events/PPVs", events, events_more),
                ("Titles", titles, titles_more),
                ("Podcasts", podcasts, podcasts_more),
                ("Books", books, books_more),
                ("Movies/Specials", specials, specials_more),
                ("Video Games", games, games_more),
            ]
        )

    elif isinstance(obj, Promotion):
        events, events_more = _limit_values(
            obj.events.order_by("-date").values_list("name", flat=True).distinct(),
            limit,
        )
        titles, titles_more = _limit_objects(obj.titles.all(), limit)
        wrestlers, wrestlers_more = _limit_values(
            obj.events.values_list("matches__wrestlers__name", flat=True).distinct(),
            limit,
        )
        games, games_more = _limit_values(
            obj.video_games.values_list("name", flat=True), limit
        )
        venues, venues_more = _limit_values(
            obj.events.values_list("venue__name", flat=True).distinct(), limit
        )

        sources.extend(
            [
                ("Events/PPVs", events, events_more),
                ("Titles", titles, titles_more),
                ("Featured Wrestlers", wrestlers, wrestlers_more),
                ("Video Games", games, games_more),
                ("Venues", venues, venues_more),
            ]
        )

    elif isinstance(obj, Event):
        wrestlers, wrestlers_more = _limit_values(
            obj.matches.values_list("wrestlers__name", flat=True).distinct(), limit
        )
        titles, titles_more = _limit_values(
            obj.matches.filter(title__isnull=False)
            .values_list("title__name", flat=True)
            .distinct(),
            limit,
        )
        promo = [obj.promotion.name] if obj.promotion else []
        venue = [obj.venue.name] if obj.venue else []

        sources.extend(
            [
                ("Promotion", promo, False),
                ("Venue", venue, False),
                ("Wrestlers", wrestlers, wrestlers_more),
                ("Titles Defended", titles, titles_more),
            ]
        )

    elif isinstance(obj, Title):
        champions, champs_more = _limit_values(
            obj.get_all_champions().values_list("name", flat=True).distinct(), limit
        )
        events, events_more = _limit_values(
            obj.title_matches.values_list("event__name", flat=True).distinct(), limit
        )
        promo = [obj.promotion.name] if obj.promotion else []

        sources.extend(
            [
                ("Promotion", promo, False),
                ("Champions", champions, champs_more),
                ("Events/PPVs", events, events_more),
            ]
        )

    elif isinstance(obj, Match):
        wrestlers, wrestlers_more = _limit_values(
            obj.wrestlers.values_list("name", flat=True), limit
        )
        event_name = [obj.event.name] if obj.event else []
        promotion = (
            [obj.event.promotion.name]
            if obj.event and obj.event.promotion
            else []
        )
        title = [obj.title.name] if obj.title else []

        sources.extend(
            [
                ("Event", event_name, False),
                ("Promotion", promotion, False),
                ("Participants", wrestlers, wrestlers_more),
                ("Title On The Line", title, False),
            ]
        )

    elif isinstance(obj, VideoGame):
        promotions, promos_more = _limit_values(
            obj.promotions.values_list("name", flat=True), limit
        )
        sources.append(("Promotions", promotions, promos_more))

    elif isinstance(obj, Podcast):
        wrestlers, wrestlers_more = _limit_values(
            obj.related_wrestlers.values_list("name", flat=True), limit
        )
        sources.append(("Featuring Wrestlers", wrestlers, wrestlers_more))

    elif isinstance(obj, Book):
        wrestlers, wrestlers_more = _limit_values(
            obj.related_wrestlers.values_list("name", flat=True), limit
        )
        sources.append(("Featuring Wrestlers", wrestlers, wrestlers_more))

    elif isinstance(obj, Special):
        wrestlers, wrestlers_more = _limit_values(
            obj.related_wrestlers.values_list("name", flat=True), limit
        )
        sources.append(("Featuring Wrestlers", wrestlers, wrestlers_more))

    elif isinstance(obj, Venue):
        events, events_more = _limit_values(
            obj.events.order_by("-date").values_list("name", flat=True).distinct(),
            limit,
        )
        promotions, promos_more = _limit_objects(obj.get_promotions(), limit)
        wrestlers, wrestlers_more = _limit_values(
            obj.get_wrestlers(limit=limit * 2).values_list("name", flat=True), limit
        )

        sources.extend(
            [
                ("Events/PPVs", events, events_more),
                ("Promotions", promotions, promos_more),
                ("Performing Wrestlers", wrestlers, wrestlers_more),
            ]
        )

    return _format_sources(sources)


def build_about_with_links(obj, limit: int = 5) -> str:
    """
    Combine the stored about text with linked-from context.
    """
    summary = build_linked_from_summary(obj, limit=limit)
    about_text = (getattr(obj, "about", None) or "").strip()

    if summary and about_text:
        return f"{about_text}\n\n{summary}"
    return summary or about_text
