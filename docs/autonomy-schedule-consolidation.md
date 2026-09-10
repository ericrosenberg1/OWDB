# Autonomy schedule consolidation

Two independent Celery schedules touch the same wrestling data today: the
legacy `owdbapp` scraper rotation and WrestleBot v3 (JR/Al/Earl). Neither
is running (`docker-compose.nuc.yml` pins `db`, `redis`, and `celery` to
`replicas: 0`, so nothing fires until a human flips that back on), but if
both were ever turned on at once they'd compete for the same external
sources. This doc lays out what each one actually does, exactly where
they overlap, and the options for consolidating them. It's a decision for
a human to make later, not something this pass changes. Both schedules
are untouched.

## The two schedules

**`owdbapp.tasks`, scheduled in `CELERY_BEAT_SCHEDULE` (`settings.py`).**
Predates WrestleBot. Rotates through Wikipedia, Cagematch, and ProFightDB
every 3 to 20 minutes pulling wrestlers/events/promotions
(`scrape-wikipedia-*`, `scrape-cagematch-*`, `scrape-profightdb-*`), fetches
Wikimedia Commons images for wrestlers/promotions/venues/titles/events
every 6 to 12 hours (`fetch-*-images`), and separately pulls movies (TMDB),
video games (RAWG), books (Google Books/Open Library), and podcasts
(iTunes/PodcastIndex) via their own dedicated APIs every 6 to 24 hours. It
also owns TV-episode tracking off TMDB (`poll-tv-episodes`,
`enrich-tv-episodes`, `backfill-tv-episodes`).

**WrestleBot v3, JR/Al/Earl.** Two implementations answer to these names
(see `wrestlebot/bots/__init__.py` for the full explanation):

- The **agent** cycles (`jr_agent_cycle`, `al_agent_cycle`,
  `earl_agent_cycle` in `wrestlebot/tasks.py`) are the ones actually wired
  into `CELERY_BEAT_SCHEDULE` today, every 30 minutes (JR, Al) or 6 hours
  (Earl). These are genuine Claude tool-use agents with a per-cycle budget
  cap.
- The **deterministic `wb_jr`/`wb_earl`** pipeline (`wrestlebot/bots/jr.py`,
  `bots/earl.py`) is not on the beat schedule at all. It only runs via a
  manual `python manage.py wb_jr` invocation, kept for cheap high-volume
  bulk processing rather than autonomous operation.

Either way, JR discovers, fetches, extracts, and persists wrestlers,
events, venues, promotions, titles, and media entities from Wikipedia
(plus Wikidata for cross-validation, and Cagematch/ProFightDB elsewhere in
the adapter set), runs its own Commons image-sweep cascade
(`wb_image_sweep`, `sources/commons.py`), and enforces a per-field
accuracy contract and provenance trail the legacy path doesn't have.

## Where they actually overlap

**Confirmed overlap: wrestler/event/promotion scraping.** Both
`scrape-wikipedia-wrestlers` and JR's discover/fetch/extract stages pull
the same wrestlers from the same Wikipedia articles. Both `owdbapp.tasks`
and `wrestlebot.sources.wikipedia` wrap the same
`owdbapp.scrapers.WikipediaScraper` class, and `scrape-cagematch-*` and
`wrestlebot.sources.cagematch` likewise both wrap the same
`owdbapp.scrapers.CagematchScraper`. That shared class gives them some
throttling coordination for free within a single process, but if the
class's rate limiting uses the older module-local-variable pattern (the
kind `wrestlebot/rate_limit.py`'s own docstring calls out as broken under
Celery prefork, since each worker process gets its own copy of the state),
two schedules running concurrently across worker processes could still
push combined traffic above what either one intends alone. ProFightDB is
the one case with no shared class at all:
`owdbapp.tasks.scrape_profightdb_wrestlers` uses
`owdbapp.scrapers.ProFightDBScraper`, while `wrestlebot.sources.profightdb`
is a separate, from-scratch implementation with its own Redis-backed
`rate_limited("profightdb", ...)` call. Two independent codebases, two
independent rate limits, no coordination between them.

**Confirmed overlap: Wikimedia Commons images.**
`owdbapp.tasks.fetch_wrestler_images` (and the promotion/venue/title/event
variants) use `owdbapp.scrapers.WikimediaCommonsClient` to pull images and
cache them to R2. WrestleBot's own image-sweep cascade
(`sources/commons.py`, just given a Redis-backed
`rate_limited("commons", per_second=1.0)` ceiling in this pass) does the
same job through a completely separate implementation with its own
license allow-list and FieldProvenance trail. These share no rate limit
and no dedup logic. Running both at once could hit Commons at up to twice
either one's intended ceiling, and could plausibly fetch and cache the
same wrestler's image twice through two different code paths.

