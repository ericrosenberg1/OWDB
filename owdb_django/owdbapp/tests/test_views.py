"""
Tests for OWDB views.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from ..models import Wrestler, Promotion, Event, Venue, UserProfile


class PublicViewsTest(TestCase):
    """Tests for public-facing views."""

    def setUp(self):
        self.client = Client()
        # Create some test data
        self.wrestler = Wrestler.objects.create(
            name="Test Wrestler",
            hometown="Test City"
        )
        self.promotion = Promotion.objects.create(
            name="Test Promotion",
            abbreviation="TP"
        )
        self.venue = Venue.objects.create(
            name="Test Arena",
            location="Test Location"
        )
        self.event = Event.objects.create(
            name="Test Event",
            promotion=self.promotion,
            venue=self.venue
        )

    def test_homepage(self):
        """Test homepage loads correctly."""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'OWDB')

    def test_wrestlers_list(self):
        """Test wrestlers list page."""
        response = self.client.get(reverse('wrestlers'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Wrestler')

    def test_wrestler_detail(self):
        """Test wrestler detail page."""
        response = self.client.get(reverse('wrestler_detail', args=[self.wrestler.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Wrestler')

    def test_wrestler_detail_by_slug(self):
        """Test wrestler detail page by slug."""
        response = self.client.get(reverse('wrestler_detail_slug', args=[self.wrestler.slug]))
        self.assertEqual(response.status_code, 200)

    def test_promotions_list(self):
        """Test promotions list page."""
        response = self.client.get(reverse('promotions'))
        self.assertEqual(response.status_code, 200)

    def test_events_list(self):
        """Test events list page."""
        response = self.client.get(reverse('events'))
        self.assertEqual(response.status_code, 200)

    def test_venues_list(self):
        """Test venues list page."""
        response = self.client.get(reverse('venues'))
        self.assertEqual(response.status_code, 200)

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'healthy'})

    def test_about_page(self):
        """Test about page."""
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

    def test_privacy_page(self):
        """Test privacy page."""
        response = self.client.get(reverse('privacy'))
        self.assertEqual(response.status_code, 200)


class SearchViewsTest(TestCase):
    """Tests for search functionality."""

    def setUp(self):
        self.client = Client()
        Wrestler.objects.create(name="John Cena", hometown="West Newbury")
        Wrestler.objects.create(name="CM Punk", hometown="Chicago")
        Wrestler.objects.create(name="Daniel Bryan", hometown="Aberdeen")

    def test_search_wrestlers(self):
        """Test searching wrestlers by name."""
        response = self.client.get(reverse('wrestlers'), {'q': 'John'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Cena')
        self.assertNotContains(response, 'CM Punk')

    def test_search_wrestlers_by_hometown(self):
        """Test searching wrestlers by hometown."""
        response = self.client.get(reverse('wrestlers'), {'q': 'Chicago'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CM Punk')

    def test_empty_search(self):
        """Test empty search returns all results."""
        response = self.client.get(reverse('wrestlers'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        # Should contain all wrestlers
        self.assertContains(response, 'John Cena')
        self.assertContains(response, 'CM Punk')

    def test_search_query_length_limit(self):
        """Test that very long search queries are truncated."""
        long_query = 'a' * 500
        response = self.client.get(reverse('wrestlers'), {'q': long_query})
        # Should not error
        self.assertEqual(response.status_code, 200)


class AuthenticationViewsTest(TestCase):
    """Tests for authentication views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        UserProfile.objects.create(
            user=self.user,
            email_verified=True,
            can_contribute=True
        )

    def test_login_page_loads(self):
        """Test login page loads."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_signup_page_loads(self):
        """Test signup page loads."""
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        self.assertRedirects(response, reverse('index'))

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username')

    def test_logout_requires_post(self):
        """Test that logout requires POST method."""
        self.client.login(username='testuser', password='testpassword123')
        # GET should fail
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

    def test_logout_with_post(self):
        """Test logout with POST method."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('index'))

    def test_authenticated_user_redirect_from_login(self):
        """Test that authenticated users are redirected from login page."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('index'))


class RateLimitingTest(TestCase):
    """Tests for rate limiting on auth views."""

    def setUp(self):
        self.client = Client()

    def test_signup_rate_limiting(self):
        """Test that signup is rate limited."""
        # Make 6 signup attempts (limit is 5)
        for i in range(6):
            response = self.client.post(reverse('signup'), {
                'username': f'testuser{i}',
                'email': f'test{i}@example.com',
                'password1': 'testpassword123',
                'password2': 'testpassword123'
            })

        # 6th attempt should show rate limit message
        self.assertContains(response, 'Too many signup attempts')

    def test_login_rate_limiting(self):
        """Test that login is rate limited."""
        # Make 11 login attempts (limit is 10)
        for i in range(11):
            response = self.client.post(reverse('login'), {
                'username': 'nonexistent',
                'password': 'wrongpassword'
            })

        # 11th attempt should show rate limit message
        self.assertContains(response, 'Too many login attempts')


class AccountViewsTest(TestCase):
    """Tests for account management views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        UserProfile.objects.create(user=self.user)

    def test_account_requires_login(self):
        """Test account page requires authentication."""
        response = self.client.get(reverse('account'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('account')}")

    def test_account_page_loads(self):
        """Test account page loads when logged in."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('account'))
        self.assertEqual(response.status_code, 200)
