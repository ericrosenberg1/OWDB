"""
Utilities for surfacing how each entity is connected across the database.

Used to enrich the "about" field with linked-from context such as podcasts,
movies, PPVs, and other cross-media mentions.
"""

from typing import Iterable, List, Sequence, Tuple, Dict, Any, Optional

from django.urls import reverse

from .models import (
    Book,
    Event,
    Match,
    Podcast,
    PodcastEpisode,
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


def _build_url(obj) -> Optional[str]:
    """Build a detail URL for known model types."""
    if isinstance(obj, Wrestler):
        if obj.slug:
            return reverse("wrestler_detail_slug", args=[obj.slug])
        return reverse("wrestler_detail", args=[obj.pk])
    if isinstance(obj, Promotion):
        if obj.slug:
            return reverse("promotion_detail_slug", args=[obj.slug])
        return reverse("promotion_detail", args=[obj.pk])
    if isinstance(obj, Event):
        if obj.slug:
            return reverse("event_detail_slug", args=[obj.slug])
        return reverse("event_detail", args=[obj.pk])
    if isinstance(obj, Match):
        return reverse("match_detail", args=[obj.pk])
    if isinstance(obj, Title):
        if obj.slug:
            return reverse("title_detail_slug", args=[obj.slug])
        return reverse("title_detail", args=[obj.pk])
    if isinstance(obj, Venue):
        if obj.slug:
            return reverse("venue_detail_slug", args=[obj.slug])
        return reverse("venue_detail", args=[obj.pk])
    if isinstance(obj, VideoGame):
        if obj.slug:
            return reverse("game_detail_slug", args=[obj.slug])
        return reverse("game_detail", args=[obj.pk])
    if isinstance(obj, Podcast):
        if obj.slug:
            return reverse("podcast_detail_slug", args=[obj.slug])
        return reverse("podcast_detail", args=[obj.pk])
    if isinstance(obj, PodcastEpisode):
        if obj.slug:
            return reverse("episode_detail_slug", args=[obj.slug])
        return reverse("episode_detail", args=[obj.pk])
    if isinstance(obj, Book):
        if obj.slug:
            return reverse("book_detail_slug", args=[obj.slug])
        return reverse("book_detail", args=[obj.pk])
    if isinstance(obj, Special):
        if obj.slug:
            return reverse("special_detail_slug", args=[obj.slug])
        return reverse("special_detail", args=[obj.pk])
    return None


def _make_item(obj, year: str = "", meta: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Build a display-ready linked item dict."""
    return {
        "name": _display_name(obj),
        "url": _build_url(obj),
        "year": year or "",
        "meta": meta or [],
        "image_url": getattr(obj, "image_url", None),
    }


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


def _year_from_date(value) -> str:
    """Return a year string for a date-like value."""
    if value and hasattr(value, "year"):
        return str(value.year)
    return ""


def _meta_text(text: str, url: Optional[str] = None) -> Dict[str, Any]:
    """Create a metadata entry, optionally linked."""
    return {"text": text, "url": url} if url else {"text": text}


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


def build_linked_from_sections(obj, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Build rich, interlinked sections for related data.
    Returns a list of dicts: {label: str, items: [item, ...]}.
    """
    sections: List[Dict[str, Any]] = []

    if isinstance(obj, Wrestler):
        promo_years = {
            item["promotion_id"]: item for item in obj.get_promotion_history_with_years()
        }
        promotions = obj.get_promotions()[:limit]
        promo_items = []
        for promo in promotions:
            years = promo_years.get(promo.id)
            year_text = ""
            if years:
                start = years.get("start_year")
                end = years.get("end_year")
                if start and end:
                    year_text = f"{start}-{end}"
                elif start:
                    year_text = f"{start}-present"
                elif end:
                    year_text = f"?-{end}"
            meta = []
            if getattr(promo, "match_count", None) is not None:
                meta.append(_meta_text(f"{promo.match_count} matches"))
            promo_items.append(_make_item(promo, year=year_text, meta=meta))
        sections.append({"label": "Promotions", "items": promo_items})

        events = (
            Event.objects.filter(matches__wrestlers=obj)
            .select_related("promotion")
            .distinct()
            .order_by("-date")[:limit]
        )
        event_items = []
        for event in events:
            meta = []
            if event.promotion:
                meta.append(_meta_text(event.promotion.name, _build_url(event.promotion)))
            event_items.append(_make_item(event, year=_year_from_date(event.date), meta=meta))
        sections.append({"label": "Events/PPVs", "items": event_items})

        titles = obj.get_titles_won().select_related("promotion")[:limit]
        title_items = []
        for title in titles:
            meta = []
            if title.promotion:
                meta.append(_meta_text(title.promotion.name, _build_url(title.promotion)))
            year_text = str(title.debut_year) if title.debut_year else ""
            title_items.append(_make_item(title, year=year_text, meta=meta))
        sections.append({"label": "Titles", "items": title_items})

        episodes = obj.get_podcast_appearances()[:limit]
        podcast_items = []
        for episode in episodes:
            meta = []
            if episode.podcast:
                meta.append(_meta_text(episode.podcast.name, _build_url(episode.podcast)))
            podcast_items.append(_make_item(episode, year=_year_from_date(episode.published_date), meta=meta))
        sections.append({"label": "Podcast Appearances", "items": podcast_items})

        books = obj.get_books()[:limit]
        book_items = []
        for book in books:
            meta = []
            if book.author:
                meta.append(_meta_text(book.author))
            year_text = str(book.publication_year) if book.publication_year else ""
            book_items.append(_make_item(book, year=year_text, meta=meta))
        sections.append({"label": "Books", "items": book_items})

        specials = obj.get_specials()[:limit]
        special_items = []
        for special in specials:
            year_text = str(special.release_year) if special.release_year else ""
            special_items.append(_make_item(special, year=year_text))
        sections.append({"label": "Documentaries & Specials", "items": special_items})

        games = obj.get_video_games()[:limit]
        game_items = []
        for game in games:
            year_text = str(game.release_year) if game.release_year else ""
            game_items.append(_make_item(game, year=year_text))
        sections.append({"label": "Video Games", "items": game_items})

    elif isinstance(obj, Promotion):
        events = obj.events.select_related("venue").order_by("-date")[:limit]
        event_items = []
        for event in events:
            meta = []
            if event.venue:
                meta.append(_meta_text(event.venue.name, _build_url(event.venue)))
            event_items.append(_make_item(event, year=_year_from_date(event.date), meta=meta))
        sections.append({"label": "Events/PPVs", "items": event_items})

        titles = obj.titles.all()[:limit]
        title_items = []
        for title in titles:
            year_text = str(title.debut_year) if title.debut_year else ""
            meta = []
            status = "Active" if title.is_active else "Retired"
            meta.append(_meta_text(status))
            title_items.append(_make_item(title, year=year_text, meta=meta))
        sections.append({"label": "Titles", "items": title_items})

        wrestlers = obj.get_all_wrestlers(limit=limit)
        wrestler_items = []
        for wrestler in wrestlers:
            meta = []
            if getattr(wrestler, "match_count", None) is not None:
                meta.append(_meta_text(f"{wrestler.match_count} matches"))
            wrestler_items.append(_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "", meta=meta))
        sections.append({"label": "Featured Wrestlers", "items": wrestler_items})

        games = obj.video_games.all()[:limit]
        game_items = []
        for game in games:
            year_text = str(game.release_year) if game.release_year else ""
            game_items.append(_make_item(game, year=year_text))
        sections.append({"label": "Video Games", "items": game_items})

        venues = obj.get_venues(limit=limit)
        venue_items = []
        for venue in venues:
            meta = []
            if getattr(venue, "event_count", None) is not None:
                meta.append(_meta_text(f"{venue.event_count} events"))
            venue_items.append(_make_item(venue, meta=meta))
        sections.append({"label": "Venues", "items": venue_items})

    elif isinstance(obj, Event):
        if obj.promotion:
            sections.append({"label": "Promotion", "items": [_make_item(obj.promotion)]})
        if obj.venue:
            sections.append({"label": "Venue", "items": [_make_item(obj.venue)]})

        wrestlers = obj.get_all_wrestlers()[:limit]
        wrestler_items = [_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "") for wrestler in wrestlers]
        sections.append({"label": "Wrestlers", "items": wrestler_items})

        titles = obj.get_titles_defended()[:limit]
        title_items = []
        for title in titles:
            meta = []
            if title.promotion:
                meta.append(_meta_text(title.promotion.name, _build_url(title.promotion)))
            title_items.append(_make_item(title, year=str(title.debut_year) if title.debut_year else "", meta=meta))
        sections.append({"label": "Titles Defended", "items": title_items})

    elif isinstance(obj, Title):
        if obj.promotion:
            sections.append({"label": "Promotion", "items": [_make_item(obj.promotion)]})

        champions = obj.get_all_champions()[:limit]
        champion_items = []
        for champion in champions:
            champion_items.append(_make_item(champion, year=str(champion.debut_year) if champion.debut_year else ""))
        sections.append({"label": "Champions", "items": champion_items})

        events = (
            Event.objects.filter(matches__title=obj)
            .select_related("promotion")
            .distinct()
            .order_by("-date")[:limit]
        )
        event_items = []
        for event in events:
            meta = []
            if event.promotion:
                meta.append(_meta_text(event.promotion.name, _build_url(event.promotion)))
            event_items.append(_make_item(event, year=_year_from_date(event.date), meta=meta))
        sections.append({"label": "Events/PPVs", "items": event_items})

    elif isinstance(obj, Match):
        if obj.event:
            sections.append({"label": "Event", "items": [_make_item(obj.event, year=_year_from_date(obj.event.date))]})
        if obj.event and obj.event.promotion:
            sections.append({"label": "Promotion", "items": [_make_item(obj.event.promotion)]})

        participants = obj.wrestlers.all()[:limit]
        participant_items = [_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "") for wrestler in participants]
        sections.append({"label": "Participants", "items": participant_items})

        if obj.title:
            sections.append({"label": "Title On The Line", "items": [_make_item(obj.title, year=str(obj.title.debut_year) if obj.title.debut_year else "")]})

    elif isinstance(obj, VideoGame):
        promotions = obj.promotions.all()[:limit]
        promo_items = [_make_item(promo, year=str(promo.founded_year) if promo.founded_year else "") for promo in promotions]
        sections.append({"label": "Promotions", "items": promo_items})

    elif isinstance(obj, Podcast):
        wrestlers = obj.related_wrestlers.all()[:limit]
        wrestler_items = [_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "") for wrestler in wrestlers]
        sections.append({"label": "Featuring Wrestlers", "items": wrestler_items})

    elif isinstance(obj, PodcastEpisode):
        if obj.podcast:
            sections.append({"label": "Podcast", "items": [_make_item(obj.podcast)]})
        guests = obj.guests.all()[:limit]
        guest_items = [_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "") for wrestler in guests]
        sections.append({"label": "Guests", "items": guest_items})

    elif isinstance(obj, Book):
        wrestlers = obj.related_wrestlers.all()[:limit]
        wrestler_items = [_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "") for wrestler in wrestlers]
        sections.append({"label": "Featuring Wrestlers", "items": wrestler_items})

    elif isinstance(obj, Special):
        wrestlers = obj.related_wrestlers.all()[:limit]
        wrestler_items = [_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "") for wrestler in wrestlers]
        sections.append({"label": "Featuring Wrestlers", "items": wrestler_items})

    elif isinstance(obj, Venue):
        events = obj.events.order_by("-date")[:limit]
        event_items = []
        for event in events:
            meta = []
            if event.promotion:
                meta.append(_meta_text(event.promotion.name, _build_url(event.promotion)))
            event_items.append(_make_item(event, year=_year_from_date(event.date), meta=meta))
        sections.append({"label": "Events/PPVs", "items": event_items})

        promotions = obj.get_promotions()[:limit]
        promo_items = []
        for promo in promotions:
            meta = []
            if getattr(promo, "event_count", None) is not None:
                meta.append(_meta_text(f"{promo.event_count} events"))
            promo_items.append(_make_item(promo, year=str(promo.founded_year) if promo.founded_year else "", meta=meta))
        sections.append({"label": "Promotions", "items": promo_items})

        wrestlers = obj.get_wrestlers(limit=limit)
        wrestler_items = []
        for wrestler in wrestlers:
            meta = []
            if getattr(wrestler, "appearance_count", None) is not None:
                meta.append(_meta_text(f"{wrestler.appearance_count} appearances"))
            wrestler_items.append(_make_item(wrestler, year=str(wrestler.debut_year) if wrestler.debut_year else "", meta=meta))
        sections.append({"label": "Performing Wrestlers", "items": wrestler_items})

    return [section for section in sections if section.get("items")]


def build_about_with_links(obj, limit: int = 5) -> str:
    """
    Combine the stored about text with linked-from context.
    """
    about_text = (getattr(obj, "about", None) or "").strip()
    return about_text
