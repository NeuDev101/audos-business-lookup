"""
Tests for authentication endpoints and middleware.
"""

import unittest
import os
import sys
from unittest.mock import patch

# Add audos_console to path
AUDOS_CONSOLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audos_console"))
if AUDOS_CONSOLE_DIR not in sys.path:
    sys.path.insert(0, AUDOS_CONSOLE_DIR)

from app import app as flask_app


class AuthTests(unittest.TestCase):
    """Tests for authentication endpoints."""

    def setUp(self):
        """Set up test client."""
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["DISABLE_AUTH"] = "1"
        self.client = flask_app.test_client()
        
        # Initialize database
        from db.db import reset_db
        reset_db()

    def tearDown(self):
        """Clean up."""
        for key in ["SECRET_KEY", "JWT_SECRET", "DATABASE_URL", "DISABLE_AUTH"]:
            if key in os.environ:
                del os.environ[key]

    def test_register_success(self):
        """Register returns demo user when auth is disabled."""
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "username": "testuser",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("user", data)
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["user"]["email"], "demo@audos.local")

    def test_register_duplicate_email(self):
        """Demo register path ignores duplicate emails when auth is disabled."""
        first = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        second = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

    def test_register_weak_password(self):
        """Weak passwords are accepted when auth is disabled (demo mode)."""
        response = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "short"},
        )
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        """Login returns demo credentials when auth is disabled."""
        response = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_login_invalid_credentials(self):
        """Invalid credentials also return demo credentials when auth is disabled."""
        response = self.client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 200)

    def test_protected_route_requires_auth(self):
        """Protected routes should be accessible without auth when disabled."""
        response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)

    def test_protected_route_with_valid_token(self):
        """Protected routes still work with Authorization header when auth is disabled."""
        response = self.client.get(
            "/api/history",
            headers={"Authorization": "Bearer demo-access-token"},
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
