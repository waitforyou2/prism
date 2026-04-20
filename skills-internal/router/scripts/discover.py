#!/usr/bin/env python3
"""
discover.py — Scan a workspace directory and discover all Prism knowledge bases.

A knowledge base is any directory containing wiki/WIKI.md.
Extracts metadata from WIKI.md frontmatter and wiki/index.md frontmatter,
then writes a registry.json for use by the router skill.

v2.1: Now includes `bm25_corpus` field — a pre-built text blob for BM25 scoring.

Usage:
  python discover.py --workspace ~/knowledge
  python discover.py --workspace ~/knowledge --out .prism/registry.json
  python discover.py --workspace . --out .prism/registry.json --verbose
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a Markdown file. Returns {} if none."""
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


def parse_tags(raw: str) -> list[str]:
    """Parse a tags string like '[tag1, tag2]' or 'tag1, tag2' into a list."""
    if not raw:
        return []
    cleaned = raw.strip().strip('[]')
    return [t.strip().strip("'\"") for t in cleaned.split(',') if t.strip()]


def extract_index_meta(index_path: Path) -> tuple[dict, list[str]]:
    """
    Extract frontmatter and topic list from wiki/index.md.

    Returns:
        fm     — frontmatter dict (page_count, updated, tags, kb_id)
        topics — list of topic titles from the "覆盖主题" line
    """
    if not index_path.exists():
        return {}, []

    try:
        text = index_path.read_text(encoding='utf-8')
    except Exception:
        return {}, []

    fm = parse_frontmatter(text)

    # Extract "覆盖主题: Topic A, Topic B, ..." line from body
    topics: list[str] = []
    for line in text.splitlines():
        if '覆盖主题' in line or 'topics' in line.lower():
            # Strip markdown bold markers and prefix
            clean = re.sub(r'\*\*[^*]+\*\*:\s*', '', line).strip()
            # Remove trailing "... 等 N 个主题"
            clean = re.sub(r'\s*\.\.\.\s*等\s*\d+\s*个主题', '', clean)
            parts = [t.strip() for t in clean.split(',') if t.strip()]
            topics = parts
            break

    return fm, topics


def extract_page_titles(wiki_dir: Path) -> list[str]:
    """Scan wiki/pages/ and extract all page titles from frontmatter."""
    pages_dir = wiki_dir / "pages"
    if not pages_dir.exists():
        return []

    titles: list[str] = []
    for md_file in sorted(pages_dir.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding='utf-8')
        except Exception:
            continue
        fm = parse_frontmatter(text)
        title = fm.get("title") or md_file.stem
        titles.append(title)
        # Also grab aliases if present
        aliases_raw = fm.get("aliases", "")
        if aliases_raw:
            for a in aliases_raw.strip("[]").split(","):
                a = a.strip().strip("'\"")
                if a:
                    titles.append(a)
    return titles


def build_bm25_corpus(kb_id: str, description: str, tags: list[str],
                       topics: list[str], page_titles: list[str]) -> str:
    """
    Build a flat text blob for BM25 indexing.

    Combines all discoverable metadata into a single string.
    Higher-value signals (kb_id, page titles) are repeated for weight boosting.
    """
    parts: list[str] = []

    # kb_id repeated 3x for strong anchor signal
    if kb_id:
        parts.extend([kb_id] * 3)

    # Description (as-is)
    if description:
        parts.append(description)

    # Tags (each repeated 2x for moderate weight)
    for tag in tags:
        parts.extend([tag] * 2)

    # Topics from index.md
    parts.extend(topics)

    # Page titles — the highest-quality knowledge indicators (repeated 2x)
    for title in page_titles:
        parts.extend([title] * 2)

    return " ".join(parts)


# ── Core ──────────────────────────────────────────────────────────────────────

def discover(workspace: Path, verbose: bool = False) -> list[dict]:
    """
    Scan workspace for knowledge bases (directories containing wiki/WIKI.md).

    Returns a list of KB metadata dicts, each including a bm25_corpus field.
    """
    kbs: list[dict] = []

    for wiki_md_path in sorted(workspace.rglob("wiki/WIKI.md")):
        kb_dir = wiki_md_path.parent.parent   # e.g. ~/knowledge/claude
        kb_id_fallback = kb_dir.name          # "claude"

        if verbose:
            print(f"  Found KB: {kb_dir}", file=sys.stderr)

        # 1. Read WIKI.md frontmatter
        try:
            wiki_text = wiki_md_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  ⚠️  Cannot read {wiki_md_path}: {e}", file=sys.stderr)
            continue

        wiki_fm = parse_frontmatter(wiki_text)

        # 2. Read index.md
        index_path = wiki_md_path.parent / "index.md"
        index_fm, topics = extract_index_meta(index_path)

        # 3. Extract all page titles for BM25 corpus
        page_titles = extract_page_titles(wiki_md_path.parent)

        # 4. Merge metadata
        kb_id       = wiki_fm.get("kb_id") or index_fm.get("kb_id") or kb_id_fallback
        description = wiki_fm.get("description", "")
        tags_raw    = wiki_fm.get("tags") or index_fm.get("tags") or ""
        tags        = parse_tags(tags_raw)

        if not tags and kb_id:
            tags = [kb_id]

        try:
            page_count = int(index_fm.get("page_count", 0))
        except (ValueError, TypeError):
            page_count = 0

        last_updated = index_fm.get("updated") or wiki_fm.get("created", "")

        try:
            rel_path = str(wiki_md_path.parent.relative_to(workspace)).replace("\\", "/")
        except ValueError:
            rel_path = str(wiki_md_path.parent).replace("\\", "/")

        # 5. Build BM25 corpus
        corpus = build_bm25_corpus(kb_id, description, tags, topics, page_titles)

        kbs.append({
            "id":           kb_id,
            "path":         rel_path,
            "abs_path":     str(wiki_md_path.parent).replace("\\", "/"),
            "description":  description,
            "tags":         tags,
            "page_count":   page_count,
            "topics":       topics,
            "last_updated": last_updated,
            "bm25_corpus":  corpus,
        })

        if verbose:
            print(f"    corpus: {corpus[:120]}...", file=sys.stderr)

    return kbs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Discover Prism knowledge bases in a workspace and build registry.json'
    )
    parser.add_argument(
        '--workspace', '-w',
        default='.',
        help='Root directory to scan for knowledge bases (default: current directory)'
    )
    parser.add_argument(
        '--out', '-o',
        default=None,
        help='Output path for registry.json. If omitted, prints to stdout.'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print discovery progress to stderr'
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    if not workspace.exists():
        print(f"❌ Workspace not found: {workspace}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"🔍 Scanning workspace: {workspace}", file=sys.stderr)

    kbs = discover(workspace, verbose=args.verbose)

    registry = {
        "discoveredAt":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspace":      str(workspace).replace("\\", "/"),
        "knowledgeBases": kbs,
    }

    output = json.dumps(registry, ensure_ascii=False, indent=2)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding='utf-8')
        print(f"✅ Registry written to {out_path}", file=sys.stderr)
        print(f"   Found {len(kbs)} knowledge base(s):", file=sys.stderr)
        for kb in kbs:
            print(f"   - [{kb['id']}] {kb['path']} ({kb['page_count']} pages)", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
