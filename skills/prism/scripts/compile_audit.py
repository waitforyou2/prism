#!/usr/bin/env python3
"""Audit whether compiled Prism raw records are represented in wiki pages."""

import argparse
import json
import re
from pathlib import Path


DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
RAW_LINK_RE = re.compile(r"\[\[(raw/[^]\n]+?)\]\]")


def load_index(wiki_dir: Path) -> list[dict]:
    index_path = wiki_dir / "raw" / "_index.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    return data.get("files", [])


def normalize_raw_link(link: str) -> str:
    return link.split("|", 1)[0].strip()


def read_page_citations(wiki_dir: Path) -> tuple[dict[str, set[str]], set[str], set[str]]:
    pages_dir = wiki_dir / "pages"
    citations_by_page: dict[str, set[str]] = {}
    all_citations: set[str] = set()
    overview_citations: set[str] = set()
    if not pages_dir.exists():
        return citations_by_page, all_citations, overview_citations

    for page_path in sorted(pages_dir.rglob("*.md")):
        if page_path.name == "_index.md":
            continue
        try:
            text = page_path.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        rel_page = page_path.relative_to(wiki_dir).as_posix()
        citations = {normalize_raw_link(link) for link in RAW_LINK_RE.findall(text)}
        citations_by_page[rel_page] = citations
        all_citations.update(citations)
        try:
            rel_parts = page_path.relative_to(pages_dir).parts
        except ValueError:
            rel_parts = ()
        if rel_parts and rel_parts[0] == "overview":
            overview_citations.update(citations)
    return citations_by_page, all_citations, overview_citations


def is_high_value(record: dict) -> bool:
    return record.get("importance") in {"urgent", "high"} or (record.get("relevance", 0) or 0) >= 80


def audit(wiki_dir: Path) -> dict:
    records = load_index(wiki_dir)
    citations_by_page, all_citations, overview_citations = read_page_citations(wiki_dir)
    compiled = [record for record in records if record.get("compiled", False)]
    pending = [record for record in records if not record.get("compiled", False)]
    compiled_paths = [record.get("path", "") for record in compiled if record.get("path")]

    uncited_compiled_raw = [
        path
        for path in compiled_paths
        if path not in all_citations
    ]
    high_value_missing_from_overview = [
        record.get("path", "")
        for record in compiled
        if record.get("path")
        and is_high_value(record)
        and record.get("path") not in overview_citations
    ]
    pages_without_raw_citations = [
        page
        for page, citations in citations_by_page.items()
        if not citations
    ]

    failures = uncited_compiled_raw or high_value_missing_from_overview
    return {
        "status": "fail" if failures else "pass",
        "total_raw_records": len(records),
        "compiled_raw_records": len(compiled),
        "pending_raw_records": len(pending),
        "page_count": len(citations_by_page),
        "uncited_compiled_raw": uncited_compiled_raw,
        "high_value_missing_from_overview": high_value_missing_from_overview,
        "pages_without_raw_citations": pages_without_raw_citations,
    }


def write_markdown_report(report: dict) -> None:
    print(f"# Prism Compile Audit: {report['status'].upper()}")
    print()
    print(
        f"- raw records: {report['total_raw_records']} | compiled: "
        f"{report['compiled_raw_records']} | pending: {report['pending_raw_records']}"
    )
    print(f"- pages scanned: {report['page_count']}")
    print()
    for key, title in [
        ("uncited_compiled_raw", "Compiled Raw Without Page Citation"),
        ("high_value_missing_from_overview", "High-Value Raw Missing From Overview"),
        ("pages_without_raw_citations", "Pages Without Raw Citations"),
    ]:
        print(f"## {title}")
        values = report[key]
        if values:
            for value in values:
                print(f"- `{value}`")
        else:
            print("- None")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Prism compiled raw coverage")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = audit(Path(args.wiki_dir))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        write_markdown_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
