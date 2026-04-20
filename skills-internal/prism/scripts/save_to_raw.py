#!/usr/bin/env python3
"""Save enriched search results to wiki/raw/ or wiki/signals/."""

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)

DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
MIN_WORD_COUNT = 100
CONTENT_HASH_LEN = 8
SIGNAL_SOURCES = {"bilibili", "weibo"}


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Save enriched search results to wiki/raw/ and wiki/signals/",
    )
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR), help="Path to wiki/ directory")
    parser.add_argument("--keyword", default=None, help="Override keyword for all items")
    parser.add_argument(
        "--min-words",
        type=int,
        default=MIN_WORD_COUNT,
        help="Full-text threshold",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--in", dest="input_file", help="Input JSON file path")
    return parser.parse_args()


def slug(text: str) -> str:
    """Convert text to a safe directory/file slug."""
    lowered_text = text.lower().strip()
    lowered_text = re.sub(r"[^\w\s-]", "", lowered_text)
    lowered_text = re.sub(r"[\s_-]+", "-", lowered_text)
    return lowered_text[:60].strip("-")


def content_hash(text: str) -> str:
    """Build a short content fingerprint."""
    return hashlib.sha256(
        text[:3000].encode("utf-8", errors="replace")
    ).hexdigest()[:CONTENT_HASH_LEN]


def yaml_escape(value: object) -> str:
    """Escape a value for inline YAML."""
    if value is None:
        return '""'
    escaped_value = str(value).replace('"', '\\"').replace("\n", " ")
    return f'"{escaped_value}"'


def build_frontmatter(item: dict, fetched_at: str) -> str:
    """Build Markdown frontmatter for a saved document."""
    lines = [
        "---",
        f'title: {yaml_escape(item.get("title", ""))}',
        f'url: {yaml_escape(item.get("url", ""))}',
        f'source: {item.get("source", "unknown")}',
        f'keyword: {yaml_escape(item.get("keyword", ""))}',
        f'relevance: {item.get("relevance", 0)}',
        f'importance: {item.get("importance", "low")}',
        f'isReal: {str(item.get("isReal", True)).lower()}',
        f"fetchedAt: {fetched_at}",
        f'fetchStatus: {item.get("fetchStatus", "unknown")}',
        f'wordCount: {item.get("wordCount", 0)}',
    ]
    if item.get("summary"):
        lines.append(f'summary: {yaml_escape(item.get("summary"))}')
    if item.get("author"):
        lines.append(f'author: {yaml_escape(extract_author_name(item.get("author")))}')
    if item.get("publishedAt"):
        lines.append(f'publishedAt: {yaml_escape(item.get("publishedAt"))}')
    lines.extend(["compiled: false", "---"])
    return "\n".join(lines) + "\n"


def extract_author_name(author: object) -> str:
    """Extract a printable author name."""
    if isinstance(author, dict):
        return author.get("name", "")
    return str(author)


def build_content(item: dict, frontmatter: str) -> str:
    """Build Markdown content with frontmatter and optional title heading."""
    full_content = item.get("fullContent") or item.get("content") or ""
    if full_content.startswith("#"):
        return frontmatter + "\n" + full_content
    heading = f"# {item.get('title', '')}\n\n" if item.get("title") else ""
    return frontmatter + "\n" + heading + full_content


def meta_record(item: dict, rel_path: str, fetched_at: str) -> dict:
    """Build a lightweight metadata record for _index.json."""
    return {
        "path": rel_path,
        "keyword": item.get("keyword", ""),
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "source": item.get("source", ""),
        "relevance": item.get("relevance", 0),
        "importance": item.get("importance", "low"),
        "isReal": item.get("isReal", True),
        "fetchedAt": fetched_at,
        "fetchStatus": item.get("fetchStatus", "unknown"),
        "wordCount": item.get("wordCount", 0),
        "author": extract_author_name(item.get("author")) if item.get("author") else None,
        "publishedAt": item.get("publishedAt"),
        "compiled": False,
    }


def load_index(index_path: Path) -> dict:
    """Load an index JSON document or return an empty structure."""
    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": []}


def save_index(index_path: Path, index_data: dict) -> None:
    """Persist an index JSON document."""
    index_path.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def existing_urls(index_data: dict) -> set[str]:
    """Collect existing URLs from an index."""
    return {entry.get("url", "") for entry in index_data.get("files", [])}


def load_items(args: argparse.Namespace) -> list[dict]:
    """Load input items from stdin or a file."""
    raw_input = (
        Path(args.input_file).read_text(encoding="utf-8-sig")
        if args.input_file
        else sys.stdin.read()
    )
    items = json.loads(raw_input)
    if not isinstance(items, list):
        raise ValueError("Expected JSON array")
    return items


def is_full_text_item(item: dict, min_words: int) -> bool:
    """Return whether an item belongs in wiki/raw/."""
    return (
        item.get("fetchStatus") == "ok"
        and (item.get("wordCount", 0) or 0) >= min_words
        and item.get("source", "unknown") not in SIGNAL_SOURCES
    )


def save_item(
    item: dict,
    wiki_dir: Path,
    today: str,
    keyword_override: str | None,
    min_words: int,
    layer_state: dict[str, dict],
    dry_run: bool,
) -> str:
    """Route and save one item to the correct layer."""
    normalized_item = normalize_item(item)
    if not has_content(normalized_item):
        LOGGER.info("Skip (empty): %s", normalized_item.get("url", "")[:80])
        return "skipped_empty"
    layer_name = "raw" if is_full_text_item(normalized_item, min_words) else "signals"
    if normalized_item.get("url", "") in layer_state[layer_name]["existing_urls"]:
        LOGGER.info("Skip dup [%s]: %s", layer_name, normalized_item.get("url", "")[:80])
        return "skipped_duplicate"
    return persist_item(
        normalized_item,
        wiki_dir,
        today,
        keyword_override,
        layer_name,
        layer_state[layer_name],
        dry_run,
    )


def normalize_item(item: dict) -> dict:
    """Normalize fetch status defaults for raw search items."""
    if item.get("fetchStatus"):
        return dict(item)
    normalized_item = dict(item)
    normalized_item["fetchStatus"] = "snippet_only"
    return normalized_item


def has_content(item: dict) -> bool:
    """Return whether an item has enough content to persist."""
    full_content = item.get("fullContent") or item.get("content") or ""
    return bool(full_content.strip() or item.get("title"))


def persist_item(
    item: dict,
    wiki_dir: Path,
    today: str,
    keyword_override: str | None,
    layer_name: str,
    state: dict,
    dry_run: bool,
) -> str:
    """Persist one item into its target layer."""
    keyword = keyword_override or item.get("keyword") or "uncategorized"
    item_with_layer = {**item, "keyword": keyword, "layer": layer_name}
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    markdown_path = build_markdown_path(wiki_dir, today, keyword, item_with_layer)
    relative_path = str(markdown_path.relative_to(wiki_dir)).replace("\\", "/")
    metadata = meta_record(item_with_layer, relative_path, fetched_at)
    if not dry_run:
        write_item(markdown_path, item_with_layer, fetched_at, metadata)
        state["index"]["files"].append(metadata)
        state["existing_urls"].add(item.get("url", ""))
    LOGGER.info(
        "%s [%s] (%sw) -> %s",
        "OK" if layer_name == "raw" else "SIG",
        layer_name,
        item.get("wordCount", 0),
        relative_path,
    )
    return f"saved_{layer_name}"


def build_markdown_path(wiki_dir: Path, today: str, keyword: str, item: dict) -> Path:
    """Build the markdown path for a saved item."""
    target_dir = wiki_dir / item["layer"] / today / slug(keyword)
    fingerprint = content_hash(item.get("fullContent") or item.get("content") or item.get("url", ""))
    title_slug = slug(item.get("title", "")) or slug(item.get("source", "unknown"))
    base_name = f"{title_slug}_{fingerprint}"
    return target_dir / f"{base_name}.md"


def write_item(markdown_path: Path, item: dict, fetched_at: str, metadata: dict) -> None:
    """Write markdown and metadata sidecar files."""
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = build_frontmatter(item, fetched_at)
    markdown_path.write_text(build_content(item, frontmatter), encoding="utf-8")
    meta_path = markdown_path.with_suffix(".meta.json")
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def initialize_layer_state(wiki_dir: Path) -> dict[str, dict]:
    """Prepare layer indexes and URL sets."""
    raw_index = load_index(wiki_dir / "raw" / "_index.json")
    signals_index = load_index(wiki_dir / "signals" / "_index.json")
    return {
        "raw": {"index": raw_index, "existing_urls": existing_urls(raw_index)},
        "signals": {
            "index": signals_index,
            "existing_urls": existing_urls(signals_index),
        },
    }


def persist_indexes(wiki_dir: Path, counts: dict[str, int], layer_state: dict[str, dict]) -> None:
    """Persist updated indexes for modified layers."""
    if counts.get("saved_raw", 0) > 0:
        raw_dir = wiki_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        save_index(raw_dir / "_index.json", layer_state["raw"]["index"])
        LOGGER.info("raw index updated: %s", raw_dir / "_index.json")
    if counts.get("saved_signals", 0) > 0:
        signals_dir = wiki_dir / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)
        save_index(signals_dir / "_index.json", layer_state["signals"]["index"])
        LOGGER.info("signals index updated: %s", signals_dir / "_index.json")


