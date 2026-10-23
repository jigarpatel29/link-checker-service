from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Batch, URLCheck
from .tasks import check_url


class BatchAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("checker.views.check_url.delay")
    def test_create_batch(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/batches/",
                {"urls": ["https://algiftcards.com", "https://www.ticketstodo.com"]},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Batch.objects.count(), 1)
        self.assertEqual(URLCheck.objects.count(), 2)
        self.assertEqual(mock_delay.call_count, 2)

    def test_reject_more_than_100_urls(self):
        response = self.client.post(
            "/batches/",
            {"urls": [f"https://example{i}.com" for i in range(101)]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reject_invalid_scheme(self):
        response = self.client.post(
            "/batches/",
            {"urls": ["ftp://example.com"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_batch_progress(self):
        batch = Batch.objects.create()
        URLCheck.objects.create(batch=batch, url="https://example.com")
        URLCheck.objects.create(
            batch=batch,
            url="https://example.org",
            status_code=200,
            response_time_ms=100,
            final_url="https://example.org/",
            checked_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
        )

        response = self.client.get(f"/batches/{batch.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "in_progress")
        self.assertEqual(response.data["progress"]["completed"], 1)

    def test_missing_batch(self):
        response = self.client.get("/batches/99999/")
        self.assertEqual(response.status_code, 404)


class URLTaskTests(TestCase):
    @patch("checker.tasks.requests.get")
    def test_check_url_success(self, mock_get):
        from django.utils import timezone

        batch = Batch.objects.create()
        item = URLCheck.objects.create(
            batch=batch,
            url="https://example.com",
        )

        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.url = "https://example.com/"
        mock_get.return_value = mock_response

        check_url.run(item.id)

        item.refresh_from_db()
        self.assertEqual(item.status_code, 200)
        self.assertEqual(item.final_url, "https://example.com/")
        self.assertIsNotNone(item.checked_at)
        self.assertFalse(item.last_check_failed)

    @patch("checker.tasks.requests.get")
    def test_check_url_connection_failure(self, mock_get):
        import requests

        batch = Batch.objects.create()
        item = URLCheck.objects.create(
            batch=batch,
            url="https://example.com",
        )
        mock_get.side_effect = requests.Timeout("Timed out")

        # Simulate the final attempt after two retries.
        check_url.apply(
            args=[item.id],
            retries=2,
            throw=True,
        )

        item.refresh_from_db()

        self.assertIsNone(item.status_code)
        self.assertTrue(item.last_check_failed)
        self.assertEqual(item.error, "Timed out")
        self.assertIsNotNone(item.checked_at)
