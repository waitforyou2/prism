#!/usr/bin/env python3
"""Create a compile plan for pending Prism raw records."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
IMPORTANCE_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


def load_index(wiki_dir: Path) -> list[dict]:
    index_path = wiki_dir / "raw" / "_index.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    return data.get("files", [])


def pending_records(records: list[dict], keyword: str | None = None) -> list[dict]:
    pending = [record for record in records if not record.get("compiled", False)]
    if keyword:
        lowered = keyword.lower()
        pending = [
            record
            for record in pending
            if lowered in str(record.get("keyword", "")).lower()
        ]
    pending.sort(
        key=lambda record: (
            IMPORTANCE_ORDER.get(record.get("importance", "low"), 3),
            -(record.get("relevance", 0) or 0),
            record.get("title", ""),
        )
    )
    return pending


def record_line(record: dict) -> str:
    path = record.get("path", "")
    title = record.get("title") or "(untitled)"
    importance = record.get("importance", "low")
    relevance = record.get("relevance", 0)
    words = record.get("wordCount", 0)
    source = record.get("source", "")
    return (
        f"- [ ] `{path}` — {title} | importance: {importance} | "
        f"relevance: {relevance} | words: {words} | source: {source}"
    )


def build_plan(records: list[dict], wiki_dir: Path) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "# Prism Compile Plan",
        "",
        f"> Generated: {now} | wiki: `{wiki_dir}` | pending raw: {len(records)}",
        "",
        "## Raw Coverage Checklist",
        "",
        "Mark each raw source only after its facts, entities, concepts, and useful claims have been absorbed into pages.",
        "",
    ]
    if records:
        lines.extend(record_line(record) for record in records)
    else:
        lines.append("_No uncompiled raw records found._")

    lines.extend(
        [
            "",
            "## Extraction Table",
            "",
            "Fill this table during compilation. Add multiple rows for a raw source when it contains multiple reusable knowledge atoms.",
            "",
            "| Raw Source | Entity | Concept | Claim / Detail | Target Page | Status |",
            "| --- | --- | --- | --- | --- | --- |",
            "| `raw/...` |  |  |  | `pages/...` | planned |",
            "",
            "## Overview Coverage",
            "",
            "High-value raw sources (`urgent`, `high`, or relevance >= 80) must be reflected in at least one overview page.",
            "",
        ]
    )
    high_value = [
        record
        for record in records
        if record.get("importance") in {"urgent", "high"}
        or (record.get("relevance", 0) or 0) >= 80
    ]
    if high_value:
        lines.extend(f"- [ ] `{record.get('path', '')}`" for record in high_value)
    else:
        lines.append("_No high-value pending raw records._")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Prism raw coverage compile plan")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    records = pending_records(load_index(wiki_dir), keyword=args.keyword)
    output_path = Path(args.out) if args.out else wiki_dir / "compile_plan.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_plan(records, wiki_dir), encoding="utf-8")
    print(f"Updated {output_path}")
    print(f"Pending raw records: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