def log_summary(counts: dict[str, int]) -> None:
    """Log a summary of the save operation."""
    LOGGER.info(
        "Done: %s -> raw | %s -> signals | %s duplicates | %s empty",
        counts.get("saved_raw", 0),
        counts.get("saved_signals", 0),
        counts.get("skipped_duplicate", 0),
        counts.get("skipped_empty", 0),
    )


def write_stdout_summary(wiki_dir: Path, today: str, counts: dict[str, int]) -> None:
    """Write the machine-readable summary to stdout."""
    summary = {
        "saved_raw": counts.get("saved_raw", 0),
        "saved_signals": counts.get("saved_signals", 0),
        "skipped": counts.get("skipped_duplicate", 0) + counts.get("skipped_empty", 0),
        "wiki_dir": str(wiki_dir),
        "date": today,
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False))
    sys.stdout.write("\n")


def main() -> int:
    """Run the save-to-raw command."""
    configure_logging()
    args = parse_args()
    try:
        items = load_items(args)
    except Exception as exc:
        LOGGER.error("Failed to parse input: %s", exc)
        return 1
    wiki_dir = Path(args.wiki_dir)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    layer_state = initialize_layer_state(wiki_dir)
    counts: dict[str, int] = {}
    for item in items:
        result = save_item(
            item,
            wiki_dir,
            today,
            args.keyword,
            args.min_words,
            layer_state,
            args.dry_run,
        )
        counts[result] = counts.get(result, 0) + 1
    if not args.dry_run:
        persist_indexes(wiki_dir, counts, layer_state)
    log_summary(counts)
    write_stdout_summary(wiki_dir, today, counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
