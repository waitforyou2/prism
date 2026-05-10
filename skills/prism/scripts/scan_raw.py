#!/usr/bin/env python3
"""Scan wiki/raw/ for uncompiled files."""

import argparse
import json
import sys
from pathlib import Path


DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
IMPORTANCE_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
IMPORTANCE_ICONS = {
    "urgent": "Urgent",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def load_index(wiki_dir: Path) -> list[dict]:
    index_path = wiki_dir / "raw" / "_index.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"Failed to read index: {exc}", file=sys.stderr)
        return []
    return data.get("files", [])


def index_paths(wiki_dir: Path, records: list[dict]) -> set[Path]:
    paths = set()
    for record in records:
        record_path = record.get("path")
        if record_path:
            paths.add((wiki_dir / record_path).resolve())
    return paths


def find_orphan_markdown(wiki_dir: Path) -> list[Path]:
    raw_dir = wiki_dir / "raw"
    if not raw_dir.exists():
        return []

    indexed_paths = index_paths(wiki_dir, load_index(wiki_dir))
    orphans = []
    for md_path in sorted(raw_dir.rglob("*.md")):
        rel_parts = md_path.relative_to(raw_dir).parts
        if any(part in {"originals", "__pycache__"} for part in rel_parts[:-1]):
            continue
        if md_path.resolve() in indexed_paths:
            continue
        orphans.append(md_path)
    return orphans


def format_words(word_count: int) -> str:
    if word_count == 0:
        return "snippet only"
    if word_count >= 1000:
        return f"{word_count / 1000:.1f}k words"
    return f"{word_count} words"


def select_unprocessed(files: list[dict], keyword: str | None) -> list[dict]:
    unprocessed = [record for record in files if not record.get("compiled", False)]
    if keyword:
        lowered_keyword = keyword.lower()
        unprocessed = [
            record
            for record in unprocessed
            if lowered_keyword in record.get("keyword", "").lower()
        ]
    unprocessed.sort(
        key=lambda record: (
            IMPORTANCE_ORDER.get(record.get("importance", "low"), 3),
            -(record.get("relevance", 0)),
        )
    )
    return unprocessed


def write_json_output(unprocessed: list[dict]) -> None:
    print(json.dumps(unprocessed, ensure_ascii=False, indent=2))


def write_markdown_output(unprocessed: list[dict], wiki_dir: Path) -> None:
    print(f"## Pending files ({len(unprocessed)})\n")
    print(f"> wiki dir: `{wiki_dir}`\n")

    groups: dict[str, list[dict]] = {}
    for record in unprocessed:
        groups.setdefault(record.get("importance", "low"), []).append(record)

    for importance_key in ["urgent", "high", "medium", "low"]:
        records = groups.get(importance_key, [])
        if not records:
            continue
        print(f"### {IMPORTANCE_ICONS[importance_key]} ({len(records)})\n")
        for record in records:
            title = record.get("title", "(no title)")[:70]
            keyword = record.get("keyword", "")
            source = record.get("source", "")
            relevance = record.get("relevance", 0)
            fetched_at = (record.get("fetchedAt") or "")[:10]
            print(f"- **{title}**")
            print(
                f"  keyword: `{keyword}` | source: {source} | relevance: {relevance}"
                f" | {format_words(record.get('wordCount', 0))} | {fetched_at}"
            )
            print(f"  path: `{record.get('path', '')}`")
            if record.get("url"):
                print(f"  url: {record['url']}")
            print()

    print("---")
    print("*Run the `prism` skill following `wiki/WIKI.md` to organize these files into `wiki/pages/`.*")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan wiki/raw/ for unprocessed files")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--keyword", default=None, help="Filter by keyword")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    orphans = find_orphan_markdown(wiki_dir)
    if orphans:
        print(
            f"warning: found {len(orphans)} orphan raw markdown file(s); run normalize_raw.py before scanning",
            file=sys.stderr,
        )

    files = load_index(wiki_dir)
    unprocessed = select_unprocessed(files, args.keyword)

    if args.json:
        write_json_output(unprocessed)
    elif unprocessed:
        write_markdown_output(unprocessed, wiki_dir)
    else:
        print("No uncompiled files in wiki/raw/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
