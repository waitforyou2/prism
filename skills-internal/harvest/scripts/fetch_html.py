#!/usr/bin/env python3
"""Download article HTML locally for later Defuddle parsing."""

import argparse
import hashlib
import json
import logging
from pathlib import Path

import requests

LOGGER = logging.getLogger(__name__)

SKIP_SOURCES = {"bilibili", "weibo"}
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5,zh-CN;q=0.3",
}

requests.packages.urllib3.disable_warnings()


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download HTML locally for Defuddle parsing",
    )
    parser.add_argument("--in", dest="input_file", required=True, help="Input JSON file path")
    parser.add_argument("--html-dir", required=True, help="Directory where HTML files will be stored")
    parser.add_argument("--out", required=True, help="Output JSON file path")
    parser.add_argument(
        "--min-relevance",
        type=int,
        default=70,
        help="Minimum relevance to download",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=25,
        help="Per-request timeout in seconds",
    )
    return parser.parse_args()


def load_items(input_file: str) -> list[dict]:
    """Load JSON input items from disk."""
    parsed_items = json.loads(Path(input_file).read_text(encoding="utf-8-sig"))
    if not isinstance(parsed_items, list):
        raise ValueError("input JSON must be an array")
    return parsed_items


def is_sogou_link(item_data: dict) -> bool:
    """Return whether the item is a Sogou redirect link."""
    return (
        item_data.get("source") == "sogou"
        and "sogou.com/link" in item_data.get("url", "")
    )


def should_download(item_data: dict, min_relevance: int) -> bool:
    """Return whether an item should be downloaded locally."""
    if item_data.get("relevance", 0) < min_relevance:
        return False
    if item_data.get("source") in SKIP_SOURCES:
        return False
    if is_sogou_link(item_data):
        return False
    return bool(item_data.get("url"))


def build_html_path(item_data: dict, html_dir: Path) -> Path:
    """Build a deterministic local HTML path for an item."""
    source_name = item_data.get("source", "web")
    url_digest = hashlib.sha256(
        item_data.get("url", "").encode("utf-8")
    ).hexdigest()[:16]
    return html_dir / f"{source_name}_{url_digest}.html"


def create_session() -> requests.Session:
    """Create a requests session with intranet-friendly defaults."""
    session = requests.Session()
    session.verify = False
    session.headers.update(DEFAULT_HEADERS)
    return session


def download_item(
    session: requests.Session,
    item_data: dict,
    html_dir: Path,
    timeout_seconds: int,
) -> dict:
    """Download a single item and annotate it with local HTML metadata."""
    enriched_item = dict(item_data)
    html_path = build_html_path(enriched_item, html_dir)
    try:
        response = session.get(
            enriched_item["url"],
            timeout=timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()
        html_path.write_text(response.text, encoding="utf-8")
        enriched_item["htmlPath"] = str(html_path.resolve())
        enriched_item["fetchedUrl"] = response.url
        enriched_item["downloadStatus"] = "downloaded"
        enriched_item["fetchStatus"] = "downloaded"
    except Exception as exc:
        enriched_item["downloadStatus"] = "failed"
        enriched_item["fetchError"] = str(exc)[:200]
    return enriched_item


def download_items(
    items: list[dict],
    html_dir: Path,
    min_relevance: int = 70,
    timeout: int = 25,
    session: requests.Session | None = None,
) -> list[dict]:
    """Download all eligible items and attach local HTML paths."""
    html_dir.mkdir(parents=True, exist_ok=True)
    session = session or create_session()
    downloaded_items: list[dict] = []

    for item_data in items:
        if not should_download(item_data, min_relevance):
            enriched_item = dict(item_data)
            enriched_item["downloadStatus"] = "skipped"
            downloaded_items.append(enriched_item)
            continue
        downloaded_items.append(
            download_item(session, item_data, html_dir, timeout)
        )
    return downloaded_items


def log_summary(results: list[dict], output_path: Path) -> None:
    """Log a summary for the completed download batch."""
    downloaded_count = sum(
        1 for item_data in results if item_data.get("downloadStatus") == "downloaded"
    )
    failed_count = sum(
        1 for item_data in results if item_data.get("downloadStatus") == "failed"
    )
    skipped_count = len(results) - downloaded_count - failed_count
    LOGGER.info(
        "Downloaded: %s | Failed: %s | Skipped: %s",
        downloaded_count,
        failed_count,
        skipped_count,
    )
    LOGGER.info("Saved to %s", output_path)


def main() -> int:
    """Run the local HTML download command."""
    configure_logging()
    args = parse_args()
    try:
        items = load_items(args.input_file)
    except ValueError as exc:
        LOGGER.error("Error: %s", exc)
        return 1

    results = download_items(
        items,
        html_dir=Path(args.html_dir),
        min_relevance=args.min_relevance,
        timeout=args.timeout,
    )
    output_path = Path(args.out)
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_summary(results, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
