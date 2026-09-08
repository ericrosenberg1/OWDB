# OWDB user rating system — design

Status: **Draft** — model stub merged in migration 0026; UI + aggregation not built.

## Goals

1. Logged-in OWDB users can rate any entity (wrestlers, events, matches, titles, stables, promotions, TV shows, specials, books, video games, podcasts, theme songs).
2. Ratings drive site-wide aggregate views:
   - **Trending wrestlers** (rolling-window favorite/rating velocity).
   - **Best matches of all time** (Bayesian-weighted user score, blended with Cagematch & Observer ratings).
   - **Historic events leaderboard** (best WrestleMania ever, best WCW PPV ever).
   - **User favorites** — each user has a personal "my list" page per entity type.
3. Reviews are first-class: users can attach prose; reviews surface on entity pages.
4. The aggregation is **anti-gameable** — no single user can swing a ranking, and brand-new accounts are weighted toward zero.

## Model

Stub (in `owdb_django/owdbapp/models.py`):

```python
class UserRating(TimeStampedModel):
    user            = FK auth.User
    entity_type     = "wrestler"|"event"|"match"|"title"|"stable"|"promotion"|
                       "tv_show"|"special"|"book"|"video_game"|"podcast"|"theme_song"
    entity_id       = positive integer
    rating          = 1..10 nullable    # nullable so a user can favorite without rating
    is_favorite     = boolean
    review_text     = text (optional)
    created_at / updated_at
    unique(user, entity_type, entity_id)
```

That's enough for v1. Indexes already cover the read patterns: by entity, by user, by favorite.

## Aggregation table (next migration)

Computed periodically (Celery beat — every hour for trending, daily for all-time):

```python
class UserRatingAggregate(TimeStampedModel):
    entity_type           = same choices as UserRating
    entity_id             = positive integer
    window                = "all_time" | "30d" | "7d"
    rating_count          = int
    favorite_count        = int
    rating_mean           = float          # raw arithmetic mean
    rating_bayesian       = float          # see formula below
    review_count          = int
    refreshed_at          = datetime
    unique(entity_type, entity_id, window)
```

**Bayesian rating** (the right formula for "best match of all time"):

```
B = (m * C + S) / (m + N)

where
    N = rating_count for this entity
    S = sum of ratings for this entity
    C = global mean rating across all entities of this type
    m = "prior weight" — choose 10 to start, tune later

Pseudocode equivalent: B = (10*C + sum_ratings) / (10 + count)
```

Entities with 1-2 ratings get pulled toward the global mean. Entities with 50+ ratings approach their true mean. This is the same approach IMDB uses for Top 250.

For **trending**, decay weight more aggressively:

```
T = sum(rating_i * exp(-age_days_i / 7)) / N_recent
```

## Anti-abuse

- New accounts (< 30 days) count at **20% weight** toward aggregates.
- One rating per user per entity (DB-unique). Updates allowed; history preserved via `updated_at`.
- IP + cookie fingerprint logged on rating create for offline anomaly detection (not blocking).
- Bulk-rating velocity rate limit: 60 ratings/day per user (high enough for power users, low enough to catch botting).
- Earl audits aggregate spikes (rule: `rating_velocity_anomaly`) and can flag entities for human review.

## UI surfaces

1. **Entity pages** get a 1-10 star widget + "Add to favorites" toggle + optional review textarea.
2. **Aggregate pages**:
   - `/top/wrestlers/` — top-200 wrestlers by Bayesian rating
   - `/top/matches/` — top-200 matches by Bayesian rating (filterable by year, promotion)
   - `/trending/wrestlers/` — top 30 by trending score (last 7 days)
   - `/u/<user>/favorites/` — personal favorites list, grouped by entity type
3. **Discover page** features cross-section: "users who liked X also liked Y" via simple cosine similarity across the rating matrix.

## Phasing

1. **Phase 1** (next session): build `UserRatingAggregate`, the Celery refresh task, and the rating widget on the wrestler detail page only. Ship and let people start rating.
2. **Phase 2**: add aggregate pages (`/top/...`).
3. **Phase 3**: trending + recommendations.
4. **Phase 4**: review moderation tools, integration with Earl's anomaly detection.

## Integration with existing internal rankings

OWDB already has `Hot100Ranking` (proprietary monthly algorithm) and now
`ExternalRanking` (PWI 500 / Observer). User ratings are a third leg:

- `Hot100Ranking` = our editorial / algorithmic monthly view
- `ExternalRanking` = third-party authoritative lists
- `UserRatingAggregate` = community wisdom

All three should be visible on a wrestler page — they're complementary, not competing.

## Open questions

- 1-10 vs 1-5 (with halves) for the input UI? **Default to 1-10 integer for simplicity.**
- Allow anonymous ratings via cookie? **No — too easy to game; require login.**
- Surface reviews on entity pages immediately or with a delay? **Immediate, but flag low-trust users for soft-shadow review.**
