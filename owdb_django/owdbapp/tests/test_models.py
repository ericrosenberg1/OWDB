"""
Tests for OWDB models.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from ..models import (
    Wrestler,
    Promotion,
    Event,
    Venue,
    Title,
    Match,
    MatchParticipant,
    Stable,
    Podcast,
    PodcastEpisode,
    Book,
    Special,
    VideoGame,
    UserProfile,
    APIKey,
    EmailVerificationToken,
)


class WrestlerModelTest(TestCase):
    """Tests for the Wrestler model."""

    def test_wrestler_creation(self):
        """Test creating a wrestler with basic fields."""
        wrestler = Wrestler.objects.create(
            name="Stone Cold Steve Austin",
            real_name="Steve Williams",
            hometown="Victoria, Texas",
            debut_year=1989,
        )
        self.assertEqual(str(wrestler), "Stone Cold Steve Austin")
        self.assertEqual(wrestler.slug, "stone-cold-steve-austin")
        self.assertTrue(wrestler.is_active)

    def test_wrestler_retirement(self):
        """Test that retired wrestlers are marked correctly."""
        wrestler = Wrestler.objects.create(name="The Rock", debut_year=1996, retirement_year=2004)
        self.assertFalse(wrestler.is_active)

    def test_wrestler_aliases_list(self):
        """Test parsing comma-separated aliases."""
        wrestler = Wrestler.objects.create(
            name="Triple H", aliases="Hunter Hearst Helmsley, Terra Ryzing, Jean-Paul Levesque"
        )
        aliases = wrestler.get_aliases_list()
        self.assertEqual(len(aliases), 3)
        self.assertIn("Hunter Hearst Helmsley", aliases)

    def test_wrestler_slug_uniqueness(self):
        """Test that slugs are unique."""
        Wrestler.objects.create(name="Test Wrestler")
        wrestler2 = Wrestler.objects.create(name="Test Wrestler")
        # Second wrestler should have different slug
        self.assertNotEqual(wrestler2.slug, "test-wrestler")


class PromotionModelTest(TestCase):
    """Tests for the Promotion model."""

    def test_promotion_creation(self):
        """Test creating a promotion."""
        promo = Promotion.objects.create(
            name="World Wrestling Entertainment", abbreviation="WWE", founded_year=1952
        )
        self.assertEqual(str(promo), "World Wrestling Entertainment (WWE)")
        self.assertTrue(promo.is_active)

    def test_closed_promotion(self):
        """Test that closed promotions are marked correctly."""
        promo = Promotion.objects.create(
            name="World Championship Wrestling",
            abbreviation="WCW",
            founded_year=1988,
            closed_year=2001,
        )
        self.assertFalse(promo.is_active)


class VenueModelTest(TestCase):
    """Tests for the Venue model."""

    def test_venue_creation(self):
        """Test creating a venue."""
        venue = Venue.objects.create(
            name="Madison Square Garden", location="New York, NY", capacity=20789
        )
        self.assertEqual(str(venue), "Madison Square Garden")
        self.assertEqual(venue.slug, "madison-square-garden")


class EventModelTest(TestCase):
    """Tests for the Event model."""

    def setUp(self):
        self.promotion = Promotion.objects.create(name="WWE", abbreviation="WWE")
        self.venue = Venue.objects.create(name="WrestleMania Venue", location="Test City")

    def test_event_creation(self):
        """Test creating an event."""
        event = Event.objects.create(
            name="WrestleMania 40",
            promotion=self.promotion,
            venue=self.venue,
            date=timezone.now().date(),
        )
        self.assertEqual(str(event), f"WrestleMania 40 ({timezone.now().year})")


class UserProfileModelTest(TestCase):
    """Tests for the UserProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_profile_creation(self):
        """Test creating a user profile."""
        profile = UserProfile.objects.create(
            user=self.user, email_verified=False, can_contribute=False
        )
        self.assertEqual(str(profile), "Profile for testuser")
        self.assertFalse(profile.email_verified)


