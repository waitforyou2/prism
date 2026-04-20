#!/usr/bin/env python3
"""Scan wiki/raw/ for unprocessed files and emit JSON or Markdown output."""

import argparse
import json
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)

DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
IMPORTANCE_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
IMPORTANCE_ICONS = {
    "urgent": "Urgent",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Scan wiki/raw/ for unprocessed files")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--keyword", default=None, help="Filter by keyword")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
    return parser.parse_args()


def load_index(wiki_dir: Path) -> list[dict]:
    """Load the raw index file when present."""
    index_path = wiki_dir / "raw" / "_index.json"
    if not index_path.exists():
        return []
    try:
        loaded_index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        LOGGER.error("Failed to read index: %s", exc)
        return []
    return loaded_index.get("files", [])


def load_meta_files(wiki_dir: Path) -> list[dict]:
    """Load metadata sidecar files from wiki/raw/."""
    raw_dir = wiki_dir / "raw"
    if not raw_dir.exists():
        return []

    records: list[dict] = []
    for meta_path in sorted(raw_dir.rglob("*.meta.json")):
        try:
            records.append(json.loads(meta_path.read_text(encoding="utf-8-sig")))
        except Exception as exc:
            LOGGER.warning("Failed to read meta file %s: %s", meta_path, exc)
    return records


def format_words(word_count: int) -> str:
    """Format a word count for display."""
    if word_count == 0:
        return "snippet only"
    if word_count >= 1000:
        return f"{word_count / 1000:.1f}k words"
    return f"{word_count} words"


def select_unprocessed(files: list[dict], keyword: str | None) -> list[dict]:
    """Return unprocessed files filtered by keyword when requested."""
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
    """Write JSON output to stdout."""
    sys.stdout.write(json.dumps(unprocessed, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def write_markdown_output(unprocessed: list[dict], wiki_dir: Path) -> None:
    """Write Markdown output to stdout."""
    output_lines = [
        f"## Pending files ({len(unprocessed)})",
        "",
        f"> wiki dir: `{wiki_dir}`",
        "",
    ]
    grouped_records: dict[str, list[dict]] = {}
    for record in unprocessed:
        grouped_records.setdefault(record.get("importance", "low"), []).append(record)

    for importance_key in ["urgent", "high", "medium", "low"]:
        records = grouped_records.get(importance_key, [])
        if not records:
            continue
        output_lines.append(f"### {IMPORTANCE_ICONS[importance_key]} ({len(records)})")
        output_lines.append("")
        output_lines.extend(build_record_lines(records))

    output_lines.append("---")
    output_lines.append(
        "*Run the `prism` skill following `wiki/WIKI.md` to organize these files into `wiki/pages/`.*"
    )
    sys.stdout.write("\n".join(output_lines))
    sys.stdout.write("\n")


def build_record_lines(records: list[dict]) -> list[str]:
    """Build Markdown lines for a group of records."""
    output_lines: list[str] = []
    for record in records:
        output_lines.append(f"- **{record.get('title', '(no title)')[:70]}**")
        output_lines.append(
            "  keyword: `{keyword}` | source: {source} | relevance: {relevance}"
            " | {words} | {date}".format(
                keyword=record.get("keyword", ""),
                source=record.get("source", ""),
                relevance=record.get("relevance", 0),
                words=format_words(record.get("wordCount", 0)),
                date=(record.get("fetchedAt") or "")[:10],
            )
        )
        output_lines.append(f"  path: `{record.get('path', '')}`")
        record_url = record.get("url", "")
        if record_url:
            output_lines.append(f"  url: {record_url}")
        output_lines.append("")
    return output_lines


def main() -> int:
    """Run the raw scan command."""
    configure_logging()
    args = parse_args()
    wiki_dir = Path(args.wiki_dir)
    files = load_meta_files(wiki_dir) or load_index(wiki_dir)
    unprocessed = select_unprocessed(files, args.keyword)

    if not unprocessed:
        if args.json:
            write_json_output([])
        else:
            sys.stdout.write("No uncompiled files in wiki/raw/\n")
        return 0

    if args.json:
        write_json_output(unprocessed)
    else:
        write_markdown_output(unprocessed, wiki_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
