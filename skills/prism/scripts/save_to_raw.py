#!/usr/bin/env python3
"""
save_to_raw.py — Save enriched search results to wiki/raw/ layer.

Reads enriched JSON array from stdin (output of fetch_content.js),
writes each item as:
  wiki/raw/{YYYY-MM-DD}/{keyword}/{source}_{hash}.md     ← full content with frontmatter
  wiki/raw/{YYYY-MM-DD}/{keyword}/{source}_{hash}.meta.json ← metadata only

Also maintains wiki/raw/_index.json for fast scanning.

Usage:
  cat enriched.json | python save_to_raw.py
  cat enriched.json | python save_to_raw.py --wiki-dir /path/to/wiki
  cat enriched.json | python save_to_raw.py --keyword "harness engineering"
  cat enriched.json | python save_to_raw.py --min-words 50 --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
MIN_WORD_COUNT        = 100      # Full-text threshold for wiki/raw/
CONTENT_HASH_LEN     = 8        # Characters of content fingerprint in filename

# fetchStatus values that mean "no real content extracted"
SIGNAL_STATUSES = {'failed', 'skipped_no_extractor', 'snippet_only', 'ok_low_content'}
# Sources that are always signals (no extractor available)
SIGNAL_SOURCES  = {'bilibili', 'weibo'}


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(*msg):
    print(*msg, file=sys.stderr)

def slug(text: str) -> str:
    """Convert text to a safe directory/file slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:60].strip('-')

def content_hash(text: str) -> str:
    return hashlib.sha256(text[:3000].encode('utf-8', errors='replace')).hexdigest()[:CONTENT_HASH_LEN]

def yaml_escape(value) -> str:
    """Escape a string for inline YAML."""
    if value is None:
        return '""'
    value = str(value).replace('"', '\\"').replace('\n', ' ')
    return f'"{value}"'

def build_frontmatter(item: dict, fetched_at: str) -> str:
    lines = ['---']
    lines.append(f'title: {yaml_escape(item.get("title", ""))}')
    lines.append(f'url: {yaml_escape(item.get("url", ""))}')
    lines.append(f'source: {item.get("source", "unknown")}')
    lines.append(f'keyword: {yaml_escape(item.get("keyword", ""))}')
    lines.append(f'relevance: {item.get("relevance", 0)}')
    lines.append(f'importance: {item.get("importance", "low")}')
    lines.append(f'isReal: {str(item.get("isReal", True)).lower()}')
    if item.get("summary"):
        lines.append(f'summary: {yaml_escape(item.get("summary"))}')
    lines.append(f'fetchedAt: {fetched_at}')
    lines.append(f'fetchStatus: {item.get("fetchStatus", "unknown")}')
    lines.append(f'wordCount: {item.get("wordCount", 0)}')
    if item.get("author"):
        author = item["author"]
        if isinstance(author, dict):
            lines.append(f'author: {yaml_escape(author.get("name", ""))}')
        else:
            lines.append(f'author: {yaml_escape(str(author))}')
    if item.get("publishedAt"):
        lines.append(f'publishedAt: {yaml_escape(item.get("publishedAt"))}')
    lines.append(f'compiled: false')
    lines.append('---')
    return '\n'.join(lines) + '\n'

def build_content(item: dict, frontmatter: str) -> str:
    full_content = item.get("fullContent") or item.get("content") or ""
    title = item.get("title", "")

    # If Defuddle gave us content that already starts with a heading, use as-is
    if full_content.startswith('#'):
        return frontmatter + '\n' + full_content
    
    # Otherwise prepend a title heading
    heading = f'# {title}\n\n' if title else ''
    return frontmatter + '\n' + heading + full_content

def meta_record(item: dict, rel_path: str, fetched_at: str) -> dict:
    """Build a lightweight metadata record for _index.json (no content)."""
    author = item.get("author")
    author_name = None
    if isinstance(author, dict):
        author_name = author.get("name")
    elif isinstance(author, str):
        author_name = author

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
        "author": author_name,
        "publishedAt": item.get("publishedAt"),
        "compiled": False,
    }


# ── Index management ─────────────────────────────────────────────────────────

def load_index(index_path: Path) -> dict:
    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"files": []}

def save_index(index_path: Path, index: dict):
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

def existing_urls(index: dict) -> set:
    return {f.get("url", "") for f in index.get("files", [])}


# ── Core logic ────────────────────────────────────────────────────────────────

