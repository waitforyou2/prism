#!/usr/bin/env python3
"""Twitter/X search via twitterapi.io."""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

LOGGER = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()

REQUEST_KWARGS = {"verify": False}
TWITTER_API_BASE = "https://api.twitterapi.io"
MIN_LIKES = 10
MIN_RETWEETS = 5
MIN_VIEWS = 500
MIN_FOLLOWERS = 100


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Twitter search via twitterapi.io")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    parser.add_argument("--trends", action="store_true", help="Get worldwide trending topics")
    parser.add_argument("--user", help="Get latest tweets from a specific user")
    parser.add_argument("--out", help="Output JSON file path")
    return parser.parse_args()


def get_api_key() -> str:
    """Read the Twitter API key from the environment."""
    api_key = os.environ.get("TWITTER_API_KEY")
    if not api_key:
        raise ValueError("TWITTER_API_KEY environment variable not set")
    return api_key


def api_request(endpoint: str, params: dict | None = None) -> dict:
    """Make an authenticated request to twitterapi.io."""
    response = requests.get(
        f"{TWITTER_API_BASE}{endpoint}",
        params=params or {},
        headers={
            "X-API-Key": get_api_key(),
            "Content-Type": "application/json",
        },
        timeout=30,
        **REQUEST_KWARGS,
    )
    response.raise_for_status()
    return response.json()


def format_since_date(days_ago: int) -> str:
    """Format a UTC date string for Twitter search queries."""
    target_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return target_date.strftime("%Y-%m-%d")


def build_query(keyword: str, query_type: str) -> str:
    """Build an advanced search query."""
    query_parts = [keyword, "-filter:retweets", "-filter:replies"]
    query_parts.append(
        f"since:{format_since_date(7 if query_type == 'Top' else 3)}"
    )
    if query_type == "Top":
        query_parts.append("min_faves:10")
    return " ".join(query_parts)


def fetch_page(
    query: str,
    query_type: str,
    cursor: str | None = None,
) -> tuple[list[dict], str | None]:
    """Fetch one page of tweet search results."""
    params = {"query": query, "queryType": query_type}
    if cursor:
        params["cursor"] = cursor
    payload = api_request("/twitter/tweet/advanced_search", params)
    tweets = payload.get("tweets", [])
    if not isinstance(tweets, list):
        tweets = []
    next_cursor = payload.get("next_cursor") if payload.get("has_next_page") else None
    return tweets, next_cursor


def quality_filter(tweets: list[dict]) -> list[dict]:
    """Filter and rank tweets by quality metrics."""
    filtered_tweets: list[dict] = []
    for tweet in tweets:
        if "reply" in tweet.get("type", "").lower():
            continue
        if re.match(r"^@\w+\s", tweet.get("text", "").strip()):
            continue
        author = tweet.get("author", {})
        threshold_factor = 0.5 if author.get("isBlueVerified") else 1.0
        if tweet.get("likeCount", 0) < MIN_LIKES * threshold_factor:
            continue
        if tweet.get("retweetCount", 0) < MIN_RETWEETS * threshold_factor:
            continue
        if tweet.get("viewCount", 0) < MIN_VIEWS * threshold_factor:
            continue
        if author.get("followers", 0) < MIN_FOLLOWERS * threshold_factor:
            continue
        filtered_tweets.append(tweet)
    filtered_tweets.sort(key=score_tweet, reverse=True)
    return filtered_tweets


def score_tweet(tweet: dict) -> float:
    """Compute a quality score for a tweet."""
    score = (
        tweet.get("likeCount", 0) * 2
        + tweet.get("retweetCount", 0) * 3
        + tweet.get("viewCount", 0) / 100
    )
    if tweet.get("author", {}).get("isBlueVerified"):
        score += 50
    return score


def tweet_to_result(tweet: dict) -> dict:
    """Convert a raw tweet to the unified result format."""
    author = tweet.get("author", {})
    return {
        "title": tweet.get("text", "")[:100],
        "content": tweet.get("text", ""),
        "url": tweet.get("url", ""),
        "source": "twitter",
        "sourceId": tweet.get("id"),
        "publishedAt": tweet.get("createdAt"),
        "viewCount": tweet.get("viewCount", 0),
        "likeCount": tweet.get("likeCount", 0),
        "retweetCount": tweet.get("retweetCount", 0),
        "replyCount": tweet.get("replyCount", 0),
        "quoteCount": tweet.get("quoteCount", 0),
        "author": {
            "name": author.get("name", ""),
            "username": author.get("userName", ""),
            "avatar": author.get("profilePicture", ""),
            "followers": author.get("followers", 0),
            "verified": author.get("isBlueVerified", False),
        },
    }


def search_twitter(query: str, limit: int = 20) -> list[dict]:
    """Run the Twitter search workflow."""
    top_query = build_query(query, "Top")
    latest_query = build_query(query, "Latest")
    LOGGER.info("Top query: %s", top_query)
    LOGGER.info("Latest query: %s", latest_query)

    all_tweets: list[dict] = []
    seen_ids: set[str] = set()
    top_cursor = None

    top_cursor = fetch_search_batch(top_query, "Top", seen_ids, all_tweets)
    fetch_search_batch(latest_query, "Latest", seen_ids, all_tweets)
    if top_cursor:
        fetch_search_batch(top_query, "Top", seen_ids, all_tweets, cursor=top_cursor)

    LOGGER.info("Unique tweets: %s", len(all_tweets))
    filtered_tweets = quality_filter(all_tweets)
    LOGGER.info("After quality filter: %s", len(filtered_tweets))
    return [tweet_to_result(tweet) for tweet in filtered_tweets[:limit]]


def fetch_search_batch(
    query: str,
    query_type: str,
    seen_ids: set[str],
    all_tweets: list[dict],
    cursor: str | None = None,
) -> str | None:
    """Fetch one batch and extend the shared tweet collection."""
    page_label = "2" if cursor else "1"
    try:
        tweets, next_cursor = fetch_page(query, query_type, cursor)
    except Exception as exc:
        LOGGER.warning("%s page %s error: %s", query_type, page_label, exc)
        return None
    append_new_tweets(tweets, seen_ids, all_tweets)
    LOGGER.info("%s page %s: %s tweets", query_type, page_label, len(tweets))
    return next_cursor


def append_new_tweets(
    tweets: list[dict],
    seen_ids: set[str],
    all_tweets: list[dict],
) -> None:
    """Append tweets that have not been seen before."""
    for tweet in tweets:
        tweet_id = tweet.get("id")
        if tweet_id and tweet_id not in seen_ids:
            seen_ids.add(tweet_id)
            all_tweets.append(tweet)


def get_trends() -> list[dict]:
    """Get worldwide Twitter trends."""
    return api_request("/twitter/trends", {"woeid": "1"}).get("trends", [])


def get_user_tweets(username: str) -> list[dict]:
    """Get a user's latest tweets."""
    tweets = api_request("/twitter/user/last_tweets", {"userName": username}).get(
        "tweets",
        [],
    )
    if not isinstance(tweets, list):
        return []
    return [tweet_to_result(tweet) for tweet in tweets]


def resolve_results(args: argparse.Namespace) -> list[dict]:
    """Resolve which result set should be produced from arguments."""
    if args.trends:
        return get_trends()
    if args.user:
        return get_user_tweets(args.user)
    if args.query:
        return search_twitter(args.query, args.limit)
    raise ValueError("A query, --trends, or --user option is required")


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
    """Run the Twitter search command."""
    configure_logging()
    args = parse_args()
    try:
        results = resolve_results(args)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return 1
    write_results(results, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
