#!/usr/bin/env python3
"""Discover Prism knowledge bases within a workspace."""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Discover Prism knowledge bases in a workspace and build registry.json",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=".",
        help="Root directory to scan for knowledge bases",
    )
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help="Output path for registry.json. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print discovery progress to stderr",
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


def parse_tags(raw_tags: str) -> list[str]:
    """Parse a tags string into a list."""
    if not raw_tags:
        return []
    cleaned_tags = raw_tags.strip().strip("[]")
    return [
        tag.strip().strip("'\"")
        for tag in cleaned_tags.split(",")
        if tag.strip()
    ]


def extract_index_meta(index_path: Path) -> tuple[dict, list[str]]:
    """Extract frontmatter and topic list from wiki/index.md."""
    if not index_path.exists():
        return {}, []
    try:
        text = index_path.read_text(encoding="utf-8-sig")
    except Exception:
        return {}, []
    frontmatter = parse_frontmatter(text)
    topics = extract_topics(text)
    return frontmatter, topics


def extract_topics(text: str) -> list[str]:
    """Extract topic names from index body text."""
    for line in text.splitlines():
        if "topics" not in line.lower() and "覆盖主题" not in line:
            continue
        clean_line = re.sub(r"\*\*[^*]+\*\*:\s*", "", line).strip()
        clean_line = re.sub(r"\s*\.\.\.\s*total\s*\d+\s*topics", "", clean_line)
        return [topic.strip() for topic in clean_line.split(",") if topic.strip()]
    return []


def extract_page_titles(wiki_dir: Path) -> list[str]:
    """Scan wiki/pages/ and extract page titles plus aliases."""
    pages_dir = wiki_dir / "pages"
    if not pages_dir.exists():
        return []
    page_titles: list[str] = []
    for markdown_file in sorted(pages_dir.rglob("*.md")):
        if markdown_file.name.startswith("_"):
            continue
        try:
            text = markdown_file.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        frontmatter = parse_frontmatter(text)
        page_titles.append(frontmatter.get("title") or markdown_file.stem)
        page_titles.extend(extract_aliases(frontmatter.get("aliases", "")))
    return page_titles


def extract_aliases(raw_aliases: str) -> list[str]:
    """Parse aliases from frontmatter."""
    aliases: list[str] = []
    if not raw_aliases:
        return aliases
    for alias in raw_aliases.strip("[]").split(","):
        clean_alias = alias.strip().strip("'\"")
        if clean_alias:
            aliases.append(clean_alias)
    return aliases


def build_bm25_corpus(
    kb_id: str,
    description: str,
    tags: list[str],
    topics: list[str],
    page_titles: list[str],
) -> str:
    """Build a weighted text blob for BM25 indexing."""
    corpus_parts: list[str] = []
    if kb_id:
        corpus_parts.extend([kb_id] * 3)
    if description:
        corpus_parts.append(description)
    for tag in tags:
        corpus_parts.extend([tag] * 2)
    corpus_parts.extend(topics)
    for page_title in page_titles:
        corpus_parts.extend([page_title] * 2)
    return " ".join(corpus_parts)


def discover(workspace: Path, verbose: bool = False) -> list[dict]:
    """Scan the workspace for knowledge bases."""
    knowledge_bases: list[dict] = []
    for wiki_path in sorted(workspace.rglob("wiki/WIKI.md")):
        knowledge_base = build_knowledge_base_record(workspace, wiki_path, verbose)
        if knowledge_base:
            knowledge_bases.append(knowledge_base)
    return knowledge_bases


def build_knowledge_base_record(
    workspace: Path,
    wiki_path: Path,
    verbose: bool,
) -> dict | None:
    """Build a single knowledge base record from wiki paths."""
    kb_dir = wiki_path.parent.parent
    if verbose:
        LOGGER.info("Found KB: %s", kb_dir)
    try:
        wiki_text = wiki_path.read_text(encoding="utf-8-sig")
    except Exception as exc:
        LOGGER.warning("Cannot read %s: %s", wiki_path, exc)
        return None
    wiki_frontmatter = parse_frontmatter(wiki_text)
    index_frontmatter, topics = extract_index_meta(wiki_path.parent / "index.md")
    page_titles = extract_page_titles(wiki_path.parent)
    record = merge_metadata(
        workspace,
        kb_dir,
        wiki_frontmatter,
        index_frontmatter,
        topics,
        page_titles,
    )
    if verbose:
        LOGGER.info("corpus: %s...", record["bm25_corpus"][:120])
    return record


def merge_metadata(
    workspace: Path,
    kb_dir: Path,
    wiki_frontmatter: dict,
    index_frontmatter: dict,
    topics: list[str],
    page_titles: list[str],
) -> dict:
    """Merge wiki and index metadata into one record."""
    kb_id = (
        wiki_frontmatter.get("kb_id")
        or index_frontmatter.get("kb_id")
        or kb_dir.name
    )
    description = wiki_frontmatter.get("description", "")
    tags = parse_tags(wiki_frontmatter.get("tags") or index_frontmatter.get("tags") or "")
    if not tags and kb_id:
        tags = [kb_id]
    try:
        page_count = int(index_frontmatter.get("page_count", 0))
    except (ValueError, TypeError):
        page_count = 0
    try:
        relative_path = str((kb_dir / "wiki").relative_to(workspace)).replace("\\", "/")
    except ValueError:
        relative_path = str(kb_dir / "wiki").replace("\\", "/")
    return {
        "id": kb_id,
        "path": relative_path,
        "abs_path": str(kb_dir / "wiki").replace("\\", "/"),
        "description": description,
        "tags": tags,
        "page_count": page_count,
        "topics": topics,
        "last_updated": index_frontmatter.get("updated") or wiki_frontmatter.get("created", ""),
        "bm25_corpus": build_bm25_corpus(kb_id, description, tags, topics, page_titles),
    }


def write_registry(
    knowledge_bases: list[dict],
    workspace: Path,
    output_path: str | None,
) -> None:
    """Write the registry to stdout or a file."""
    registry = {
        "discoveredAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspace": str(workspace).replace("\\", "/"),
        "knowledgeBases": knowledge_bases,
    }
    rendered_registry = json.dumps(registry, ensure_ascii=False, indent=2)
    if output_path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered_registry, encoding="utf-8")
        LOGGER.info("Registry written to %s", destination)
        LOGGER.info("Found %s knowledge base(s)", len(knowledge_bases))
        for knowledge_base in knowledge_bases:
            LOGGER.info(
                "- [%s] %s (%s pages)",
                knowledge_base["id"],
                knowledge_base["path"],
                knowledge_base["page_count"],
            )
        return
    sys.stdout.write(rendered_registry)
    sys.stdout.write("\n")


def main() -> int:
    """Run the discovery command."""
    configure_logging()
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        LOGGER.error("Workspace not found: %s", workspace)
        return 1
    if args.verbose:
        LOGGER.info("Scanning workspace: %s", workspace)
    knowledge_bases = discover(workspace, verbose=args.verbose)
    write_registry(knowledge_bases, workspace, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
