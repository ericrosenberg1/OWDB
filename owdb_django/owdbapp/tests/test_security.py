"""
Security tests for OWDB.
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User


class SecurityHeadersTest(TestCase):
    """Tests for security headers."""

    def setUp(self):
        self.client = Client()

    @override_settings(DEBUG=False)
    def test_x_frame_options(self):
        """Test X-Frame-Options header is set."""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.get('X-Frame-Options'), 'DENY')

    def test_content_type_options(self):
        """Test X-Content-Type-Options header."""
        response = self.client.get(reverse('index'))
        # This should be set by Django's SecurityMiddleware
        self.assertIn(response.get('X-Content-Type-Options', ''), ['nosniff', None])


class CSRFProtectionTest(TestCase):
    """Tests for CSRF protection."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username='csrfuser',
            email='csrf@example.com',
            password='testpassword123'
        )

    def test_login_requires_csrf(self):
        """Test that login POST requires CSRF token."""
        response = self.client.post(reverse('login'), {
            'username': 'csrfuser',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, 403)  # CSRF failure

    def test_logout_requires_csrf(self):
        """Test that logout POST requires CSRF token."""
        # Login first (without CSRF checks)
        client = Client()
        client.login(username='csrfuser', password='testpassword123')

        # Now try to logout with CSRF enforcement
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 403)


class OpenRedirectTest(TestCase):
    """Tests for open redirect prevention."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='redirectuser',
            email='redirect@example.com',
            password='testpassword123'
        )

    def test_login_prevents_open_redirect(self):
        """Test that login doesn't redirect to external URLs."""
        response = self.client.post(
            reverse('login') + '?next=https://evil.com',
            {
                'username': 'redirectuser',
                'password': 'testpassword123'
            }
        )
        # Should redirect to index, not external URL
        self.assertRedirects(response, reverse('index'))

    def test_login_allows_internal_redirect(self):
        """Test that login allows internal redirects."""
        response = self.client.post(
            reverse('login') + '?next=/wrestlers/',
            {
                'username': 'redirectuser',
                'password': 'testpassword123'
            }
        )
        # Should redirect to wrestlers page
        self.assertRedirects(response, '/wrestlers/')


class InputValidationTest(TestCase):
    """Tests for input validation."""

    def setUp(self):
        self.client = Client()

    def test_search_handles_special_characters(self):
        """Test that search handles special characters safely."""
        special_chars = "<script>alert('xss')</script>"
        response = self.client.get(reverse('wrestlers'), {'q': special_chars})
        self.assertEqual(response.status_code, 200)
        # XSS payload should be escaped
        self.assertNotContains(response, "<script>")

    def test_search_handles_sql_injection_attempt(self):
        """Test that search handles SQL injection attempts safely."""
        sql_injection = "'; DROP TABLE wrestlers; --"
        response = self.client.get(reverse('wrestlers'), {'q': sql_injection})
        self.assertEqual(response.status_code, 200)

    def test_signup_username_validation(self):
        """Test username validation on signup."""
        # Username too short
        response = self.client.post(reverse('signup'), {
            'username': 'ab',  # Less than 3 chars
            'email': 'test@example.com',
            'password1': 'testpassword123',
            'password2': 'testpassword123'
        })
        self.assertContains(response, 'at least 3 characters')

    def test_signup_password_mismatch(self):
        """Test password mismatch on signup."""
        response = self.client.post(reverse('signup'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpassword123',
            'password2': 'differentpassword'
        })
        self.assertContains(response, 'Passwords do not match')


class SessionSecurityTest(TestCase):
    """Tests for session security."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='sessionuser',
            email='session@example.com',
            password='testpassword123'
        )

    def test_session_created_on_login(self):
        """Test that session is created on login."""
        self.client.login(username='sessionuser', password='testpassword123')
        self.assertIn('sessionid', self.client.cookies)

    def test_session_destroyed_on_logout(self):
        """Test that session is destroyed on logout."""
        self.client.login(username='sessionuser', password='testpassword123')
        self.client.post(reverse('logout'))
        # Session cookie should be cleared
        self.assertEqual(self.client.cookies['sessionid'].value, '')
