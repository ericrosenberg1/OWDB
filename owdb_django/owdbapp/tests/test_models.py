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
