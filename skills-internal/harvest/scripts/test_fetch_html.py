"""Tests for the local HTML download helper."""

import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import fetch_html


class FetchHtmlTests(unittest.TestCase):
    """Verify local HTML download behavior."""

    def test_download_items_writes_html_and_manifest(self) -> None:
        """Downloaded items should include a persisted local HTML path."""
        items = [
            {
                "title": "Example",
                "url": "https://intranet.example/article",
                "source": "bing",
                "relevance": 90,
            }
        ]
        response = Mock()
        response.text = (
            "<html><body><main><article>"
            "Hello intranet"
            "</article></main></body></html>"
        )
        response.raise_for_status.return_value = None
        temp_path = Path(__file__).resolve().parents[3] / ".tmp-fetch-html-test"
        shutil.rmtree(temp_path, ignore_errors=True)
        temp_path.mkdir(parents=True, exist_ok=True)
        try:
            html_dir = temp_path / "html"
            with patch("fetch_html.requests.Session.get", return_value=response):
                results = fetch_html.download_items(
                    items,
                    html_dir=html_dir,
                    min_relevance=70,
                    timeout=10,
                )
            self.assertEqual(results[0]["fetchStatus"], "downloaded")
            self.assertIn("htmlPath", results[0])
            html_path = Path(results[0]["htmlPath"])
            self.assertTrue(html_path.exists())
            self.assertIn("Hello intranet", html_path.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