class APIKeyModelTest(TestCase):
    """Tests for the APIKey model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser", email="api@example.com", password="testpass123"
        )

    def test_api_key_generation(self):
        """Test API key generation."""
        key = APIKey.generate_key()
        self.assertEqual(len(key), 40)  # Should be 40 hex characters

    def test_api_key_creation(self):
        """Test creating an API key."""
        api_key = APIKey.objects.create(user=self.user, key=APIKey.generate_key(), name="Test Key")
        self.assertTrue(api_key.is_active)
        self.assertFalse(api_key.is_paid)

    def test_api_key_rate_limiting(self):
        """Test API key daily limit checking."""
        api_key = APIKey.objects.create(user=self.user, key=APIKey.generate_key())
        # Free tier should have 1000 limit
        self.assertTrue(api_key.check_rate_limit())


class EmailVerificationTokenTest(TestCase):
    """Tests for email verification tokens."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="verifyuser", email="verify@example.com", password="testpass123"
        )

    def test_token_generation(self):
        """Test token generation."""
        token = EmailVerificationToken.generate_token()
        self.assertEqual(len(token), 64)  # Should be 64 hex characters

    def test_token_expiry(self):
        """Test that tokens can expire."""
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token=EmailVerificationToken.generate_token(),
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        self.assertTrue(token.is_expired())

    def test_valid_token(self):
        """Test that fresh tokens are valid."""
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token=EmailVerificationToken.generate_token(),
            expires_at=timezone.now() + timezone.timedelta(hours=24),
        )
        self.assertFalse(token.is_expired())


class ReviewGateQuerySetTest(TestCase):
    """
    Tests for VerificationQuerySet.public() — the review gate.

    Policy under test: `.public()` is a blocklist on `rejected`, not an
    allowlist on `verified`. Production data has whole entity types that
    are almost entirely `candidate` (Title 100%, Promotion 88% at the time
    this gate was written), so an allowlist would empty those sections —
    see the policy note on VerificationQuerySet in models.py.
    """

    def test_public_excludes_rejected(self):
        Wrestler.objects.create(name="Rejected Wrestler", verification_state="rejected")
        Wrestler.objects.create(name="Good Wrestler", verification_state="verified")
        public_names = list(Wrestler.objects.public().values_list("name", flat=True))
        self.assertNotIn("Rejected Wrestler", public_names)
        self.assertIn("Good Wrestler", public_names)

    def test_public_keeps_candidate_and_provisional(self):
        """Regression test for the "just hide anything not verified" mistake."""
        Wrestler.objects.create(name="Candidate Wrestler", verification_state="candidate")
        Wrestler.objects.create(name="Provisional Wrestler", verification_state="provisional")
        public_names = list(Wrestler.objects.public().values_list("name", flat=True))
        self.assertIn("Candidate Wrestler", public_names)
        self.assertIn("Provisional Wrestler", public_names)

    def test_default_manager_stays_unfiltered(self):
        """
        `Model.objects.all()` / `.filter()` without `.public()` must still
        return rejected rows — Django Admin and the wrestlebot pipeline
        (e.g. wrestler_linking.py's manual rejected-state check) both
        depend on seeing every state through the default manager.
        """
        Promotion.objects.create(name="Rejected Promo", verification_state="rejected")
        self.assertTrue(Promotion.objects.filter(verification_state="rejected").exists())

    def test_related_manager_inherits_public(self):
        """
        A related manager off a gated model (e.g. `promotion.events`) gets
        `.public()` for free, since Django builds related managers as a
        subclass of the model's default manager class.
        """
        promo = Promotion.objects.create(name="Promo With Events")
        Event.objects.create(
            name="Rejected Event",
            promotion=promo,
            date=timezone.now().date(),
            verification_state="rejected",
        )
        Event.objects.create(
            name="Good Event",
            promotion=promo,
            date=timezone.now().date(),
            verification_state="verified",
        )
        public_events = list(promo.events.public().values_list("name", flat=True))
        self.assertNotIn("Rejected Event", public_events)
        self.assertIn("Good Event", public_events)


