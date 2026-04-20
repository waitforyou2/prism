#!/usr/bin/env python3
"""Rebuild wiki/index.md from existing page files."""

import argparse
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)

DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
TYPE_ICONS = {
    "concept": "Concept",
    "entity": "Entity",
    "synthesis": "Synthesis",
    "overview": "Overview",
    "other": "Other",
}
TYPE_LABELS = {
    "concept": "Concepts",
    "entity": "Entities",
    "synthesis": "Syntheses",
    "overview": "Overviews",
    "other": "Misc",
}
ENTITY_TYPE_ICONS = {
    "person": "Person",
    "tool": "Tool",
    "company": "Company",
    "product": "Product",
}


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Rebuild wiki/index.md")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument(
        "--kb-id",
        default="",
        help="Knowledge base ID to embed in frontmatter",
    )
    return parser.parse_args()


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a Markdown file."""
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = pattern.match(text)
    if not match:
        return {}
    frontmatter: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter


def get_first_paragraph(text: str) -> str:
    """Extract the first non-heading paragraph from Markdown."""
    in_frontmatter = False
    finished_frontmatter = False
    for line in text.splitlines():
        if line.strip() == "---" and not finished_frontmatter:
            in_frontmatter = not in_frontmatter
            finished_frontmatter = finished_frontmatter or not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if line.startswith("#") or not line.strip():
            continue
        return line.strip()[:100]
    return ""


def scan_pages(wiki_dir: Path) -> dict[str, list[dict]]:
    """Scan wiki/pages/ and group pages by type."""
    groups: dict[str, list[dict]] = {
        "overview": [],
        "concept": [],
        "entity": [],
        "synthesis": [],
        "other": [],
    }
    pages_dir = wiki_dir / "pages"
    for markdown_file in sorted(pages_dir.rglob("*.md")):
        if markdown_file.name == "_index.md":
            continue
        try:
            text = markdown_file.read_text(encoding="utf-8")
        except Exception:
            continue
        frontmatter = parse_frontmatter(text)
        page_type = frontmatter.get("type", "other")
        groups.setdefault(page_type, groups["other"]).append(
            {
                "title": frontmatter.get("title") or markdown_file.stem,
                "path": markdown_file.relative_to(wiki_dir).as_posix(),
                "tags": frontmatter.get("tags", ""),
                "updated": frontmatter.get("updated", ""),
                "entity_type": frontmatter.get("entity_type", ""),
                "description": get_first_paragraph(text),
            }
        )
    return groups


def collect_tags(groups: dict[str, list[dict]]) -> set[str]:
    """Collect all tags mentioned in grouped page metadata."""
    all_tags: set[str] = set()
    for page_group in groups.values():
        for page in page_group:
            raw_tags = page.get("tags")
            if not raw_tags:
                continue
            for raw_tag in str(raw_tags).split(","):
                clean_tag = raw_tag.strip().strip("[]'\" ")
                if clean_tag:
                    all_tags.add(clean_tag)
    return all_tags


def build_kb_summary(groups: dict[str, list[dict]]) -> str:
    """Generate a concise summary of the knowledge base."""
    all_tags = collect_tags(groups)
    all_titles = [page["title"] for group in groups.values() for page in group]
    summary_lines: list[str] = []
    if all_tags:
        summary_lines.append(f"**Tags**: {', '.join(sorted(all_tags))}")
    if all_titles:
        preview = ", ".join(all_titles[:15])
        suffix = f" ... total {len(all_titles)} topics" if len(all_titles) > 15 else ""
        summary_lines.append(f"**Topics**: {preview}{suffix}")
    return "\n".join(summary_lines) if summary_lines else "(empty knowledge base)"


def build_index(groups: dict[str, list[dict]], wiki_dir: Path, kb_id: str = "") -> str:
    """Build the generated index.md content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_pages = sum(len(group) for group in groups.values())
    all_tags = collect_tags(groups)
    frontmatter_lines = ["---"]
    if kb_id:
        frontmatter_lines.append(f"kb_id: {kb_id}")
    frontmatter_lines.append(f"page_count: {total_pages}")
    frontmatter_lines.append(f"updated: {now}")
    if all_tags:
        frontmatter_lines.append(f"tags: [{', '.join(sorted(all_tags))}]")
    frontmatter_lines.extend(["---", ""])
    output_lines = frontmatter_lines + [
        "# Prism Wiki Index",
        "",
        f"> Last updated: {now} | Total {total_pages} pages",
        "",
        "## Knowledge Base Summary",
        "",
        build_kb_summary(groups),
        "",
        "---",
        "",
    ]
    for type_key in ["overview", "concept", "entity", "synthesis", "other"]:
        page_group = groups.get(type_key, [])
        if not page_group:
            continue
        output_lines.append(
            f"## {TYPE_ICONS.get(type_key, 'Other')} "
            f"{TYPE_LABELS.get(type_key, type_key.title())} ({len(page_group)})"
        )
        output_lines.append("")
        output_lines.extend(build_page_lines(type_key, page_group))
        output_lines.append("")
    output_lines.append("---")
    output_lines.append("*This file is generated by `update_index.py`. Do not edit manually.*")
    return "\n".join(output_lines) + "\n"


def build_page_lines(type_key: str, page_group: list[dict]) -> list[str]:
    """Build index lines for a page group."""
    output_lines: list[str] = []
    for page in sorted(page_group, key=lambda entry: entry["title"].lower()):
        title = page["title"]
        if type_key == "entity" and page.get("entity_type"):
            prefix = ENTITY_TYPE_ICONS.get(page["entity_type"], "")
            if prefix:
                title = f"{prefix} {title}"
        if page["description"]:
            output_lines.append(f"- [[{title}]]({page['path']}) - {page['description']}")
        else:
            output_lines.append(f"- [[{title}]]({page['path']})")
    return output_lines


def main() -> int:
    """Run the index rebuild command."""
    configure_logging()
    args = parse_args()
    wiki_dir = Path(args.wiki_dir)
    pages_dir = wiki_dir / "pages"
    if not pages_dir.exists():
        LOGGER.error("pages/ directory not found: %s", pages_dir)
        return 1
    groups = scan_pages(wiki_dir)
    total_pages = sum(len(group) for group in groups.values())
    if total_pages == 0:
        LOGGER.info("No pages found in wiki/pages/ - index not updated")
        return 0
    knowledge_base_id = args.kb_id or wiki_dir.parent.name
    content = build_index(groups, wiki_dir, knowledge_base_id)
    index_path = wiki_dir / "index.md"
    index_path.write_text(content, encoding="utf-8")
    LOGGER.info("Updated %s", index_path)
    LOGGER.info(
        "%s",
        ", ".join(
            f"{len(groups[group_name])} {group_name}s"
            for group_name in ["overview", "concept", "entity", "synthesis"]
            if groups[group_name]
        ),
    )
    if knowledge_base_id:
        LOGGER.info("kb_id: %s", knowledge_base_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
