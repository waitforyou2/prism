#!/usr/bin/env python3
"""Chinese platform search aggregator."""

import argparse
import json
import logging
import random
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

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
]
ALL_SOURCES = ["sogou", "bilibili", "weibo", "juejin"]
RATE_LIMITS = {"sogou": 3, "bilibili": 2, "weibo": 3, "juejin": 3}


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Chinese platform search aggregator")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--sources",
        default=",".join(ALL_SOURCES),
        help=f"Comma-separated sources (default: {','.join(ALL_SOURCES)})",
    )
    parser.add_argument("--limit", type=int, default=20, help="Max results per source")
    parser.add_argument(
        "--detect-account",
        action="store_true",
        help="Detect if keyword is a Bilibili account and fetch latest videos",
    )
    parser.add_argument("--out", help="Output JSON file path")
    return parser.parse_args()


def rand_ua() -> str:
    """Return a random browser user agent."""
    return random.choice(USER_AGENTS)


def request_json(url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    """Fetch a JSON response with shared request defaults."""
    response = requests.get(
        url,
        params=params or {},
        headers=headers or {"User-Agent": rand_ua()},
        timeout=15,
        **REQUEST_KWARGS,
    )
    response.raise_for_status()
    return response.json()


def request_text(url: str, params: dict, headers: dict) -> str:
    """Fetch an HTML response with shared request defaults."""
    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=15,
        allow_redirects=True,
        **REQUEST_KWARGS,
    )
    response.raise_for_status()
    return response.text


