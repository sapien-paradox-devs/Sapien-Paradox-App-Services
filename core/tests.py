from unittest.mock import patch, MagicMock

import stripe

from django.contrib.auth.hashers import check_password, identify_hasher
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


class PaymentsApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.book = Book.objects.create(
            title="Pathfinder Codex",
            slug="pathfinder",
            price_cents=2500,
        )
        self.payload = {
            "email": "buyer@example.com",
            "password": "SuperSecret123!",
            "full_name": "New Reader",
            "phone": "+15551234567",
            "book_slug": "pathfinder",
            "pace": "steady",
        }

    def _fake_session(self, session_id):
        return {
            "id": session_id,
            "amount_total": 2500,
            "metadata": {
                "email": "buyer@example.com",
                "password_hash": "hashed-pw-blob",
                "full_name": "New Reader",
                "phone": "+15551234567",
                "book_slug": "pathfinder",
                "pace": "steady",
            },
        }

    @patch("stripe.checkout.Session.create")
    def test_create_session_returns_url(self, mock_create):
        mock_create.return_value = MagicMock(url="https://checkout.stripe.com/c/pay/cs_test_123")
        response = self.client.post(
            "/api/payments/create-checkout-session",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"checkout_url": "https://checkout.stripe.com/c/pay/cs_test_123"},
        )

    @patch("stripe.checkout.Session.create")
    def test_create_session_hashes_password_in_metadata(self, mock_create):
        mock_create.return_value = MagicMock(url="https://stripe.example/x")
        self.client.post(
            "/api/payments/create-checkout-session",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        metadata = mock_create.call_args.kwargs["metadata"]
        self.assertNotIn(self.payload["password"], json.dumps(metadata))
        self.assertNotEqual(metadata["password_hash"], self.payload["password"])
        identify_hasher(metadata["password_hash"])  # raises if unrecognized
        self.assertTrue(check_password(self.payload["password"], metadata["password_hash"]))

    @patch("stripe.checkout.Session.create")
    def test_create_session_duplicate_email_409(self, mock_create):
        User.objects.create_user(
            email="buyer@example.com",
            password="anything",
            full_name="Existing",
            phone="+15551110000",
        )
        response = self.client.post(
            "/api/payments/create-checkout-session",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        mock_create.assert_not_called()

    @patch("stripe.checkout.Session.create")
    def test_create_session_unknown_book_400(self, mock_create):
        bad = dict(self.payload, book_slug="no-such-book")
        response = self.client.post(
            "/api/payments/create-checkout-session",
            data=json.dumps(bad),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        mock_create.assert_not_called()

    @patch("core.services.grants.create_for_order")
    @patch("core.services.whatsapp.send_chapter")
    @patch("stripe.Webhook.construct_event")
    def test_webhook_completed_creates_user_and_order(self, mock_event, mock_send, mock_grants):
        mock_grants.return_value = []
        mock_event.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": self._fake_session("cs_test_abc")},
        }
        response = self.client.post(
            "/api/payments/webhook",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="buyer@example.com").exists())
        order = Order.objects.get(stripe_session_id="cs_test_abc")
        self.assertEqual(order.book, self.book)
        self.assertEqual(order.pace, "steady")
        self.assertEqual(order.amount_cents, 2500)
        mock_send.assert_not_called()

    @patch("core.services.grants.create_for_order")
    @patch("core.services.whatsapp.send_chapter")
    @patch("stripe.Webhook.construct_event")
    def test_webhook_idempotent_replay_noops(self, mock_event, _mock_send, mock_grants):
        mock_grants.return_value = []
        mock_event.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": self._fake_session("cs_test_dup")},
        }
        for _ in range(2):
            response = self.client.post(
                "/api/payments/webhook",
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email="buyer@example.com").count(), 1)
        self.assertEqual(Order.objects.filter(stripe_session_id="cs_test_dup").count(), 1)
        # Replay short-circuits BEFORE create_for_order is called again.
        self.assertEqual(mock_grants.call_count, 1)

    @patch("stripe.Webhook.construct_event")
    def test_webhook_invalid_signature_400(self, mock_event):
        mock_event.side_effect = stripe.SignatureVerificationError("bad sig", "sig")
        response = self.client.post(
            "/api/payments/webhook",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "invalid signature")

    @patch("core.services.grants.create_for_order")
    @patch("core.services.whatsapp.send_chapter")
    @patch("stripe.Webhook.construct_event")
    def test_webhook_whatsapp_failure_does_not_block_200(self, mock_event, mock_send, mock_grants):
        shard = Shard.objects.create(title="Ch1 shard", slug="ch1-shard")
        Chapter.objects.create(book=self.book, order_index=1, title="Ch1", shard=shard)

        def _make_grants(order):
            return [TemporalGrant.objects.create(
                user=order.user,
                shard=shard,
                expires_at=timezone.now() + timedelta(days=1),
            )]

        mock_grants.side_effect = _make_grants
        mock_send.side_effect = RuntimeError("twilio outage")
        mock_event.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": self._fake_session("cs_test_wa_fail")},
        }
        response = self.client.post(
            "/api/payments/webhook",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.filter(stripe_session_id="cs_test_wa_fail").exists())
        mock_send.assert_called_once()


class SessionFromCheckoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.book = Book.objects.create(
            title="Pathfinder Codex", slug="pathfinder", price_cents=2500,
        )
        self.user = User.objects.create_user(
            email="buyer@example.com",
            password="anything",
            full_name="New Reader",
            phone="+15551234567",
        )
        self.order = Order.objects.create(
            user=self.user,
            book=self.book,
            pace="steady",
            stripe_session_id="cs_test_logmein",
            amount_cents=2500,
        )

    def test_session_from_checkout_logs_in_user(self):
        response = self.client.post(
            "/api/auth/session-from-checkout",
            data=json.dumps({"session_id": "cs_test_logmein"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "buyer@example.com")
        self.assertIn("sessionid", response.cookies)

    def test_session_from_checkout_unknown_session_404(self):
        response = self.client.post(
            "/api/auth/session-from-checkout",
            data=json.dumps({"session_id": "cs_test_no_such"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