class ReviewGateRelationalLeakTest(TestCase):
    """
    A rejected entity must not leak through another entity's own "related
    object listing" helper methods — the query-level gate alone isn't
    enough if a detail page's cross-reference methods bypass it.
    """

    def setUp(self):
        self.promotion = Promotion.objects.create(name="Leak Test Promotion")
        self.title = Title.objects.create(name="Leak Test Title", promotion=self.promotion)
        self.event = Event.objects.create(
            name="Leak Test Event", promotion=self.promotion, date=timezone.now().date()
        )
        self.rejected_wrestler = Wrestler.objects.create(
            name="Rejected Champion", verification_state="rejected"
        )
        self.good_wrestler = Wrestler.objects.create(
            name="Good Champion", verification_state="verified"
        )

    def test_title_get_all_champions_excludes_rejected_wrestler(self):
        Match.objects.create(
            event=self.event,
            match_text="Rejected title win",
            title=self.title,
            winner=self.rejected_wrestler,
        )
        Match.objects.create(
            event=self.event,
            match_text="Good title win",
            title=self.title,
            winner=self.good_wrestler,
        )
        champion_names = list(self.title.get_all_champions().values_list("name", flat=True))
        self.assertNotIn("Rejected Champion", champion_names)
        self.assertIn("Good Champion", champion_names)

    def test_event_get_titles_defended_excludes_rejected_title(self):
        rejected_title = Title.objects.create(
            name="Rejected Title", promotion=self.promotion, verification_state="rejected"
        )
        Match.objects.create(
            event=self.event, match_text="Rejected title defense", title=rejected_title
        )
        Match.objects.create(event=self.event, match_text="Good title defense", title=self.title)
        defended_names = list(self.event.get_titles_defended().values_list("name", flat=True))
        self.assertNotIn("Rejected Title", defended_names)
        self.assertIn("Leak Test Title", defended_names)


