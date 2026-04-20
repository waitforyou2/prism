#!/usr/bin/env python3
"""
Download article HTML locally so Defuddle can parse from disk instead of fetching pages itself.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: Install dependencies first: pip install requests", file=sys.stderr)
    sys.exit(1)

requests.packages.urllib3.disable_warnings()

SKIP_SOURCES = {"bilibili", "weibo"}
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5,zh-CN;q=0.3",
}


def is_sogou_link(item):
    return item.get("source") == "sogou" and "sogou.com/link" in item.get("url", "")


def should_download(item, min_relevance):
    if item.get("relevance", 0) < min_relevance:
        return False
    if item.get("source") in SKIP_SOURCES:
        return False
    if is_sogou_link(item):
        return False
    return bool(item.get("url"))


def build_html_path(item, html_dir):
    source = item.get("source", "web")
    digest = hashlib.sha256(item.get("url", "").encode("utf-8")).hexdigest()[:16]
    return html_dir / f"{source}_{digest}.html"


def create_session():
    session = requests.Session()
    session.verify = False
    session.headers.update(DEFAULT_HEADERS)
    return session


def download_items(items, html_dir, min_relevance=70, timeout=25, session=None):
    html_dir.mkdir(parents=True, exist_ok=True)
    session = session or create_session()

    results = []
    for item in items:
        enriched = dict(item)
        if not should_download(enriched, min_relevance):
            enriched["downloadStatus"] = "skipped"
            results.append(enriched)
            continue

        html_path = build_html_path(enriched, html_dir)
        try:
            resp = session.get(enriched["url"], timeout=timeout, allow_redirects=True)
            resp.raise_for_status()
            html_path.write_text(resp.text, encoding="utf-8")
            enriched["htmlPath"] = str(html_path.resolve())
            enriched["fetchedUrl"] = resp.url
            enriched["downloadStatus"] = "downloaded"
            enriched["fetchStatus"] = "downloaded"
        except Exception as exc:
            enriched["downloadStatus"] = "failed"
            enriched["fetchError"] = str(exc)[:200]
        results.append(enriched)
    return results


def main():
    parser = argparse.ArgumentParser(description="Download HTML locally for Defuddle parsing")
    parser.add_argument("--in", dest="in_file", required=True, help="Input JSON file path")
    parser.add_argument("--html-dir", required=True, help="Directory where HTML files will be stored")
    parser.add_argument("--out", required=True, help="Output JSON file path")
    parser.add_argument("--min-relevance", type=int, default=70, help="Minimum relevance to download")
    parser.add_argument("--timeout", type=int, default=25, help="Per-request timeout in seconds")
    args = parser.parse_args()

    items = json.loads(Path(args.in_file).read_text(encoding="utf-8"))
    if not isinstance(items, list):
        print("Error: input JSON must be an array", file=sys.stderr)
        sys.exit(1)

    results = download_items(
        items,
        html_dir=Path(args.html_dir),
        min_relevance=args.min_relevance,
        timeout=args.timeout,
    )

    out_path = Path(args.out)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    downloaded = sum(1 for item in results if item.get("downloadStatus") == "downloaded")
    failed = sum(1 for item in results if item.get("downloadStatus") == "failed")
    skipped = len(results) - downloaded - failed
    print(f"Downloaded: {downloaded} | Failed: {failed} | Skipped: {skipped}", file=sys.stderr)
    print(f"Saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
