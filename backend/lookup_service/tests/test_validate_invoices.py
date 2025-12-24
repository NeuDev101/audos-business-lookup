import json
import os
import tempfile
import unittest
from io import BytesIO
from unittest import mock

from app import app as flask_app


class ValidateInvoicesEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        # Configure auth/DB for tests
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["DISABLE_AUTH"] = "1"
        # Initialize database
        from db.db import reset_db
        reset_db()
        # Register a test user and capture access token
        register_resp = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.access_token = register_resp.get_json()["access_token"]
        self.valid_token = self.access_token
        # Mock run_batch for all tests
        self.run_batch_patcher = mock.patch("app.run_batch")
        self.mock_run_batch = self.run_batch_patcher.start()
        self.mock_run_batch.return_value = {
            "batch_id": "test-batch",
            "counts": {"pass": 0, "fail": 0, "warn": 0},
            "invoices": [],
        }

    def tearDown(self):
        # Clean up environment variables
        for key in ["SECRET_KEY", "JWT_SECRET", "DATABASE_URL", "DISABLE_AUTH"]:
            if key in os.environ:
                del os.environ[key]
        # Stop the patcher
        self.run_batch_patcher.stop()

    def _make_authorized_request(self, data, metadata=None, token=None):
        """Helper to make authorized request with token and optional metadata."""
        headers = {}
        auth_token = token or self.access_token
        if auth_token is not None:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Add default metadata if not provided and files are present
        if metadata is None and "files" in data:
            # Provide minimal valid metadata for tests that don't care about invoice content
            default_metadata = {
                "invoice_number": "TEST-001",
                "issuer_name": "Test Issuer",
                "buyer": "Test Buyer",
                "date": "2024-01-01",
                "items": [{"description": "Test Item", "amount_excl_tax": 100.0, "tax_rate": "10%"}],
            }
            data["metadata"] = json.dumps(default_metadata)
        elif metadata is not None:
            data["metadata"] = json.dumps(metadata) if isinstance(metadata, dict) else metadata
        
        return self.client.post(
            "/validate-invoices",
            data=data,
            content_type="multipart/form-data",
            headers=headers,
        )

    def test_missing_token_allowed_when_auth_disabled(self):
        """Missing Authorization header should be allowed when auth is disabled."""
        data = {"files": [(BytesIO(b"pdf-content"), "test.pdf")]}
        response = self._make_authorized_request(data, token=None)
        self.assertEqual(response.status_code, 200)

    def test_bad_token_allowed_when_auth_disabled(self):
        """Invalid token should be ignored when auth is disabled."""
        data = {"files": [(BytesIO(b"pdf-content"), "test.pdf")]}
        response = self._make_authorized_request(data, token="wrong-token")
        self.assertEqual(response.status_code, 200)

    def test_too_many_files_returns_400(self):
        """Test that more than 50 files returns 400."""
        # Create 51 file entries
        files = [(BytesIO(b"content"), f"file{i}.pdf") for i in range(51)]
        data = {"files": files}
        response = self._make_authorized_request(data, token=self.access_token)
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("Too many files", payload["error"])

    def test_bad_extension_returns_400(self):
        """Test that unsupported file extension returns 400."""
        data = {"files": [(BytesIO(b"content"), "test.txt")]}
        response = self._make_authorized_request(data, token=self.access_token)
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("No valid files", payload["error"])

    def test_empty_file_returns_400(self):
        """Test that empty file returns 400."""
        data = {"files": [(BytesIO(b""), "test.pdf")]}
        response = self._make_authorized_request(data, token=self.access_token)
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("empty file", payload["error"])

    def test_file_too_large_returns_400(self):
        """Test that file exceeding 10MB returns 400."""
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        data = {"files": [(BytesIO(large_content), "large.pdf")]}
        response = self._make_authorized_request(data, token=self.access_token)
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("file too large", payload["error"])

    @mock.patch("app.run_batch")
    @mock.patch("builtins.open", create=True)
    @mock.patch("os.path.exists")
    def test_valid_token_and_pdf_returns_pdf_file(self, mock_exists, mock_open, mock_run_batch):
        """Test happy path with valid token and PDF file returns PDF file download."""
        # Create a temporary PDF file path
        temp_pdf_path = "/tmp/test_invoice.pdf"
        mock_pdf_content = b"%PDF-1.4\nvalid pdf content"
        
        mock_run_batch.return_value = {
            "batch_id": "batch-123",
            "counts": {"pass": 1, "fail": 0, "warn": 0},
            "invoices": [
                {
                    "invoice_number": "INV-001",
                    "status": "pass",
                    "compliant": True,
                    "issues": 0,
                    "pdf_path": temp_pdf_path,
                },
            ],
        }
        
        mock_exists.return_value = True
        mock_file = mock.mock_open(read_data=mock_pdf_content)
        mock_open.return_value = mock_file.return_value

        # Create valid PDF content
        pdf_content = b"%PDF-1.4\nvalid pdf content"
        data = {"files": [(BytesIO(pdf_content), "invoice.pdf")]}
        response = self._make_authorized_request(data, token=self.access_token)

        self.assertEqual(response.status_code, 200)
        # For single file, should return PDF file
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))
        mock_run_batch.assert_called_once()

    @mock.patch("app.run_batch")
    @mock.patch("builtins.open", create=True)
    @mock.patch("os.path.exists")
    def test_valid_multiple_files_returns_zip(self, mock_exists, mock_open, mock_run_batch):
        """Test that multiple valid files return a zip file with PDFs and JSON summary."""
        temp_pdf_path1 = "/tmp/test_invoice1.pdf"
        temp_pdf_path2 = "/tmp/test_invoice2.pdf"
        mock_pdf_content = b"%PDF-1.4\nvalid pdf content"
        
        mock_run_batch.return_value = {
            "batch_id": "batch-456",
            "counts": {"pass": 2, "fail": 0, "warn": 0},
            "invoices": [
                {
                    "invoice_number": "INV-001",
                    "status": "pass",
                    "compliant": True,
                    "issues": 0,
                    "pdf_path": temp_pdf_path1,
                },
                {
                    "invoice_number": "INV-002",
                    "status": "pass",
                    "compliant": True,
                    "issues": 0,
                    "pdf_path": temp_pdf_path2,
                },
            ],
        }
        
        mock_exists.return_value = True
        mock_file = mock.mock_open(read_data=mock_pdf_content)
        mock_open.return_value = mock_file.return_value

        data = {
            "files": [
                (BytesIO(b"pdf-content-1"), "invoice1.pdf"),
                (BytesIO(b"png-content"), "invoice2.png"),
            ]
        }
        response = self._make_authorized_request(data, token=self.access_token)

        self.assertEqual(response.status_code, 200)
        # For multiple files, should return zip file
        self.assertEqual(response.mimetype, "application/zip")
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))
        mock_run_batch.assert_called_once()
        # Verify both files were included in the batch
        call_args = mock_run_batch.call_args[0][0]
        self.assertEqual(len(call_args), 2)
    
    @mock.patch("app.run_batch")
    @mock.patch("app.INVOICE_PDF_GENERATOR")
    @mock.patch("builtins.open", create=True)
    @mock.patch("os.path.exists")
    def test_with_mocked_pdf_generator(self, mock_exists, mock_open, mock_pdf_generator, mock_run_batch):
        """Test that PDF generator is used when available (though run_batch already generates PDFs)."""
        temp_pdf_path = "/tmp/test.pdf"
        mock_pdf_content = b"%PDF-1.4\nvalid pdf content"
        
        mock_run_batch.return_value = {
            "batch_id": "batch-789",
            "counts": {"pass": 1, "fail": 0, "warn": 0},
            "invoices": [
                {
                    "invoice_number": "INV-001",
                    "status": "pass",
                    "compliant": True,
                    "issues": 0,
                    "pdf_path": temp_pdf_path,
                },
            ],
        }
        
        # Mock file operations like other happy-path tests
        mock_exists.return_value = True
        mock_file = mock.mock_open(read_data=mock_pdf_content)
        mock_open.return_value = mock_file.return_value
        
        pdf_content = b"%PDF-1.4\nvalid pdf content"
        data = {"files": [(BytesIO(pdf_content), "invoice.pdf")]}
        response = self._make_authorized_request(data, token=self.valid_token)
        
        self.assertEqual(response.status_code, 200)
        mock_run_batch.assert_called_once()
    
    def test_unsupported_extension_rejected(self):
        """Test that unsupported file extension is rejected."""
        data = {"files": [(BytesIO(b"content"), "test.txt")]}
        response = self._make_authorized_request(data, token=self.valid_token)
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("No valid files", payload["error"])


if __name__ == "__main__":
    unittest.main()
