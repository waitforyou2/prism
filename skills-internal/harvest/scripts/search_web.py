#!/usr/bin/env python3
"""International web search aggregator."""

import argparse
import json
import logging
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()

REQUEST_KWARGS = {"verify": False}
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
    ),
]
ALL_SOURCES = ["bing", "google", "duckduckgo", "hackernews", "github", "youtube"]
RATE_LIMITS = {
    "bing": 5,
    "google": 10,
    "duckduckgo": 3,
    "hackernews": 1,
    "github": 2,
    "youtube": 3,
}


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="International web search aggregator")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--sources",
        default=",".join(ALL_SOURCES),
        help=f"Comma-separated sources (default: {','.join(ALL_SOURCES)})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max results per source",
    )
    parser.add_argument("--out", help="Output JSON file path")
    return parser.parse_args()


def get_headers(language: str = "en") -> dict[str, str]:
    """Build a realistic browser header set."""
    accept_language = "en-US,en;q=0.5" if language == "en" else "zh-CN,zh;q=0.9,en;q=0.8"
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": accept_language,
    }


def request_text(url: str, params: dict, headers: dict | None = None) -> str:
    """Fetch a text response with shared request defaults."""
    response = requests.get(
        url,
        params=params,
        headers=headers or get_headers(),
        timeout=15,
        **REQUEST_KWARGS,
    )
    response.raise_for_status()
    return response.text


def request_json(url: str, params: dict, headers: dict | None = None) -> dict:
    """Fetch a JSON response with shared request defaults."""
    response = requests.get(
        url,
        params=params,
        headers=headers or {"User-Agent": random.choice(USER_AGENTS)},
        timeout=15,
        **REQUEST_KWARGS,
    )
    response.raise_for_status()
    return response.json()


