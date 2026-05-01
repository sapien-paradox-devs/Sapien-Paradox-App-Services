from django.test import TestCase, Client
from django.urls import reverse
from .models import User
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
        # We can check if _auth_user_id is in session
        self.assertNotIn("_auth_user_id", self.client.session)
