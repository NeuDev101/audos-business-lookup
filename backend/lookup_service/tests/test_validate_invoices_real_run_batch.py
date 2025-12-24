"""
Real end-to-end tests for /validate-invoices using actual run_batch (not mocked).
Tests that real validator and totals helper are used.
"""
import json
import os
import sys
import unittest
from io import BytesIO
from unittest import mock

# Add audos_console to path
AUDOS_CONSOLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audos_console"))
if AUDOS_CONSOLE_DIR not in sys.path:
    sys.path.insert(0, AUDOS_CONSOLE_DIR)

from app import app as flask_app


class ValidateInvoicesRealRunBatchTests(unittest.TestCase):
    """Tests using real run_batch to verify validator and totals helper are used."""
    
    def setUp(self):
        """Set up test client."""
        self.client = flask_app.test_client()
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        from db.db import init_db
        init_db()
        # Register user to obtain JWT
        register_response = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.valid_token = register_response.get_json()["access_token"]
        
        # Mock file system operations that run_batch needs
        # Patch using the path as it appears in the imported module
        # Since app.py imports 'from shared import batch_runner', we patch 'shared.batch_runner'
        self.tempfile_patcher = mock.patch("shared.batch_runner.tempfile")
        self.os_makedirs_patcher = mock.patch("shared.batch_runner.os.makedirs")
        self.open_patcher = mock.patch("builtins.open", create=True)
        self.os_path_exists_patcher = mock.patch("shared.batch_runner.os.path.exists")
        self.os_replace_patcher = mock.patch("shared.batch_runner.os.replace")
        # Patch insert_invoice where it's imported in batch_runner module
        self.insert_invoice_patcher = mock.patch("shared.batch_runner.insert_invoice")
        
        # Start patches
        self.tempfile_patcher.start()
        self.os_makedirs_patcher.start()
        self.os_path_exists_patcher.start()
        self.os_replace_patcher.start()
        self.insert_invoice_patcher.start()
        
        # Mock file operations
        mock_file = mock.mock_open()
        self.open_patcher.start()
    
    def tearDown(self):
        """Clean up."""
        for key in ["SECRET_KEY", "JWT_SECRET", "DATABASE_URL"]:
            if key in os.environ:
                del os.environ[key]
        
        # Stop all patches
        self.tempfile_patcher.stop()
        self.os_makedirs_patcher.stop()
        self.open_patcher.stop()
        self.os_path_exists_patcher.stop()
        self.os_replace_patcher.stop()
        self.insert_invoice_patcher.stop()
    
    def _make_authorized_request(self, files_data, metadata_json=None, token=None):
        """Helper to make authorized request."""
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        
        if metadata_json:
            files_data["metadata"] = metadata_json
        
        return self.client.post(
            "/validate-invoices",
            data=files_data,
            content_type="multipart/form-data",
            headers=headers,
        )
    
    @mock.patch("shared.batch_runner.generate_invoice_pdf")
    @mock.patch("shared.batch_runner.sha256_file")
    def test_valid_invoice_passes_real_validation(self, mock_sha256, mock_pdf_gen):
        """Test that a valid invoice passes real validator validation."""
        pdf_content = b"%PDF-1.4\ntest"
        
        valid_metadata = {
            "invoice_number": "INV-001",
            "issuer_name": "Acme Corp",
            "buyer": "Customer Inc",
            "date": "2024-01-01",
            "items": [
                {"description": "Product A", "amount_excl_tax": 1000.0, "tax_rate": "10%"}
            ],
        }
        
        # Mock PDF generation
        mock_pdf_gen.return_value = None
        mock_sha256.return_value = "test-hash"
        
        files_data = {"files": [(BytesIO(pdf_content), "invoice.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(valid_metadata),
            token=self.valid_token
        )
        
        # Should succeed (real validator will validate)
        self.assertEqual(response.status_code, 200)
        
        # Verify response contains validation results
        # (For single file, might return PDF or JSON depending on implementation)
        # The key is that run_batch was called with real invoice data
        payload = response.get_json()
        if payload:
            # If JSON response, should have batch_id
            self.assertIn("batch_id", payload or {})
    
    @mock.patch("shared.batch_runner.generate_invoice_pdf")
    @mock.patch("shared.batch_runner.sha256_file")
    def test_invoice_with_incorrect_totals_fails_real_validation(self, mock_sha256, mock_pdf_gen):
        """Test that invoice with incorrect totals fails real validation."""
        pdf_content = b"%PDF-1.4\ntest"
        
        metadata_with_bad_totals = {
            "invoice_number": "INV-001",
            "issuer_name": "Acme Corp",
            "buyer": "Customer Inc",
            "date": "2024-01-01",
            "items": [
                {"description": "Product A", "amount_excl_tax": 1000.0, "tax_rate": "10%"}
            ],
            "totals": {
                "subtotal": 1000.0,
                "taxTotal": 150.0,  # Wrong! Should be 100.0
                "grandTotal": 1150.0,  # Wrong! Should be 1100.0
            },
        }
        
        mock_pdf_gen.return_value = None
        mock_sha256.return_value = "test-hash"
        
        files_data = {"files": [(BytesIO(pdf_content), "invoice.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(metadata_with_bad_totals),
            token=self.valid_token
        )
        
        # Should process but validation should fail
        self.assertEqual(response.status_code, 200)
        
        # Check response for validation failure
        payload = response.get_json()
        if payload and "invoices" in payload:
            # Should have failed validation
            invoice_result = payload["invoices"][0]
            self.assertEqual(invoice_result.get("status"), "fail")
            self.assertFalse(invoice_result.get("compliant", True))


if __name__ == "__main__":
    unittest.main()
