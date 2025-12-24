import io
import os
import sys
import json
import unittest
from unittest import mock

# Ensure backend/lookup_service is on the path for direct app import
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, APP_DIR)

from app import app as flask_app  # noqa: E402

VALID_ID = "1234567890123"


class LookupServiceSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()

    @mock.patch("app.record_result")
    @mock.patch("app.start_run")
    @mock.patch("app.log_lookup")
    @mock.patch("app.lookup_business")
    def test_lookup_single_success(self, mock_lookup_business, mock_log_lookup, mock_start_run, mock_record_result):
        mock_lookup_business.return_value = {
            "business_id": VALID_ID,
            "name": "Audos Inc.",
            "address": "Tokyo",
        }

        response = self.client.post("/lookup-single", json={"business_id": VALID_ID})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["business_id"], VALID_ID)
        self.assertIn("run_id", payload)
        mock_lookup_business.assert_called_once_with(VALID_ID)
        mock_start_run.assert_called()
        mock_record_result.assert_called()
        mock_log_lookup.assert_called()

    @mock.patch("app.record_result")
    @mock.patch("app.start_run")
    @mock.patch("app.log_lookup")
    @mock.patch("app.lookup_business")
    def test_lookup_bulk_success(self, mock_lookup_business, mock_log_lookup, mock_start_run, mock_record_result):
        mock_lookup_business.side_effect = [
            {"business_id": VALID_ID, "name": "Audos Inc."},
            {"business_id": VALID_ID, "name": "Audos Inc."},
        ]

        response = self.client.post(
            "/lookup-bulk",
            data=json.dumps({"business_ids": [VALID_ID, VALID_ID]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["results"]), 2)
        self.assertIn("run_id", payload)
        self.assertEqual(mock_lookup_business.call_count, 2)
        mock_start_run.assert_called()
        mock_record_result.assert_called()
        mock_log_lookup.assert_called()

    @mock.patch("app.record_result")
    @mock.patch("app.start_run")
    @mock.patch("app.log_lookup")
    @mock.patch("app.lookup_business")
    def test_lookup_csv_success(self, mock_lookup_business, mock_log_lookup, mock_start_run, mock_record_result):
        mock_lookup_business.return_value = {
            "business_id": VALID_ID,
            "name": "Audos Inc.",
        }
        csv_data = f"business_id\n{VALID_ID}\n".encode("utf-8")

        response = self.client.post(
            "/lookup-csv",
            data={"file": (io.BytesIO(csv_data), "test.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["results"]), 1)
        self.assertIn("run_id", payload)
        mock_lookup_business.assert_called_once_with(VALID_ID)
        mock_start_run.assert_called()
        mock_record_result.assert_called()
        mock_log_lookup.assert_called()

    def test_lookup_csv_bad_extension(self):
        """CSV endpoint rejects files with non-CSV extension."""
        csv_data = b"business_id\n1234567890123\n"

        response = self.client.post(
            "/lookup-csv",
            data={"file": (io.BytesIO(csv_data), "test.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("Only CSV files are allowed", payload["error"])

    @mock.patch("app.MAX_CSV_SIZE_BYTES", 100)
    def test_lookup_csv_too_large(self):
        """CSV endpoint rejects files exceeding size limit."""
        csv_data = b"business_id\n" + b"1234567890123\n" * 10

        response = self.client.post(
            "/lookup-csv",
            data={"file": (io.BytesIO(csv_data), "test.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("File size exceeds", payload["error"])

    def test_lookup_csv_missing_id_column(self):
        """CSV endpoint rejects CSVs without business_id or corporate_number column."""
        csv_data = b"name,address\nTest Corp,Tokyo\n"

        response = self.client.post(
            "/lookup-csv",
            data={"file": (io.BytesIO(csv_data), "test.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("csv_missing_id_column", payload["error"])


if __name__ == "__main__":
    unittest.main()
