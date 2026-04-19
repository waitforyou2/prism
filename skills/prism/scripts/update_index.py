#!/usr/bin/env python3
"""
update_index.py — Rebuild wiki/pages/_index.md from existing page files.

Scans wiki/pages/ for all .md files, reads their frontmatter,
and regenerates the _index.md table of contents.

Also writes machine-readable frontmatter to index.md so that
discover.py can extract KB metadata without full parsing.

Usage:
  python update_index.py
  python update_index.py --wiki-dir /path/to/wiki
  python update_index.py --wiki-dir /path/to/wiki --kb-id claude
"""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_WIKI_DIR = Path.cwd() / "wiki"

TYPE_ICONS = {
    "concept":   "📐",
    "entity":    "👤",
    "synthesis": "🔬",
}

TYPE_LABELS = {
    "concept":   "Concepts",
    "entity":    "Entities",
    "synthesis": "Syntheses",
}

ENTITY_TYPE_ICONS = {
    "person":   "🧑",
    "tool":     "🔧",
    "company":  "🏢",
    "product":  "📦",
}


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a Markdown file."""
    pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = pattern.match(text)
    if not match:
        return {}

    fm: dict = {}
    for line in match.group(1).splitlines():
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        key   = key.strip()
        value = value.strip().strip('"').strip("'")
        fm[key] = value
    return fm


def get_first_paragraph(text: str) -> str:
    """Extract the first non-heading paragraph from Markdown."""
    in_frontmatter = False
    found_end = False
    for line in text.splitlines():
        if line.strip() == '---':
            if not found_end:
                in_frontmatter = True
                continue
        if in_frontmatter and line.strip() == '---':
            in_frontmatter = False
            found_end = True
            continue
        if in_frontmatter:
            continue
        if line.startswith('#') or not line.strip():
            continue
        return line.strip()[:100]
    return ""


def scan_pages(wiki_dir: Path) -> dict[str, list]:
    """Scan wiki/pages/ and group pages by type."""
    pages_dir = wiki_dir / "pages"
    groups: dict[str, list] = {"concept": [], "entity": [], "synthesis": [], "other": []}

    for md_file in sorted(pages_dir.rglob("*.md")):
        if md_file.name == "_index.md":
            continue
        try:
            text = md_file.read_text(encoding='utf-8')
        except Exception:
            continue

        fm = parse_frontmatter(text)
        page_type = fm.get("type", "other")
        title = fm.get("title") or md_file.stem
        description = get_first_paragraph(text)
        rel_path = md_file.relative_to(wiki_dir).as_posix()

        entry = {
            "title": title,
            "path": rel_path,
            "tags": fm.get("tags", ""),
            "updated": fm.get("updated", ""),
            "entity_type": fm.get("entity_type", ""),
            "description": description,
        }

        if page_type in groups:
            groups[page_type].append(entry)
        else:
            groups["other"].append(entry)

    return groups


def build_kb_summary(groups: dict) -> str:
    """Generate a concise summary of the knowledge base for router discovery."""
    all_tags: set[str] = set()
    all_titles: list[str] = []

    for items in groups.values():
        for page in items:
            all_titles.append(page["title"])
            if page.get("tags"):
                for t in str(page["tags"]).split(","):
                    t = t.strip().strip("[]'\" ")
                    if t:
                        all_tags.add(t)

    parts = []
    if all_tags:
        parts.append(f"**标签**: {', '.join(sorted(all_tags))}")
    if all_titles:
        preview = ", ".join(all_titles[:15])
        suffix = f" ... 等 {len(all_titles)} 个主题" if len(all_titles) > 15 else ""
        parts.append(f"**覆盖主题**: {preview}{suffix}")

    return "\n".join(parts) if parts else "(空知识库)"


def build_index(groups: dict, wiki_dir: Path, kb_id: str = "") -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = sum(len(v) for v in groups.values())

    # Collect all tags for frontmatter
    all_tags: set[str] = set()
    for items in groups.values():
        for page in items:
            if page.get("tags"):
                for t in str(page["tags"]).split(","):
                    t = t.strip().strip("[]'\" ")
                    if t:
                        all_tags.add(t)
    tags_str = ", ".join(sorted(all_tags)) if all_tags else ""

    # Machine-readable frontmatter (consumed by discover.py)
    fm_lines = ["---"]
    if kb_id:
        fm_lines.append(f"kb_id: {kb_id}")
    fm_lines.append(f"page_count: {total}")
    fm_lines.append(f"updated: {now}")
    if tags_str:
        fm_lines.append(f"tags: [{tags_str}]")
    fm_lines += ["---", ""]

    lines = fm_lines + [
        "# Prism Wiki — 知识目录",
        "",
        f"> 最后更新: {now} | 共 {total} 个页面",
        "",
        "## 📋 知识库概述",
        "",
        build_kb_summary(groups),
        "",
        "---",
        "",
    ]

    for type_key in ["concept", "entity", "synthesis", "other"]:
        items = groups.get(type_key, [])
        if not items:
            continue

        icon  = TYPE_ICONS.get(type_key, "📄")
        label = TYPE_LABELS.get(type_key, type_key.title())
        lines.append(f"## {icon} {label} ({len(items)})\n")

        for page in sorted(items, key=lambda p: p["title"].lower()):
            title = page["title"]
            path  = page["path"]
            desc  = page["description"]

            if type_key == "entity" and page.get("entity_type"):
                ei = ENTITY_TYPE_ICONS.get(page["entity_type"], "")
                title_display = f"{ei} {title}" if ei else title
            else:
                title_display = title

            if desc:
                lines.append(f"- [[{title_display}]]({path}) — {desc}")
            else:
                lines.append(f"- [[{title_display}]]({path})")

        lines.append("")

    lines.append("---")
    lines.append("*此文件由 `update_index.py` 自动生成，请勿手动编辑*")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description='Rebuild wiki/index.md')
    parser.add_argument('--wiki-dir', default=str(DEFAULT_WIKI_DIR))
    parser.add_argument('--kb-id', default="", help='Knowledge base ID to embed in frontmatter')
    args = parser.parse_args()

    wiki_dir  = Path(args.wiki_dir)
    pages_dir = wiki_dir / "pages"

    if not pages_dir.exists():
        print(f"❌ pages/ directory not found: {pages_dir}")
        return

    groups = scan_pages(wiki_dir)
    total  = sum(len(v) for v in groups.values())

    if total == 0:
        print("ℹ️ No pages found in wiki/pages/ — index not updated")
        return

    # Infer kb_id from directory name if not provided
    kb_id = args.kb_id or wiki_dir.parent.name

    content    = build_index(groups, wiki_dir, kb_id)
    index_path = wiki_dir / "index.md"
    index_path.write_text(content, encoding='utf-8')

    print(f"✅ Updated {index_path}")
    print(f"   {total} pages: "
          + ", ".join(f"{len(groups[k])} {k}s" for k in ["concept", "entity", "synthesis"] if groups[k]))
    if kb_id:
        print(f"   kb_id: {kb_id}")


if __name__ == "__main__":
    main()
