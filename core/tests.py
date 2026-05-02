from django.test import TestCase, Client
from django.urls import reverse
from .models import User, Book, Chapter, Shard, Order, TemporalGrant
from .access import user_has_access_to
from django.utils import timezone
from datetime import timedelta
import json

class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            full_name="Test User",
            phone="+1234567890"
        )

    def test_login_success(self):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "test@example.com", "password": "password123"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user"]["email"], "test@example.com")
        self.assertEqual(data["user"]["full_name"], "Test User")
        self.assertTrue("sessionid" in response.cookies)

    def test_login_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "test@example.com", "password": "wrongpassword"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "invalid credentials")

    def test_logout(self):
        # Login first
        self.client.login(email="test@example.com", password="password123")
        
        response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 204)
        
        # Verify session is cleared (subsequent calls would be unauthenticated)
        self.assertNotIn("_auth_user_id", self.client.session)

class AccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password123",
            full_name="Test User",
            phone="+1234567890"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
            full_name="Other User",
            phone="+0987654321"
        )
        self.book = Book.objects.create(
            title="Test Book",
            slug="test-book",
            price_cents=1000
        )
        self.shard = Shard.objects.create(
            title="Test Shard",
            slug="test-shard"
        )
        self.chapter = Chapter.objects.create(
            book=self.book,
            order_index=1,
            title="Test Chapter",
            shard=self.shard
        )

    def test_no_order_no_access(self):
        self.assertFalse(user_has_access_to(self.user, self.chapter))

    def test_order_exists_but_no_grant_no_access(self):
        Order.objects.create(
            user=self.user,
            book=self.book,
            pace=Order.Pace.STEADY,
            stripe_session_id="sess_123",
            amount_cents=1000
        )
        self.assertFalse(user_has_access_to(self.user, self.chapter))

    def test_order_and_unlocked_grant_has_access(self):
        Order.objects.create(
            user=self.user,
            book=self.book,
            pace=Order.Pace.STEADY,
            stripe_session_id="sess_123",
            amount_cents=1000
        )
        TemporalGrant.objects.create(
            user=self.user,
            shard=self.shard,
            unlock_at=timezone.now() - timedelta(hours=1),
            expires_at=timezone.now() + timedelta(days=1),
            max_views=5
        )
        self.assertTrue(user_has_access_to(self.user, self.chapter))

    def test_order_and_locked_grant_no_access(self):
        Order.objects.create(
            user=self.user,
            book=self.book,
            pace=Order.Pace.STEADY,
            stripe_session_id="sess_123",
            amount_cents=1000
        )
        TemporalGrant.objects.create(
            user=self.user,
            shard=self.shard,
            unlock_at=timezone.now() + timedelta(hours=1),
            expires_at=timezone.now() + timedelta(days=1),
            max_views=5
        )
        self.assertFalse(user_has_access_to(self.user, self.chapter))

    def test_other_user_no_access(self):
        Order.objects.create(
            user=self.user,
            book=self.book,
            pace=Order.Pace.STEADY,
            stripe_session_id="sess_123",
            amount_cents=1000
        )
        TemporalGrant.objects.create(
            user=self.user,
            shard=self.shard,
            unlock_at=timezone.now() - timedelta(hours=1),
            expires_at=timezone.now() + timedelta(days=1),
            max_views=5
        )
        # self.user has access, but self.other_user should not
        self.assertFalse(user_has_access_to(self.other_user, self.chapter))


class GrantsApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.book = Book.objects.create(
            title="Pathfinder Codex",
            slug="pathfinder",
            price_cents=2500,
        )
        self.shard = Shard.objects.create(
            title="Mirror Paradox Shard",
            slug="mirror-paradox-shard",
        )
        self.chapter = Chapter.objects.create(
            book=self.book,
            order_index=3,
            title="The Mirror Paradox",
            shard=self.shard,
        )
        self.grant = TemporalGrant.objects.create(
            shard=self.shard,
            token="valid-token-001",
            unlock_at=timezone.now() - timedelta(hours=1),
            expires_at=timezone.now() + timedelta(days=1),
            max_views=5,
        )

    def test_get_grant_valid_returns_chapter_shape(self):
        response = self.client.get(f"/api/grants/{self.grant.token}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["chapter"]["title"], "The Mirror Paradox")
        self.assertEqual(data["chapter"]["order_index"], 3)
        self.assertEqual(data["chapter"]["book_title"], "Pathfinder Codex")
        self.assertEqual(data["shard_id"], "mirror-paradox-shard")
        self.assertIsNone(data["opened_at"])

    def test_get_grant_missing_token_404(self):
        response = self.client.get("/api/grants/no-such-token")
        self.assertEqual(response.status_code, 404)

    def test_get_grant_expired_404(self):
        self.grant.expires_at = timezone.now() - timedelta(hours=1)
        self.grant.save()
        response = self.client.get(f"/api/grants/{self.grant.token}")
        self.assertEqual(response.status_code, 404)

    def test_get_grant_exhausted_404(self):
        self.grant.current_views = self.grant.max_views
        self.grant.save()
        response = self.client.get(f"/api/grants/{self.grant.token}")
        self.assertEqual(response.status_code, 404)

    def test_get_grant_locked_403(self):
        self.grant.unlock_at = timezone.now() + timedelta(hours=1)
        self.grant.save()
        response = self.client.get(f"/api/grants/{self.grant.token}")
        self.assertEqual(response.status_code, 403)

    def test_open_grant_sets_opened_at(self):
        self.assertIsNone(self.grant.opened_at)
        response = self.client.post(f"/api/grants/{self.grant.token}/open")
        self.assertEqual(response.status_code, 200)
        self.grant.refresh_from_db()
        self.assertIsNotNone(self.grant.opened_at)

    def test_open_grant_idempotent(self):
        self.client.post(f"/api/grants/{self.grant.token}/open")
        self.grant.refresh_from_db()
        first_opened_at = self.grant.opened_at
        # Replay; opened_at must not change.
        self.client.post(f"/api/grants/{self.grant.token}/open")
        self.grant.refresh_from_db()
        self.assertEqual(self.grant.opened_at, first_opened_at)

    def test_open_grant_missing_token_404(self):
        response = self.client.post("/api/grants/no-such-token/open")
        self.assertEqual(response.status_code, 404)

    def test_open_grant_locked_403(self):
        self.grant.unlock_at = timezone.now() + timedelta(hours=1)
        self.grant.save()
        response = self.client.post(f"/api/grants/{self.grant.token}/open")
        self.assertEqual(response.status_code, 403)
        self.grant.refresh_from_db()
        self.assertIsNone(self.grant.opened_at)
