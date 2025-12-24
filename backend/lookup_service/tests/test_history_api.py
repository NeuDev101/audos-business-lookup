"""
Tests for history API endpoints.
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
from db.models import insert_invoice


class HistoryAPITests(unittest.TestCase):
    """Tests for history API endpoints."""

    def setUp(self):
        """Set up test client and create test user."""
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["DISABLE_AUTH"] = "1"
        self.client = flask_app.test_client()
        
        # Initialize database
        from db.db import reset_db
        reset_db()
        
        # Create test user and get token
        register_response = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.token = register_response.get_json()["access_token"]
        self.user_id = register_response.get_json()["user"]["id"]
        self.other_user_id = 999

    def tearDown(self):
        """Clean up."""
        for key in ["SECRET_KEY", "JWT_SECRET", "DATABASE_URL", "DISABLE_AUTH"]:
            if key in os.environ:
                del os.environ[key]

    def test_get_history_empty(self):
        """Test getting history when no invoices exist."""
        response = self.client.get(
            "/api/history",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["invoices"]), 0)
        self.assertEqual(data["pagination"]["total"], 0)

    def test_get_history_with_invoices(self):
        """Test getting history with invoices."""
        # Insert test invoices
        insert_invoice(
            invoice_number="INV-001",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="hash1",
            user_id=self.user_id,
        )
        insert_invoice(
            invoice_number="INV-002",
            status="fail",
            issues_count=2,
            pdf_path=None,
            pdf_hash="hash2",
            user_id=self.user_id,
        )
        
        response = self.client.get(
            "/api/history",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["invoices"]), 2)
        self.assertEqual(data["pagination"]["total"], 2)

    def test_get_history_filters_by_user(self):
        """Test that history only returns invoices for the authenticated user."""
        # Insert invoice for user 1
        insert_invoice(
            invoice_number="INV-001",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="hash1",
            user_id=self.user_id,
        )
        
        # Insert invoice for a different user
        insert_invoice(
            invoice_number="INV-002",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice2.pdf",
            pdf_hash="hash2",
            user_id=self.other_user_id,
        )
        
        # Get history for user 1
        response = self.client.get(
            "/api/history",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["invoices"]), 1)
        self.assertEqual(data["invoices"][0]["invoice_number"], "INV-001")

    def test_get_history_with_status_filter(self):
        """Test history filtering by status."""
        insert_invoice(
            invoice_number="INV-001",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="hash1",
            user_id=self.user_id,
        )
        insert_invoice(
            invoice_number="INV-002",
            status="fail",
            issues_count=2,
            pdf_path=None,
            pdf_hash="hash2",
            user_id=self.user_id,
        )
        
        response = self.client.get(
            "/api/history?status=fail",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["invoices"]), 1)
        self.assertEqual(data["invoices"][0]["status"], "fail")

    def test_get_history_detail(self):
        """Test getting a specific invoice detail."""
        invoice = insert_invoice(
            invoice_number="INV-001",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="hash1",
            user_id=self.user_id,
        )
        
        response = self.client.get(
            f"/api/history/{invoice.id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["invoice_number"], "INV-001")

    def test_get_history_detail_not_found(self):
        """Test getting non-existent invoice returns 404."""
        response = self.client.get(
            "/api/history/99999",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 404)

    def test_get_history_detail_wrong_user(self):
        """Test that users can't access other users' invoices."""
        # Create invoice for other user
        invoice = insert_invoice(
            invoice_number="INV-001",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="hash1",
            user_id=self.other_user_id,
        )
        
        # Try to access it with first user's token
        response = self.client.get(
            f"/api/history/{invoice.id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