def search_sogou(query: str, limit: int = 20) -> list[dict]:
    """Search Sogou web results."""
    try:
        html = request_text(
            "https://www.sogou.com/web",
            {"query": query, "ie": "utf-8"},
            {
                "User-Agent": rand_ua(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        results = parse_sogou_results(html, limit)
        LOGGER.info("Sogou: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("Sogou error: %s", exc)
        return []


def parse_sogou_results(html: str, limit: int) -> list[dict]:
    """Parse Sogou HTML results."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for item in soup.select(".vrwrap, .rb"):
        title_element = item.select_one("h3 a, .vr-title a, .vrTitle a")
        if not title_element:
            continue
        title = title_element.get_text(strip=True)
        url = title_element.get("href", "")
        if url.startswith("/link?url="):
            url = f"https://www.sogou.com{url}"
        snippet_element = (
            item.select_one(".space-txt")
            or item.select_one(".str-text-info")
            or item.select_one(".str_info")
            or item.select_one(".text-layout")
            or item.select_one("p")
        )
        snippet = snippet_element.get_text(strip=True) if snippet_element else ""
        if title and url and "澶у杩樺湪鎼" not in title:
            results.append(
                {"title": title, "content": snippet or title, "url": url, "source": "sogou"}
            )
        if len(results) >= limit:
            break
    return results


def _bili_headers() -> dict[str, str]:
    """Build Bilibili headers."""
    return {
        "User-Agent": rand_ua(),
        "Referer": "https://search.bilibili.com/",
        "Accept": "application/json",
        "Cookie": f"buvid3={uuid.uuid4()}infoc",
    }


def search_bilibili(query: str, limit: int = 20) -> list[dict]:
    """Search Bilibili videos."""
    try:
        payload = request_json(
            "https://api.bilibili.com/x/web-interface/search/type",
            {
                "keyword": query,
                "search_type": "video",
                "order": "pubdate",
                "page": 1,
                "pagesize": limit,
            },
            _bili_headers(),
        )
        results = build_bilibili_results(payload, limit)
        LOGGER.info("Bilibili: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("Bilibili error: %s", exc)
        return []


def build_bilibili_results(payload: dict, limit: int) -> list[dict]:
    """Build normalized Bilibili results."""
    result_items = payload.get("data", {}).get("result") or []
    if payload.get("code") != 0 or not result_items:
        LOGGER.info("Bilibili: no results (code=%s)", payload.get("code"))
        return []
    results: list[dict] = []
    for item in result_items[:limit]:
        title = re.sub(r"</?em[^>]*>", "", item.get("title", ""))
        results.append(
            {
                "title": title,
                "content": item.get("description") or title,
                "url": f"https://www.bilibili.com/video/{item['bvid']}",
                "source": "bilibili",
                "sourceId": item.get("bvid"),
                "publishedAt": datetime.fromtimestamp(
                    item.get("pubdate", 0),
                    tz=timezone.utc,
                ).isoformat(),
                "viewCount": item.get("play", 0),
                "likeCount": item.get("like", 0),
                "commentCount": item.get("review", 0),
                "danmakuCount": item.get("danmaku", 0),
                "author": {
                    "name": item.get("author", ""),
                    "username": str(item.get("mid", "")),
                },
            }
        )
    return results


def search_bilibili_user(keyword: str) -> dict | None:
    """Search for a matching Bilibili user."""
    try:
        payload = request_json(
            "https://api.bilibili.com/x/web-interface/search/type",
            {
                "keyword": keyword,
                "search_type": "bili_user",
                "page": 1,
                "pagesize": 5,
            },
            _bili_headers(),
        )
    except Exception as exc:
        LOGGER.warning("Bilibili user search error: %s", exc)
        return None
    users = payload.get("data", {}).get("result") or []
    if payload.get("code") != 0 or not users:
        return None
    for user in users:
        if user["uname"].lower() == keyword.lower():
            return user
    top_user = users[0]
    if top_user.get("fans", 0) > 1000 and keyword.lower() in top_user["uname"].lower():
        return top_user
    return None


def get_bilibili_user_videos(mid: str, limit: int = 10) -> list[dict]:
    """Fetch latest videos from a Bilibili user's channel."""
    try:
        payload = request_json(
            "https://api.bilibili.com/x/space/arc/search",
            {"mid": mid, "pn": 1, "ps": limit, "order": "pubdate"},
            {
                "User-Agent": rand_ua(),
                "Referer": f"https://space.bilibili.com/{mid}",
                "Accept": "application/json",
            },
        )
        results = build_bilibili_user_video_results(payload)
        LOGGER.info("Bilibili user %s: %s videos", mid, len(results))
        return results
    except Exception as exc:
        LOGGER.warning("Bilibili user videos error: %s", exc)
        return []


def build_bilibili_user_video_results(payload: dict) -> list[dict]:
    """Build normalized Bilibili user video results."""
    results: list[dict] = []
    for video in payload.get("data", {}).get("list", {}).get("vlist", []):
        results.append(
            {
                "title": video.get("title", ""),
                "content": video.get("description") or video.get("title", ""),
                "url": f"https://www.bilibili.com/video/{video['bvid']}",
                "source": "bilibili",
                "sourceId": video.get("bvid"),
                "publishedAt": datetime.fromtimestamp(
                    video.get("created", 0),
                    tz=timezone.utc,
                ).isoformat(),
                "viewCount": video.get("play", 0),
                "commentCount": video.get("comment", 0) or video.get("review", 0),
                "danmakuCount": video.get("danmaku", 0),
                "author": {
                    "name": video.get("author", ""),
                    "username": str(video.get("mid", "")),
                },
            }
        )
    return results


def search_weibo(query: str, _limit: int = 20) -> list[dict]:
    """Match query against Weibo hot topics."""
    try:
        payload = request_json(
            "https://weibo.com/ajax/side/hotSearch",
            headers={
                "User-Agent": rand_ua(),
                "Accept": "application/json",
                "Referer": "https://weibo.com/",
            },
        )
        results = build_weibo_results(query, payload)
        LOGGER.info("Weibo: %s matches", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("Weibo error: %s", exc)
        return []


def build_weibo_results(query: str, payload: dict) -> list[dict]:
    """Build normalized Weibo hot-topic matches."""
    hot_items = payload.get("data", {}).get("realtime") or []
    if payload.get("ok") != 1 or not hot_items:
        LOGGER.info("Weibo: no data")
        return []
    query_words = [word for word in query.lower().split() if word]
    results: list[dict] = []
    for item in hot_items:
        word = (item.get("note") or item.get("word") or "").lower()
        if not topic_matches_query(word, query.lower(), query_words):
            continue
        topic = item.get("note") or item.get("word", "")
        results.append(
            {
                "title": f"Weibo Hot Search: {topic}",
                "content": f"Weibo hot topic {topic}, popularity {item.get('num', 0):,}",
                "url": f"https://s.weibo.com/weibo?q={quote('#' + topic + '#')}",
                "source": "weibo",
                "viewCount": item.get("num", 0),
            }
        )
    return results


def topic_matches_query(word: str, query_lower: str, query_words: list[str]) -> bool:
    """Return whether a Weibo topic matches the query."""
    return (
        any(query_word in word or word in query_word for query_word in query_words)
        or query_lower in word
        or word in query_lower
    )


def search_juejin(query: str, limit: int = 20) -> list[dict]:
    """Search Juejin articles."""
    try:
        response = requests.post(
            "https://api.juejin.cn/search_api/v1/search",
            headers={"User-Agent": rand_ua(), "Content-Type": "application/json"},
            json={"key_word": query, "id_type": 0, "limit": limit, "cursor": "0"},
            timeout=15,
            **REQUEST_KWARGS,
        )
        response.raise_for_status()
        payload = response.json()
        results = build_juejin_results(payload, limit)
        LOGGER.info("Juejin: %s results", len(results))
        return results
    except Exception as exc:
        LOGGER.warning("Juejin error: %s", exc)
        return []


def build_juejin_results(payload: dict, limit: int) -> list[dict]:
    """Build normalized Juejin results."""
    result_items = payload.get("data") or []
    if payload.get("err_no") != 0 or not result_items:
        LOGGER.info("Juejin: no results")
        return []
    results: list[dict] = []
    for item in result_items:
        if item.get("result_type") != 2:
            continue
        model = item.get("result_model", {})
        article_info = model.get("article_info", {})
        author_info = model.get("author_user_info", {})
        if not article_info or not article_info.get("article_id"):
            continue
        results.append(
            {
                "title": clean_em_tags(article_info.get("title", "")),
                "content": clean_em_tags(article_info.get("brief_content", "")),
                "url": f"https://juejin.cn/post/{article_info['article_id']}",
                "source": "juejin",
                "sourceId": article_info.get("article_id"),
                "viewCount": article_info.get("view_count", 0),
                "author": {
                    "name": author_info.get("user_name", ""),
                    "username": str(article_info.get("user_id", "")),
                },
                "likeCount": article_info.get("digg_count", 0),
            }
        )
        if len(results) >= limit:
            break
    return results


def clean_em_tags(text: str) -> str:
    """Remove HTML emphasis tags inserted by search results."""
    return text.replace("<em>", "").replace("</em>", "")


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


def maybe_detect_bilibili_account(query: str) -> list[dict]:
    """Detect a Bilibili account and return account metadata plus videos."""
    LOGGER.info("Detecting Bilibili account...")
    user = search_bilibili_user(query)
    if not user:
        LOGGER.info("No matching account found")
        return []
    account_info = {
        "_type": "account_detected",
        "platform": "bilibili",
        "name": user["uname"],
        "mid": user["mid"],
        "fans": user.get("fans", 0),
        "verified": user.get("official_verify", {}).get("type", -1) >= 0,
        "description": user.get("usign", ""),
    }
    LOGGER.info(
        "Found Bilibili account: %s (%s fans)",
        user["uname"],
        user.get("fans", 0),
    )
    time.sleep(2)
    return [account_info, *get_bilibili_user_videos(user["mid"])]


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
    """Run the Chinese platform search command."""
    configure_logging()
    args = parse_args()
    sources = [source.strip().lower() for source in args.sources.split(",") if source.strip()]
    try:
        validate_sources(sources)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return 1
    all_results = []
    if args.detect_account:
        all_results.extend(maybe_detect_bilibili_account(args.query))
    all_results.extend(run_searches(args.query, sources, args.limit))
    LOGGER.info("Total: %s results", len(all_results))
    write_results(all_results, args.out)
    return 0


SEARCH_FNS = {
    "sogou": search_sogou,
    "bilibili": search_bilibili,
    "weibo": search_weibo,
    "juejin": search_juejin,
}


if __name__ == "__main__":
    raise SystemExit(main())