class WrestlerRecordAndMetaCategoriesTest(TestCase):
    """Regression coverage for the owdbapp bug-fix sweep, item 5.

    get_win_loss_record() went from 8 sequential queries to 4, and
    get_all_meta_categories() went from 10 to 1, by folding independent
    .count() calls into aggregate() with conditional/distinct Count(). Both
    are meant to be query-plan changes only. This fixture pins the actual
    numbers, so a
    refactor that silently changes what gets counted (e.g. a join fan-out
    inflating a count, or an aggregate alias shadowing a relation name, both
    of which happened once during development of this fix) fails loudly
    instead of shipping a wrong "1,024 matches" or "0 rivals" onto a real
    wrestler's page.

    The fixture deliberately gives every many-to-many category (stables,
    podcast_appearances, books, video_games, specials) exactly 2 rows, and
    spreads matches across 3 events in 2 promotions with 3 different
    opponents. A fan-out bug in the consolidated aggregate() would multiply
    these together (e.g. reporting 32 instead of 2 for a category), not just
    round incorrectly, so this fixture would catch it.
    """

    def setUp(self):
        self.promotion1 = Promotion.objects.create(name="Promotion One", abbreviation="P1")
        self.promotion2 = Promotion.objects.create(name="Promotion Two", abbreviation="P2")
        self.title = Title.objects.create(name="World Title", promotion=self.promotion1)

        self.event1 = Event.objects.create(
            name="Event One", promotion=self.promotion1, date=timezone.datetime(2020, 1, 1).date()
        )
        self.event2 = Event.objects.create(
            name="Event Two", promotion=self.promotion1, date=timezone.datetime(2020, 2, 1).date()
        )
        self.event3 = Event.objects.create(
            name="Event Three", promotion=self.promotion2, date=timezone.datetime(2020, 3, 1).date()
        )

        self.wrestler = Wrestler.objects.create(name="Test Champion")
        self.opponent1 = Wrestler.objects.create(name="Opponent One")
        self.opponent2 = Wrestler.objects.create(name="Opponent Two")
        self.opponent3 = Wrestler.objects.create(name="Opponent Three")

        # M1: decided via the Match.winner FK only (no MatchParticipant rows
        # at all), no title. Win #1 (via the FK fallback path).
        self.match1 = Match.objects.create(
            event=self.event1,
            match_text="Champion vs Opponent One",
            outcome_type="pinfall",
            winner=self.wrestler,
        )
        self.match1.wrestlers.set([self.wrestler, self.opponent1])

        # M2: decided via MatchParticipant.is_winner (and also has winner=FK
        # set, matching real data) plus a title change. Win #2 (via the MP
        # path) and the one title win.
        self.match2 = Match.objects.create(
            event=self.event1,
            match_text="Champion vs Opponent Two (Title)",
            outcome_type="pinfall",
            winner=self.wrestler,
            title=self.title,
            title_changed=True,
        )
        self.match2.wrestlers.set([self.wrestler, self.opponent2])
        MatchParticipant.objects.create(match=self.match2, wrestler=self.wrestler, is_winner=True)
        MatchParticipant.objects.create(match=self.match2, wrestler=self.opponent2, is_winner=False)

        # M3: a 3-way draw. Counts toward draws, not wins/losses.
        self.match3 = Match.objects.create(
            event=self.event2,
            match_text="Three-way draw",
            outcome_type="draw",
        )
        self.match3.wrestlers.set([self.wrestler, self.opponent1, self.opponent2])

        # M4: decided via winning_side (no winner FK) plus MatchParticipant,
        # a title defense (title set, title_changed=False). Win #3, and a
        # second title_matches row that is NOT a title win.
        self.match4 = Match.objects.create(
            event=self.event3,
            match_text="Title defense",
            outcome_type="submission",
            winning_side=1,
            title=self.title,
            title_changed=False,
        )
        self.match4.wrestlers.set([self.wrestler, self.opponent3])
        MatchParticipant.objects.create(
            match=self.match4, wrestler=self.wrestler, is_winner=True, side=1
        )
        MatchParticipant.objects.create(
            match=self.match4, wrestler=self.opponent3, is_winner=False, side=0
        )

        # M5: no winner, no winning_side, no outcome_type, so unknown.
        self.match5 = Match.objects.create(
            event=self.event3,
            match_text="Result unclear",
        )
        self.match5.wrestlers.set([self.wrestler, self.opponent1])

        # Two rows in every other many-to-many category.
        self.stable1 = Stable.objects.create(name="Stable One")
        self.stable1.members.add(self.wrestler)
        self.stable2 = Stable.objects.create(name="Stable Two")
        self.stable2.members.add(self.wrestler)

        podcast = Podcast.objects.create(name="Wrestling Talk")
        self.episode1 = PodcastEpisode.objects.create(podcast=podcast, title="Episode One")
        self.episode1.guests.add(self.wrestler)
        self.episode2 = PodcastEpisode.objects.create(podcast=podcast, title="Episode Two")
        self.episode2.guests.add(self.wrestler)

        self.book1 = Book.objects.create(title="Book One")
        self.book1.related_wrestlers.add(self.wrestler)
        self.book2 = Book.objects.create(title="Book Two")
        self.book2.related_wrestlers.add(self.wrestler)

        self.game1 = VideoGame.objects.create(name="Game One")
        self.game1.wrestlers.add(self.wrestler)
        self.game2 = VideoGame.objects.create(name="Game Two")
        self.game2.wrestlers.add(self.wrestler)

        self.special1 = Special.objects.create(title="Special One")
        self.special1.related_wrestlers.add(self.wrestler)
        self.special2 = Special.objects.create(title="Special Two")
        self.special2.related_wrestlers.add(self.wrestler)

    def test_win_loss_record_matches_hand_computed_expectations(self):
        record = self.wrestler.get_win_loss_record()
        self.assertEqual(
            record,
            {
                "wins": 3,  # M1 (FK path), M2 (MP path), M4 (MP path)
                "losses": 0,
                "draws": 1,  # M3
                "unknown": 1,  # M5
                "total": 5,
                "win_percentage": 100.0,
                "title_matches": 2,  # M2, M4
                "title_wins": 1,  # M2 only (M4 is a defense, not a change)
            },
        )
        # The old "main_events" computation was dead (the annotation it used
        # was never applied to the filter or returned) and unused by any
        # template or caller anywhere in the repo; removed rather than fixed
        # into something that requires guessing a real "main event" rule.
        self.assertNotIn("main_events", record)

    def test_win_loss_record_query_count_is_four(self):
        """Pin the query-count win: 8 sequential queries -> 4."""
        with self.assertNumQueries(4):
            self.wrestler.get_win_loss_record()

    def test_all_meta_categories_matches_hand_computed_expectations(self):
        counts = self.wrestler.get_all_meta_categories()
        self.assertEqual(
            counts,
            {
                "matches": 5,
                "events": 3,  # event1, event2, event3
                "promotions": 2,  # promotion1 (event1/2), promotion2 (event3)
                "titles": 1,  # only self.title, from M2 and M4
                "stables": 2,
                "podcast_appearances": 2,
                "books": 2,
                "video_games": 2,
                "specials": 2,
                "rivals": 3,  # opponent1, opponent2, opponent3, no double count
            },
        )

    def test_all_meta_categories_query_count_is_one(self):
        """Pin the query-count win: 10 sequential queries -> 1."""
        with self.assertNumQueries(1):
            self.wrestler.get_all_meta_categories()

    def test_all_meta_categories_zero_matches_gives_zero_rivals(self):
        """Guard the co_participants-includes-self subtraction: a wrestler
        with no matches must report 0 rivals, not -1."""
        lonely = Wrestler.objects.create(name="Nobody Faced Them")
        counts = lonely.get_all_meta_categories()
        self.assertEqual(counts["matches"], 0)
        self.assertEqual(counts["rivals"], 0)


