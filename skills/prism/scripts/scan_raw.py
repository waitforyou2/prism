#!/usr/bin/env python3
"""
scan_raw.py — Scan wiki/raw/ for unprocessed files and print a prioritized list.

Reads wiki/raw/_index.json, filters for unprocessed items,
sorts by importance + relevance, and outputs a formatted Markdown
report for the AI to read before deciding how to organize pages.

Usage:
  python scan_raw.py
  python scan_raw.py --wiki-dir /path/to/wiki
  python scan_raw.py --keyword "harness engineering"   # filter by keyword
  python scan_raw.py --json                            # output raw JSON instead of Markdown
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_WIKI_DIR = Path.cwd() / "wiki"

IMPORTANCE_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
IMPORTANCE_ICONS = {
    "urgent": "🚨 Urgent",
    "high":   "🔴 High",
    "medium": "🟡 Medium",
    "low":    "🟢 Low",
}


def load_index(wiki_dir: Path) -> list:
    index_path = wiki_dir / "raw" / "_index.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding='utf-8'))
        return data.get("files", [])
    except Exception as e:
        print(f"❌ Failed to read index: {e}", file=sys.stderr)
        return []


def format_words(n: int) -> str:
    if n == 0:
        return "snippet only"
    if n >= 1000:
        return f"{n/1000:.1f}k words"
    return f"{n} words"


def main():
    parser = argparse.ArgumentParser(description='Scan wiki/raw/ for unprocessed files')
    parser.add_argument('--wiki-dir', default=str(DEFAULT_WIKI_DIR))
    parser.add_argument('--keyword',  default=None, help='Filter by keyword')
    parser.add_argument('--json',     action='store_true', help='Output JSON instead of Markdown')
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    files = load_index(wiki_dir)

    # Filter
    unprocessed = [f for f in files if not f.get("processed", False)]
    if args.keyword:
        unprocessed = [f for f in unprocessed if args.keyword.lower() in f.get("keyword", "").lower()]

    if not unprocessed:
        if args.json:
            print("[]")
        else:
            print("✅ No unprocessed files in wiki/raw/")
        return

    # Sort: importance asc (urgent first), then relevance desc
    unprocessed.sort(key=lambda f: (
        IMPORTANCE_ORDER.get(f.get("importance", "low"), 3),
        -(f.get("relevance", 0))
    ))

    if args.json:
        print(json.dumps(unprocessed, ensure_ascii=False, indent=2))
        return

    # Markdown output
    print(f"## 📥 待处理文件（共 {len(unprocessed)} 个）\n")
    print(f"> wiki 目录: `{wiki_dir}`\n")

    # Group by importance
    groups: dict[str, list] = {}
    for f in unprocessed:
        imp = f.get("importance", "low")
        groups.setdefault(imp, []).append(f)

    for imp_key in ["urgent", "high", "medium", "low"]:
        items = groups.get(imp_key, [])
        if not items:
            continue
        label = IMPORTANCE_ICONS[imp_key]
        print(f"### {label} ({len(items)})\n")
        for f in items:
            words_str  = format_words(f.get("wordCount", 0))
            relevance  = f.get("relevance", 0)
            source     = f.get("source", "")
            keyword    = f.get("keyword", "")
            title      = f.get("title", "(no title)")[:70]
            path       = f.get("path", "")
            url        = f.get("url", "")
            fetched_at = (f.get("fetchedAt") or "")[:10]

            print(f"- **{title}**")
            print(f"  keyword: `{keyword}` | source: {source} | relevance: {relevance} | {words_str} | {fetched_at}")
            print(f"  path: `{path}`")
            if url:
                print(f"  url: {url}")
            print()

    print("---")
    print(f"*运行 `prism` skill 按照 `wiki/CLAUDE.md` 的规范将这些内容整理到 `wiki/pages/`*")


if __name__ == "__main__":
    main()
