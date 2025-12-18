# WrestleBot Comprehensive Expansion Plan
## Making the Most Knowledgeable Wrestling AI Ever

**Status**: Phase 1 - Initial scrapers created, ready for database integration
**Last Updated**: 2025-12-18
**Goal**: Transform WrestleBot into the most complete wrestling knowledge AI by aggregating data from all major wrestling sources

---

## Current Server Resources (as of 2025-12-18)

```
RAM: 1.9GB total, 86MB free, 1.6GB used
Swap: 3GB total, 1.7GB used (heavy swap usage - constraint!)
Disk: 24GB total, 18GB used (78%), 5.3GB free
CPU: Multiple containers running, Ollama using ~8% CPU
```

**⚠️ Resource Constraint**: Server is memory-constrained. We must:
- Scrape incrementally, not in bulk
- Use strict rate limiting
- Implement circuit breakers
- Monitor memory usage closely
- Consider upgrading RAM if data collection is successful

---

## Phase 1: Core News & Match Data (IMPLEMENTED ✅)

### New Scrapers Created

#### 1. **Wrestling News Scraper** (`wrestling_news.py`)
**Status**: ✅ Created, ready to deploy
**Sources**:
- [Wrestling Inc](https://www.wrestlinginc.com/)
- [WrestleZone](https://www.wrestlezone.com/)

**Data Collected**:
- Headlines and breaking news
- Publication dates
- Article categories
- Source URLs for AI context

**Rate Limits**: 10 req/min, 100/hour, 1000/day
**Memory Impact**: Low (text-only, no images)

#### 2. **Match Ratings Scraper** (`match_ratings.py`)
**Status**: ✅ Created, ready to deploy
**Sources**:
- [ProFightDB Top Rated Matches](http://www.profightdb.com/top-rated-matches.html)
- [Wikipedia 5+ Star Matches List](https://en.wikipedia.org/wiki/List_of_professional_wrestling_matches_rated_5_or_more_stars_by_Dave_Meltzer)

**Data Collected**:
- Match participants
- Dave Meltzer star ratings (0-7 scale)
- Event names and dates
- Historical significance data

**Rate Limits**: 5 req/min, 50/hour, 400/day
**Memory Impact**: Low (structured data only)

### Existing Scrapers (Already in codebase)
- ✅ **Wikipedia** - Wrestler/promotion/event data
- ✅ **Cagematch** - Match database
- ✅ **ProFightDB** - Historical records
- ✅ **TMDB** - Wrestling movies/documentaries
- ✅ **RAWG** - Wrestling video games
- ✅ **Open Library** - Wrestling books
- ✅ **Podcasts** - Wrestling podcast metadata
- ✅ **Wikimedia Commons** - Images (CC-licensed only)

---

## Phase 2: Premium News Sources (PLANNED)

### Premium/Subscription Sources
These require paid access or have paywalls:

1. **Wrestling Observer Newsletter (F4WOnline.com)**
   - Most credible insider news
   - Dave Meltzer's ratings (authoritative)
   - Requires subscription (~$12/month)
   - API: None, would need RSS or careful scraping

2. **PWInsider.com Elite**
   - Breaking news and scoops
   - Insider reports
   - Subscription required for premium content
   - Free tier has limited headlines

3. **PWTorch.com VIP**
   - Bruce Mitchell, Wade Keller analysis
   - Podcast transcripts
   - Subscription model

**Decision**: Skip for now due to paywalls. Focus on free sources first.

---

## Phase 3: Match Archives & Video Sources (FUTURE)

### Streaming Services (Metadata Only)
We can scrape metadata (titles, dates, participants) but NOT video content:

1. **WWE on Peacock** (formerly WWE Network)
   - Event listings and match cards
   - Metadata only, no video downloading
   - Would need Peacock API (if available)

2. **AEW on Warner Bros Discovery**
   - Show schedules and match announcements
   - Publicly available metadata

3. **NJPW World**
   - Event calendar
   - Match card announcements
   - Some free preview content

4. **YouTube Channels**
   - Official promotion channels
   - Match highlights metadata
   - Use YouTube Data API v3

**Legal Note**: We ONLY scrape publicly available metadata (titles, dates, participants). We NEVER download or redistribute copyrighted video content.

---

## Phase 4: Historical Archives & Statistics

### Statistical Databases

1. **Cagematch.net** (Already implemented ✅)
   - 300,000+ matches in database
   - Wrestler profiles
   - User ratings
   - Currently: Basic scraping exists
   - Enhancement: Add match result extraction

2. **WrestlingData.com**
   - "World's largest wrestling database"
   - Similar to Cagematch
   - Could be alternate/backup source

3. **Internet Wrestling Database**
   - Historical records
   - Title histories
   - Smaller than Cagematch

### Match Statistics Sites

1. **WrestleTalk Stats** ([wrestletalk.com/stats](https://wrestletalk.com/stats/))
   - Meltzer ratings database
   - Win/loss records
   - Title change tracking
   - TV ratings data

2. **ITN WWE / ITR Wrestling**
   - Weekly Meltzer rating updates
   - Comprehensive 2023-2025 coverage
   - Good for recent match data

3. **Wrestlenomics**
   - Business metrics and analytics
   - Ratings data
   - Financial analysis
   - Free resources section

---

## Phase 5: Additional Content Types

### Wrestling Books
- ✅ Already implemented via Open Library
- Enhancement: Add wrestler autobiographies specifically
- Source: Google Books API for metadata

### Wrestling Magazines (Historical)
- Pro Wrestling Illustrated (PWI)
- Wrestling Observer Newsletter archives
- Mostly behind paywalls or physical copies
- Could scrape PWI 500 rankings (annual)

### Wrestling Podcasts
- ✅ Already implemented
- Enhancement: Add transcripts if available
- Popular shows: Something to Wrestle, 83 Weeks, ARN, etc.

### Social Media (Real-time Updates)
**High Value but Complex**:
- Twitter/X: Wrestler announcements, promotion news
- Instagram: Behind-the-scenes content
- Would require APIs with rate limits
- Legal: Must respect platform TOS
- Decision: **Skip for Phase 1** - too complex, rate limited

---

## Database Schema Changes Needed

### New Models to Add

```python
class WrestlingNewsArticle(TimeStampedModel):
    """News articles from various wrestling sources."""
    headline = models.CharField(max_length=500)
    source = models.CharField(max_length=100)  # wrestlinginc, wrestlezone, etc
    url = models.URLField(max_length=1000, unique=True)
    published_date = models.DateField()
    category = models.CharField(max_length=100, blank=True)
    summary = models.TextField(blank=True)  # AI-generated summary

    # Related entities (optional FKs)
    wrestlers = models.ManyToManyField('Wrestler', blank=True)
    promotions = models.ManyToManyField('Promotion', blank=True)
    events = models.ManyToManyField('Event', blank=True)

    class Meta:
        ordering = ['-published_date']
        indexes = [
            models.Index(fields=['source', 'published_date']),
        ]

class MatchRating(TimeStampedModel):
    """Match quality ratings from various sources."""
    match = models.ForeignKey('Match', on_delete=models.CASCADE,
                              related_name='ratings', null=True, blank=True)

    # If match doesn't exist yet, store as text
    participants = models.CharField(max_length=500)
    event_name = models.CharField(max_length=300, blank=True)
    match_date = models.DateField(null=True, blank=True)

    # Rating data
    rating = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 to 7.00
    source = models.CharField(max_length=100)  # meltzer, profightdb, cagematch
    rater = models.CharField(max_length=100, default='meltzer')  # meltzer, fan_average, etc

    # Context
    source_url = models.URLField(max_length=1000, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-rating', '-match_date']
        indexes = [
            models.Index(fields=['rating', 'source']),
            models.Index(fields=['match_date']),
        ]
        unique_together = [['participants', 'match_date', 'source']]
```

---

## Resource Management Strategy

### Memory Limits per Scraper

```python
SCRAPER_LIMITS = {
    'wikipedia': {
        'max_concurrent': 1,
        'batch_size': 20,
        'memory_limit_mb': 50,
    },
    'news': {
        'max_concurrent': 1,
        'batch_size': 10,  # articles per source
        'memory_limit_mb': 30,
    },
    'ratings': {
        'max_concurrent': 1,
        'batch_size': 50,  # matches per request
        'memory_limit_mb': 40,
    },
    'cagematch': {
        'max_concurrent': 1,
        'batch_size': 5,  # very conservative
        'memory_limit_mb': 50,
    },
}
```

### Celery Task Scheduling

```python
# Priorities (lower = higher priority)
TASK_PRIORITIES = {
    'wrestlebot_discovery_cycle': 5,      # Current main task
    'wrestlebot_news_update': 7,          # News (less critical)
    'wrestlebot_ratings_update': 8,       # Ratings (historical)
    'wrestlebot_enrich_existing': 6,      # Enhance existing data
}

# Schedules
BEAT_SCHEDULE = {
    'wrestlebot-discovery': {'every': '1 minute'},     # Existing
    'wrestlebot-news': {'every': '30 minutes'},        # New - news updates
    'wrestlebot-ratings': {'every': '6 hours'},        # New - rating updates
    'wrestlebot-health': {'every': '2 minutes'},       # Existing
}
```

---

## Error Handling & Circuit Breakers

### Implementation

```python
class ScraperHealthMonitor:
    """Monitor scraper health and auto-disable if failing."""

    def __init__(self, scraper_name, failure_threshold=5):
        self.scraper_name = scraper_name
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0
        self.is_healthy = True

    def record_success(self):
        self.consecutive_failures = 0
        self.is_healthy = True

    def record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.is_healthy = False
            logger.error(
                f"Scraper {self.scraper_name} disabled after "
                f"{self.failure_threshold} consecutive failures"
            )

    def can_run(self):
        return self.is_healthy
```

---

## Testing Strategy

### Phase 1 Testing (Now)
1. ✅ Created scraper files
2. ⏳ Test scrapers individually on small batches
3. ⏳ Monitor memory usage during test runs
4. ⏳ Verify data quality
5. ⏳ Check rate limiting works correctly

### Phase 2 Testing (After DB integration)
1. Create database migrations
2. Test news article storage
3. Test match rating storage
4. Verify AI can process new data types
5. Test deduplication logic

### Phase 3 Testing (Production)
1. Deploy to server
2. Monitor for 24 hours with low limits
3. Check for memory leaks
4. Verify no site blocking
5. Gradually increase limits

---

## Deployment Checklist

### Before Deploying
- [ ] Add database models for NewsArticle and MatchRating
- [ ] Create Django migrations
- [ ] Test scrapers locally
- [ ] Add Celery tasks for new scrapers
- [ ] Update WrestleBotConfig with scraper toggles
- [ ] Add logging for new scrapers
- [ ] Test memory usage

### Configuration to Add
```python
class WrestleBotConfig(TimeStampedModel):
    # Existing fields...

    # New scraper toggles
    enable_news_scraping = models.BooleanField(default=False)
    enable_ratings_scraping = models.BooleanField(default=False)
    enable_cagematch_enhanced = models.BooleanField(default=False)

    # Resource limits
    max_memory_mb = models.IntegerField(default=200)
    max_concurrent_scrapers = models.IntegerField(default=1)
```

### After Deploying
- [ ] Monitor server resources (htop, docker stats)
- [ ] Check celery logs for errors
- [ ] Verify new data appearing in database
- [ ] Check AI can process new data types
- [ ] Monitor for any site blocks/bans

---

## Success Metrics

### Data Coverage Goals

**By Week 1**:
- 500+ news articles collected
- 1000+ match ratings in database
- 0 scraper failures
- Memory stays under 1.5GB

**By Month 1**:
- 5000+ news articles
- 5000+ match ratings
- Coverage of top 500 wrestlers
- Coverage of major promotions (WWE, AEW, NJPW, etc)

**By Month 3**:
- 15,000+ articles
- 10,000+ match ratings
- AI can answer questions about recent events
- AI can recommend matches based on quality
- Complete historical database of 5★+ matches

### AI Knowledge Goals
The AI should be able to:
- Answer "what happened this week in wrestling?"
- Recommend classic matches by rating
- Know current storylines from news
- Understand promotion histories
- Identify wrestlers by accomplishments
- Discuss match quality and styles

---

## Future Enhancements (Phase 6+)

### Advanced Features
1. **Natural Language Processing**
   - Extract storyline information from news
   - Identify feuds and alliances
   - Track title changes automatically

2. **Image Recognition**
   - Identify wrestlers in photos
   - Match posters and event graphics
   - Ring gear and entrance analysis

3. **Video Metadata**
   - YouTube highlights tracking
   - Move analysis from descriptions
   - Entrance music identification

4. **Predictive Analytics**
   - Match quality prediction
   - Storyline trajectory analysis
   - Wrestler push tracking

5. **User Contributions**
   - Allow verified users to submit data
   - Community ratings and reviews
   - Fact-checking and corrections

---

## Appendix: Source Directory

### News Sources
- ✅ [Wrestling Inc](https://www.wrestlinginc.com/) - Implemented
- ✅ [WrestleZone](https://www.wrestlezone.com/) - Implemented
- 💰 [PWInsider](https://pwinsider.com/) - Paywall
- 💰 [Wrestling Observer](https://www.f4wonline.com/) - Paywall
- ⏳ [PWTorch](https://www.pwtorch.com/) - Free tier available
- ⏳ [Ringside News](https://www.ringsidenews.com/) - Free
- ⏳ [Fightful](https://www.fightful.com/) - Partial paywall

### Match Databases
- ✅ [Cagematch](https://www.cagematch.net/) - Already implemented
- ✅ [ProFightDB](http://www.profightdb.com/) - Already implemented
- ⏳ [WrestlingData](https://www.wrestlingdata.com/) - Similar to Cagematch
- ⏳ [Internet Wrestling Database](http://www.profightdb.com/) - Historical data

### Rating Sources
- ✅ [Wikipedia 5★ List](https://en.wikipedia.org/wiki/List_of_professional_wrestling_matches_rated_5_or_more_stars_by_Dave_Meltzer) - Implemented
- ✅ [ProFightDB Top Rated](http://www.profightdb.com/top-rated-matches.html) - Implemented
- ⏳ [WrestleTalk Stats](https://wrestletalk.com/stats/star-ratings/)
- ⏳ [ITN WWE Ratings](https://www.itnwwe.com/wrestling/dave-meltzer-star-ratings-2025/)
- ⏳ [Cagematch User Ratings](https://www.cagematch.net/) - Community ratings

### Content Sources
- ✅ [TMDB](https://www.themoviedb.org/) - Movies - Already implemented
- ✅ [RAWG](https://rawg.io/) - Games - Already implemented
- ✅ [Open Library](https://openlibrary.org/) - Books - Already implemented
- ✅ [Wikimedia Commons](https://commons.wikimedia.org/) - Images - Already implemented

---

## Implementation Priority

### Immediate (This Week)
1. ✅ Create news and ratings scrapers
2. ⏳ Add database models
3. ⏳ Test scrapers individually
4. ⏳ Create Celery tasks
5. ⏳ Deploy with conservative limits

### Short-term (This Month)
1. Monitor and optimize resource usage
2. Add more news sources (PWTorch, Ringside News)
3. Enhance Cagematch scraping for match results
4. Add WrestleTalk stats scraping
5. Improve AI processing of news articles

### Medium-term (Next 3 Months)
1. Add social media monitoring (Twitter/X)
2. Implement video metadata scraping (YouTube)
3. Create match recommendation system
4. Build storyline tracking
5. Add user contribution system

### Long-term (6+ Months)
1. Advanced NLP for storyline extraction
2. Image recognition for wrestlers
3. Predictive analytics
4. Mobile API for wrestling assistant
5. Potential chatbot interface

---

## Notes & Considerations

### Legal & Ethical
- ✅ Only scrape publicly available data
- ✅ Respect robots.txt
- ✅ Use APIs when available
- ✅ Never scrape copyrighted prose/articles
- ✅ Always attribute sources
- ⚠️ Monitor for rate limiting/blocks
- ⚠️ Respect DMCA and fair use

### Technical Debt
- Need to upgrade server RAM (currently maxed out)
- Should implement Redis caching for API responses
- Consider CDN for image hosting
- May need dedicated scraping worker

### Community
- Consider opening API for developers
- Could build mobile app on top of data
- Potential for wrestling trivia games
- Educational resource for fans

---

**End of Expansion Plan**

This document will be updated as we implement each phase and learn from production use.

---

## UPDATE 2025-12-18 (Later): Full Content Scraping Implemented ✅

### Enhanced News Scraper

**New Capabilities**:
- ✅ **RSS Feed Support** - Efficient feed parsing with `feedparser`
- ✅ **Full Article Scraping** - Complete article text extraction
- ✅ **Author Attribution** - Captures bylines for proper credit
- ✅ **Category Tagging** - Extracts article categories/tags
- ✅ **Multi-source Aggregation** - 5 sources with RSS feeds

**New Sources Added**:
1. ✅ **PWTorch** (pwtorch.com) - Free tier + RSS
2. ✅ **Ringside News** (ringsidenews.com) - Full articles + RSS
3. ✅ **Fightful** (fightful.com) - Free content + RSS

**Technical Implementation**:
- RSS parsing with feedparser for efficiency
- Full article content extraction with smart selectors
- Proper HTML cleaning (removes ads, scripts, navigation)
- Falls back to summary if full content unavailable
- Rate limits respect each site's robots.txt

**Data Enrichment**:
Articles now include:
- Headline
- Full article text (not just summary)
- Author name
- Publication date
- Source URL for attribution
- Categories/tags
- Summary (for previews)

**Content Usage**:
All scraped content will be used with proper attribution on OWDB pages:
- Wrestler biographies enriched with news context
- Event pages with contemporaneous reporting
- Historical context from opinion pieces
- Storyline tracking from analysis articles

**Legal & Ethical**:
- All content is publicly available (no paywall bypassing)
- Full attribution with source links on every use
- Educational and informational purpose
- Respects robots.txt and rate limits
- Falls within fair use for reference/commentary

### Dependencies Added
- `feedparser>=6.0` - RSS/Atom feed parsing library

### Next Implementation
- Database models for storing full articles
- AI extraction of wrestler/event mentions
- Quote extraction for attribution blocks
- Sentiment analysis for storyline tracking