class WrestlerCompletenessScoreTest(TestCase):
    """get_completeness_score(): a real 0-100 weighted score that, before
    this change, was computed and never surfaced anywhere (see
    wrestler_detail.html's "Profile Completeness" info-block)."""

    def test_minimal_wrestler_scores_name_weight_only(self):
        wrestler = Wrestler.objects.create(name="Bare Wrestler")
        self.assertEqual(wrestler.get_completeness_score(), 10)

    def test_score_is_bounded_for_partial_profile(self):
        wrestler = Wrestler.objects.create(name="Partial Wrestler", hometown="Somewhere")
        score = wrestler.get_completeness_score()
        self.assertGreater(score, 0)
        self.assertLess(score, 100)

    def test_fully_populated_wrestler_with_a_match_scores_100(self):
        wrestler = Wrestler.objects.create(
            name="Complete Wrestler",
            real_name="Real Name",
            debut_year=1999,
            hometown="Hometown",
            nationality="American",
            finishers="Finisher Move",
            image_url="https://example.com/img.jpg",
            aliases="Alias",
            birth_date="1975-01-01",
            height="6'0\"",
            weight="220 lbs",
            trained_by="Some Trainer",
            signature_moves="Move",
            about="Bio text.",
            wikipedia_url="https://en.wikipedia.org/wiki/Complete_Wrestler",
        )
        promotion = Promotion.objects.create(name="Completeness Test Promotion")
        event = Event.objects.create(
            name="Completeness Test Event",
            promotion=promotion,
            date=timezone.now().date(),
        )
        match = Match.objects.create(event=event, match_text="Completeness Test Match")
        match.wrestlers.add(wrestler)

        self.assertEqual(wrestler.get_completeness_score(), 100)