def save_item(item: dict, wiki_dir: Path, today: str, keyword_override: str | None,
              existing_raw: set, existing_sig: set,
              index_raw: dict, index_sig: dict,
              dry_run: bool) -> str:
    """
    Route a single item to the appropriate layer:
      - wiki/raw/     → fetchStatus='ok' AND wordCount >= MIN_WORD_COUNT
      - wiki/signals/ → everything else (snippets, bilibili, failed, low-content)

    Returns: 'saved_raw', 'saved_signal', 'skipped_duplicate', 'skipped_empty'
    """
    url          = item.get("url", "")
    fetch_status = item.get("fetchStatus", "")
    word_count   = item.get("wordCount", 0) or 0
    full_content = item.get("fullContent") or item.get("content") or ""
    source       = item.get("source", "unknown")

    # Normalize missing fetchStatus (items straight from search scripts)
    if not fetch_status:
        fetch_status = "snippet_only"
        item = {**item, "fetchStatus": fetch_status}

    # Skip items with truly nothing
    if not full_content.strip() and not item.get("title"):
        log(f'  ⏭  Skip (empty): {url[:80]}')
        return 'skipped_empty'

    # Decide destination layer
    is_full_text = (
        fetch_status == 'ok'
        and word_count >= MIN_WORD_COUNT
        and source not in SIGNAL_SOURCES
    )
    layer      = 'raw' if is_full_text else 'signals'
    existing   = existing_raw if is_full_text else existing_sig
    index      = index_raw   if is_full_text else index_sig

    # URL-level dedup (per layer)
    if url in existing:
        log(f'  ⏭  Skip dup [{layer}]: {url[:80]}')
        return 'skipped_duplicate'

    # Content fingerprint
    fingerprint = content_hash(full_content or url)

    # Build paths
    keyword     = keyword_override or item.get("keyword") or "uncategorized"
    keyword_dir = slug(keyword)
    target_dir  = wiki_dir / layer
    day_dir     = target_dir / today / keyword_dir
    src_slug    = slug(source)
    fetched_at  = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    item_with_kw = {**item, "keyword": keyword, "layer": layer}

    frontmatter = build_frontmatter(item_with_kw, fetched_at)
    content     = build_content(item_with_kw, frontmatter)

    # Build filename from title (human-readable) + short hash (collision-proof)
    title       = item.get("title", "") or ""
    title_slug  = slug(title) if title else src_slug
    base_name = f"{title_slug}_{fingerprint}"
    md_path   = day_dir / f"{base_name}.md"
    meta_path = day_dir / f"{base_name}.meta.json"
    rel_path  = str(md_path.relative_to(wiki_dir)).replace('\\', '/')

    if not dry_run:
        day_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(content, encoding='utf-8')
        meta = meta_record(item_with_kw, rel_path, fetched_at)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        index["files"].append(meta_record(item_with_kw, rel_path, fetched_at))
        existing.add(url)

    icon = '✅' if is_full_text else '📎'
    log(f'  {icon} [{layer}] ({word_count}w) → {rel_path}')
    return f'saved_{layer}'


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Save enriched search results to wiki/raw/ and wiki/signals/')
    parser.add_argument('--wiki-dir',    default=str(DEFAULT_WIKI_DIR), help='Path to wiki/ directory')
    parser.add_argument('--keyword',     default=None, help='Override keyword for all items')
    parser.add_argument('--min-words',   type=int, default=MIN_WORD_COUNT, help='Full-text threshold (default: 100)')
    parser.add_argument('--dry-run',     action='store_true', help='Preview only, do not write files')
    parser.add_argument('--in', dest='in_file', help='Input JSON file path (bypasses stdin)')
    args = parser.parse_args()

    wiki_dir  = Path(args.wiki_dir)
    today     = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    raw_index_path = wiki_dir / "raw"     / "_index.json"
    sig_index_path = wiki_dir / "signals" / "_index.json"

    # Read input
    if args.in_file:
        raw_stdin = Path(args.in_file).read_text(encoding='utf-8')
    else:
        raw_stdin = sys.stdin.read()
        
    try:
        items = json.loads(raw_stdin)
        if not isinstance(items, list):
            raise ValueError('Expected JSON array')
    except Exception as e:
        log(f'❌ Failed to parse stdin: {e}')
        sys.exit(1)

    log(f'\n📥 {len(items)} items to process')
    if args.dry_run:
        log('🔍 Dry-run mode: no files will be written\n')

    # Load existing indexes
    index_raw = load_index(raw_index_path)
    index_sig = load_index(sig_index_path)
    existing_raw = existing_urls(index_raw)
    existing_sig = existing_urls(index_sig)
    log(f'📖 Existing → raw: {len(index_raw["files"])} files | signals: {len(index_sig["files"])} files\n')

    # Process each item
    counts: dict[str, int] = {}
    for item in items:
        result = save_item(
            item, wiki_dir, today, args.keyword,
            existing_raw, existing_sig,
            index_raw, index_sig,
            args.dry_run
        )
        counts[result] = counts.get(result, 0) + 1

    # Persist indexes
    if not args.dry_run:
        if counts.get('saved_raw', 0) > 0:
            (wiki_dir / 'raw').mkdir(parents=True, exist_ok=True)
            save_index(raw_index_path, index_raw)
            log(f'\n💾 raw index updated: {raw_index_path}')
        if counts.get('saved_signals', 0) > 0:
            (wiki_dir / 'signals').mkdir(parents=True, exist_ok=True)
            save_index(sig_index_path, index_sig)
            log(f'💾 signals index updated: {sig_index_path}')

    n_raw  = counts.get('saved_raw', 0)
    n_sig  = counts.get('saved_signals', 0)
    n_dup  = counts.get('skipped_duplicate', 0)
    n_skip = counts.get('skipped_empty', 0)

    log(f'\n✨ Done: {n_raw} → raw/ (full text) | {n_sig} → signals/ (snippet) | {n_dup} duplicates | {n_skip} empty')

    if n_raw > 0:
        log(f'💡 Run the prism skill to organize wiki/raw/ into wiki/pages/')
    if n_sig > 0:
        log(f'💡 signals/ contains {n_sig} snippet-only references — review manually or run prism to aggregate')

    print(json.dumps({
        "saved_raw": n_raw,
        "saved_signals": n_sig,
        "skipped": n_dup + n_skip,
        "wiki_dir": str(wiki_dir),
        "date": today,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