**Not overlapping: TV episode tracking.** `poll-tv-episodes`,
`enrich-tv-episodes`, and `backfill-tv-episodes` pull WWE Raw/SmackDown/
NXT/Nitro episode data from TMDB. WrestleBot's own episode ingestion
(`wb_ingest_event_lists --episodes`, `pipeline/event_lists.py`) is
Wikipedia-based and deliberately limited to shows TMDB doesn't cover well
(AEW Dynamite/Collision, and, as of this pass, NJPW Strong and NWA
Powerrr). The two are complementary by design. The `event_lists.py` module
docstring says so explicitly.

**Not overlapping: video games, books, podcasts, movies/specials.**
`owdbapp.tasks` pulls these from dedicated APIs (RAWG, Google Books/Open
Library, iTunes/PodcastIndex, TMDB) using API keys and gets rich,
purpose-built metadata. WrestleBot's generic per-entity fetch
(`pipeline/fetch.py::fetch_book_candidates`,
`fetch_video_game_candidates`, `fetch_podcast_candidates`, and
`fetch_special_candidates`) defaults to `WikipediaAdapter` for all four
types. Confirmed by reading every call site (`bots/jr.py`,
`agents/tools.py`, `wb_fetch.py`), and none of them pass a different
adapter. So today these aren't duplicated effort. They're two different
data sources for the same entity types, and the dedicated-API path is
likely the richer one where it applies.

## DECIDED 2026-09-10: options 1 and 2, both applied

Eric chose to retire the legacy `owdbapp` wrestler/event/promotion scrapers **and** the legacy
Wikimedia Commons image fetch. WrestleBot is now the single wrestler-facing scrape and image
pipeline, keeping its accuracy contract and provenance trail. `owdbapp.tasks` keeps only what is
genuinely not duplicated: TV episodes off TMDB, plus movies, video games, books and podcasts from
their dedicated APIs, which are richer than WrestleBot's generic Wikipedia fetch for those types.

Twelve entries were removed from `CELERY_BEAT_SCHEDULE` in `owdb_django/settings.py`:
`scrape-wikipedia-{wrestlers,promotions,events}`, `scrape-cagematch-{wrestlers,events}`,
`scrape-profightdb-{wrestlers,events}`, and `fetch-{wrestler,promotion,venue,title,event}-images`.
**The task functions themselves are kept.** They are still reachable by hand and through the shared
scraper classes. Only the autonomous schedule is gone, so nothing is unrecoverable.

This closes both uncoordinated pairs described below. ProFightDB was the worse of the two, since
`owdbapp.scrapers.ProFightDBScraper` and `wrestlebot.sources.profightdb` are separate
implementations with separate rate limits and no way to see each other's traffic.

Safe to do cold: nothing was running. `docker-compose.nuc.yml` pins `db`, `redis` and `celery` to
`replicas: 0`, and on the NUC only `wrestlingdb-web-1` and `wrestlingdb-cloudflared-1` were up.
`get-scraper-stats` was deliberately left on the schedule. It only reports, and the scraper task
functions it reports on still exist.

## The options as they were written, kept for the reasoning

1. **Retire the legacy `owdbapp` wrestler/event/promotion scraper tasks**
   (`scrape-wikipedia-*`, `scrape-cagematch-*`, `scrape-profightdb-*`) now
   that JR covers the same ground with an accuracy contract the legacy
   path never had, but keep the image-fetch tasks, TV-episode tracking,
   and media-API tasks (TMDB/RAWG/Google Books/iTunes/PodcastIndex) since
   those aren't duplicated. This is the smallest change that removes the
   actual double-scraping risk. It leaves the Commons double-fetch risk in
   place unless paired with option 2.

2. **Also retire the legacy Commons image-fetch tasks** (or point them at
   wrestlebot's own pipeline), since `wrestlebot/sources/commons.py` now
   has its own rate-limited, license-gated, provenance-tracked image
   pipeline that does the same job. Combine with option 1 for a single
   wrestler-facing scraper/image pipeline (WrestleBot) and let
   `owdbapp.tasks` keep only what's genuinely unique to it (TV episodes,
   movies/games/books/podcasts).

3. **Keep both schedules as they are.** If they're ever turned on
   together, migrate the two truly uncoordinated pairs (ProFightDB,
   Commons images) onto a single shared rate-limit key each. For example,
   route `owdbapp.scrapers.ProFightDBScraper` and `WikimediaCommonsClient`
   through `wrestlebot/rate_limit.py`'s Redis-backed limiter, or the
   reverse, so at least the two schedules can't jointly exceed one
   intended ceiling, without deciding a winner between the two pipelines.
   This is the least disruptive option, but it leaves duplicated effort
   (and the double-fetch risk for images) in place indefinitely.

Nothing here has been merged, retired, or reconfigured. `CELERY_BEAT_SCHEDULE`
and `docker-compose.nuc.yml` are untouched by this pass.