def search_bing(query: str, limit: int = 20) -> list[dict]:
    """Search Bing via HTML scraping."""
    try:
        html = request_text(
            "https://www.bing.com/search",
            {"q": query, "count": limit},
        )
        results = parse_bing_results(html, limit)
        LOGGER.info("Bing: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("Bing error: %s", exc)
        return []


def parse_bing_results(html: str, limit: int) -> list[dict]:
    """Parse Bing result items from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for item in soup.select("li.b_algo"):
        title_element = item.select_one("h2 a")
        if not title_element:
            continue
        url = title_element.get("href", "")
        title = title_element.get_text(strip=True)
        snippet_element = item.select_one(".b_caption p")
        snippet = snippet_element.get_text(strip=True) if snippet_element else ""
        if title and url.startswith("http"):
            results.append({"title": title, "content": snippet, "url": url, "source": "bing"})
        if len(results) >= limit:
            break
    return results


def search_google(query: str, limit: int = 20) -> list[dict]:
    """Search Google via HTML scraping."""
    try:
        html = request_text(
            "https://www.google.com/search",
            {"q": query, "num": limit, "hl": "en"},
        )
        results = parse_google_results(html, limit)
        LOGGER.info("Google: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("Google error: %s", exc)
        return []


def parse_google_results(html: str, limit: int) -> list[dict]:
    """Parse Google result items from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for item in soup.select("div.g"):
        heading = item.select_one("h3")
        link_element = item.select_one("a")
        if not heading or not link_element:
            continue
        url = link_element.get("href", "")
        snippet_element = item.select_one(".VwiC3b")
        snippet = snippet_element.get_text(strip=True) if snippet_element else ""
        if url.startswith("http"):
            results.append(
                {
                    "title": heading.get_text(strip=True),
                    "content": snippet,
                    "url": url,
                    "source": "google",
                }
            )
        if len(results) >= limit:
            break
    return results


def search_duckduckgo(query: str, limit: int = 20) -> list[dict]:
    """Search DuckDuckGo via HTML results."""
    try:
        html = request_text("https://html.duckduckgo.com/html/", {"q": query})
        results = parse_duckduckgo_results(html, limit)
        LOGGER.info("DuckDuckGo: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("DuckDuckGo error: %s", exc)
        return []


def parse_duckduckgo_results(html: str, limit: int) -> list[dict]:
    """Parse DuckDuckGo result items from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for item in soup.select(".result"):
        title_element = item.select_one(".result__title a")
        if not title_element:
            continue
        title = title_element.get_text(strip=True)
        resolved_url = resolve_duckduckgo_url(title_element.get("href", ""))
        snippet_element = item.select_one(".result__snippet")
        snippet = snippet_element.get_text(strip=True) if snippet_element else ""
        if title and resolved_url.startswith("http"):
            results.append(
                {
                    "title": title,
                    "content": snippet,
                    "url": resolved_url,
                    "source": "duckduckgo",
                }
            )
        if len(results) >= limit:
            break
    return results


def resolve_duckduckgo_url(raw_url: str) -> str:
    """Resolve DuckDuckGo redirect URLs."""
    if "uddg=" not in raw_url:
        return raw_url
    try:
        full_url = raw_url if raw_url.startswith("http") else f"https:{raw_url}"
        params = parse_qs(urlparse(full_url).query)
        extracted_url = unquote(params.get("uddg", [""])[0])
        if extracted_url and "duckduckgo.com/y.js" not in extracted_url:
            return extracted_url
    except Exception:
        return raw_url
    return raw_url


def search_hackernews(query: str, limit: int = 20) -> list[dict]:
    """Search Hacker News via Algolia API."""
    try:
        one_day_ago = int(
            (datetime.now(timezone.utc) - timedelta(hours=24)).timestamp()
        )
        payload = request_json(
            "https://hn.algolia.com/api/v1/search",
            {
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
                "numericFilters": f"created_at_i>{one_day_ago}",
            },
        )
        results = build_hackernews_results(payload, limit)
        LOGGER.info("HackerNews: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("HackerNews error: %s", exc)
        return []


def build_hackernews_results(payload: dict, limit: int) -> list[dict]:
    """Build normalized Hacker News results."""
    results: list[dict] = []
    for hit in payload.get("hits", []):
        if not (hit.get("url") or hit.get("story_text")):
            continue
        result_url = hit.get("url") or (
            f"https://news.ycombinator.com/item?id={hit['objectID']}"
        )
        results.append(
            {
                "title": hit.get("title", ""),
                "content": hit.get("story_text") or hit.get("title", ""),
                "url": result_url,
                "source": "hackernews",
                "sourceId": hit.get("objectID"),
                "publishedAt": hit.get("created_at"),
                "score": hit.get("points", 0),
                "commentCount": hit.get("num_comments", 0),
                "author": {
                    "name": hit.get("author", ""),
                    "username": hit.get("author", ""),
                },
            }
        )
        if len(results) >= limit:
            break
    return results


def search_github(query: str, limit: int = 20) -> list[dict]:
    """Search GitHub repositories via public API."""
    try:
        payload = request_json(
            "https://api.github.com/search/repositories",
            {"q": query, "sort": "stars", "per_page": limit},
        )
        results = build_github_results(payload, limit)
        LOGGER.info("GitHub: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("GitHub error: %s", exc)
        return []


def build_github_results(payload: dict, limit: int) -> list[dict]:
    """Build normalized GitHub results."""
    items = payload.get("items") or []
    if not items:
        LOGGER.info("GitHub: no results")
        return []
    results: list[dict] = []
    for item in items[:limit]:
        results.append(
            {
                "title": item.get("full_name", ""),
                "content": item.get("description") or "",
                "url": item.get("html_url", ""),
                "source": "github",
                "sourceId": str(item.get("id", "")),
                "viewCount": item.get("stargazers_count", 0),
                "likeCount": item.get("stargazers_count", 0),
                "author": {
                    "name": item.get("owner", {}).get("login", ""),
                    "username": item.get("owner", {}).get("login", ""),
                },
                "publishedAt": item.get("updated_at"),
            }
        )
    return results


def search_youtube(query: str, limit: int = 20) -> list[dict]:
    """Search YouTube videos via ytInitialData extraction."""
    try:
        html = request_text(
            "https://www.youtube.com/results",
            {"search_query": query},
            headers={"User-Agent": random.choice(USER_AGENTS)},
        )
        results = parse_youtube_results(html, limit)
        LOGGER.info("YouTube: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("YouTube error: %s", exc)
        return []


def parse_youtube_results(html: str, limit: int) -> list[dict]:
    """Parse YouTube results from ytInitialData."""
    match = re.search(r"ytInitialData = ({.*?});</script>", html)
    if not match:
        LOGGER.info("YouTube: no ytInitialData found")
        return []
    payload = json.loads(match.group(1))
    contents = (
        payload.get("contents", {})
        .get("twoColumnSearchResultsRenderer", {})
        .get("primaryContents", {})
        .get("sectionListRenderer", {})
        .get("contents", [])
    )
    results: list[dict] = []
    for section in contents:
        results.extend(parse_youtube_section(section, limit - len(results)))
        if len(results) >= limit:
            break
    return results


def parse_youtube_section(section: dict, limit: int) -> list[dict]:
    """Parse a single YouTube result section."""
    results: list[dict] = []
    items = section.get("itemSectionRenderer", {}).get("contents", [])
    for item in items:
        video = item.get("videoRenderer")
        if not video:
            continue
        result = build_youtube_result(video)
        if result:
            results.append(result)
        if len(results) >= limit:
            break
    return results


def build_youtube_result(video: dict) -> dict | None:
    """Build a normalized YouTube result."""
    title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
    video_id = video.get("videoId")
    if not title or not video_id:
        return None
    channel_name = video.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
    return {
        "title": title,
        "content": build_youtube_description(video) or title,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "source": "youtube",
        "sourceId": video_id,
        "viewCount": parse_view_count(video.get("viewCountText", {}).get("simpleText", "")),
        "author": {"name": channel_name, "username": channel_name},
    }


def build_youtube_description(video: dict) -> str:
    """Build a YouTube description from metadata snippets."""
    snippet_blocks = video.get("detailedMetadataSnippets", [{}])
    if not snippet_blocks:
        return ""
    runs = snippet_blocks[0].get("snippetText", {}).get("runs", [])
    return "".join(run.get("text", "") for run in runs)


def parse_view_count(views_text: str) -> int:
    """Parse a YouTube view count string."""
    match = re.search(r"([\d,]+)", views_text or "")
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def deduplicate(results: list[dict]) -> list[dict]:
    """Remove duplicate URLs after normalization."""
    seen_urls: set[str] = set()
    unique_results: list[dict] = []
    for result in results:
        normalized_url = (
            result["url"]
            .rstrip("/")
            .replace("http://www.", "https://")
            .replace("https://www.", "https://")
        )
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        unique_results.append(result)
    return unique_results


def validate_sources(sources: list[str]) -> None:
    """Validate source names."""
    invalid_sources = [source for source in sources if source not in SEARCH_FNS]
    if invalid_sources:
        raise ValueError(f"Unknown sources: {invalid_sources}. Available: {ALL_SOURCES}")


def run_searches(query: str, sources: list[str], limit: int) -> list[dict]:
    """Run the configured searches with polite delays."""
    all_results: list[dict] = []
    for source_index, source_name in enumerate(sources):
        if source_index > 0:
            delay_seconds = RATE_LIMITS.get(source_name, 3)
            LOGGER.info("Waiting %ss before %s...", delay_seconds, source_name)
            time.sleep(delay_seconds)
        all_results.extend(SEARCH_FNS[source_name](query, limit))
    return all_results


def write_results(results: list[dict], output_file: str | None) -> None:
    """Write results to stdout or a file."""
    rendered_results = json.dumps(results, ensure_ascii=False, indent=2)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as output_handle:
            output_handle.write(rendered_results)
        LOGGER.info("Saved to %s", output_file)
        return
    sys.stdout.write(rendered_results)
    sys.stdout.write("\n")


def main() -> int:
    """Run the international search command."""
    configure_logging()
    args = parse_args()
    sources = [source.strip().lower() for source in args.sources.split(",") if source.strip()]
    try:
        validate_sources(sources)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return 1
    all_results = run_searches(args.query, sources, args.limit)
    unique_results = deduplicate(all_results)
    LOGGER.info("Total: %s -> %s after dedup", len(all_results), len(unique_results))
    write_results(unique_results, args.out)
    return 0


SEARCH_FNS = {
    "bing": search_bing,
    "google": search_google,
    "duckduckgo": search_duckduckgo,
    "hackernews": search_hackernews,
    "github": search_github,
    "youtube": search_youtube,
}


if __name__ == "__main__":
    raise SystemExit(main())
