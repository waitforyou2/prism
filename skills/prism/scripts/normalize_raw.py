#!/usr/bin/env python3
"""Normalize manually uploaded raw files into Prism raw metadata records."""

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_WIKI_DIR = Path.cwd() / "wiki"
SUPPORTED_DOCUMENTS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv"}
SKIP_DIRS = {"originals", "__pycache__"}
CONTENT_HASH_LEN = 8


def slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60].strip("-") or "untitled"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:CONTENT_HASH_LEN]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") or text.startswith("---\r\n")


def parse_frontmatter(text: str) -> dict:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    parsed = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        parsed[key.strip()] = value.strip().strip('"').strip("'")
    return parsed


def extract_title(path: Path, text: str) -> str:
    frontmatter = parse_frontmatter(text)
    if frontmatter.get("title"):
        return frontmatter["title"]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").strip() or path.stem


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def yaml_escape(value) -> str:
    if value is None:
        return '""'
    return '"' + str(value).replace('"', '\\"').replace("\n", " ") + '"'


def build_frontmatter(title: str, keyword: str, fetched_at: str, words: int) -> str:
    return "\n".join(
        [
            "---",
            f"title: {yaml_escape(title)}",
            'url: ""',
            "source: manual",
            f"keyword: {yaml_escape(keyword)}",
            "relevance: 0",
            "importance: medium",
            "isReal: true",
            f"fetchedAt: {fetched_at}",
            "fetchStatus: manual",
            f"wordCount: {words}",
            "compiled: false",
            "---",
            "",
        ]
    )


def ensure_markdown_frontmatter(text: str, title: str, keyword: str, fetched_at: str, words: int) -> str:
    if has_frontmatter(text):
        return text
    heading = "" if re.search(r"(?m)^#\s+", text) else f"# {title}\n\n"
    return build_frontmatter(title, keyword, fetched_at, words) + heading + text.lstrip()


def load_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"files": []}
    try:
        return json.loads(index_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"files": []}


def save_index(index_path: Path, index: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def existing_meta_paths(raw_dir: Path) -> set[Path]:
    paths = set()
    for meta_path in raw_dir.rglob("*.meta.json"):
        paths.add(meta_path.with_suffix("").with_suffix(".md").resolve())
    return paths


def should_skip(path: Path, raw_dir: Path) -> bool:
    if path.name == "_index.json" or path.name.endswith(".meta.json"):
        return True
    try:
        rel_parts = path.relative_to(raw_dir).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in rel_parts[:-1])


def iter_manual_files(raw_dir: Path) -> list[Path]:
    supported = {".md"} | SUPPORTED_DOCUMENTS
    return [
        path
        for path in sorted(raw_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in supported and not should_skip(path, raw_dir)
    ]


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def convert_document_to_markdown(source: Path) -> str:
    from markitdown import MarkItDown

    result = MarkItDown().convert(str(source))
    if hasattr(result, "text_content"):
        return result.text_content
    if hasattr(result, "markdown"):
        return result.markdown
    if isinstance(result, str):
        return result
    raise TypeError("MarkItDown result does not contain markdown text")


def meta_record(
    *,
    rel_path: str,
    title: str,
    keyword: str,
    fetched_at: str,
    words: int,
    original_path: str,
) -> dict:
    return {
        "path": rel_path,
        "keyword": keyword,
        "title": title,
        "url": "",
        "source": "manual",
        "relevance": 0,
        "importance": "medium",
        "isReal": True,
        "fetchedAt": fetched_at,
        "fetchStatus": "manual",
        "wordCount": words,
        "author": None,
        "publishedAt": None,
        "compiled": False,
        "originalPath": original_path,
    }


def register_markdown(path: Path, wiki_dir: Path, keyword: str, index: dict) -> dict:
    raw_dir = wiki_dir / "raw"
    original_rel = path.relative_to(wiki_dir).as_posix()
    text = read_text(path)
    title = extract_title(path, text)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    words = word_count(text)
    fingerprint = content_hash(text)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    target_dir = raw_dir / today / "manual"
    target_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{slug(title)}_{fingerprint}"
    target_md = unique_path(target_dir, base_name, ".md")
    target_meta = target_md.with_suffix(".meta.json")

    normalized_text = ensure_markdown_frontmatter(text, title, keyword, fetched_at, words)
    if path.resolve() == target_md.resolve():
        path.write_text(normalized_text, encoding="utf-8")
    else:
        target_md.write_text(normalized_text, encoding="utf-8")
        path.unlink()

    rel_path = target_md.relative_to(wiki_dir).as_posix()
    record = meta_record(
        rel_path=rel_path,
        title=title,
        keyword=keyword,
        fetched_at=fetched_at,
        words=words,
        original_path=original_rel,
    )
    target_meta.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    index["files"].append(record)
    return record


def register_document(path: Path, wiki_dir: Path, keyword: str, index: dict) -> dict:
    raw_dir = wiki_dir / "raw"
    markdown = convert_document_to_markdown(path).replace("\ufeff", "")
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = extract_title(path, markdown)
    words = word_count(markdown)
    fingerprint = content_hash(markdown or str(path))
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    target_dir = raw_dir / today / "manual"
    target_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{slug(title)}_{fingerprint}"
    target_md = unique_path(target_dir, base_name, ".md")
    target_meta = target_md.with_suffix(".meta.json")
    target_md.write_text(
        ensure_markdown_frontmatter(markdown, title, keyword, fetched_at, words),
        encoding="utf-8",
    )

    originals_dir = raw_dir / "originals"
    originals_dir.mkdir(parents=True, exist_ok=True)
    archived_original = unique_path(originals_dir, path.stem, path.suffix)
    shutil.move(str(path), str(archived_original))

    record = meta_record(
        rel_path=target_md.relative_to(wiki_dir).as_posix(),
        title=title,
        keyword=keyword,
        fetched_at=fetched_at,
        words=words,
        original_path=archived_original.relative_to(wiki_dir).as_posix(),
    )
    target_meta.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    index["files"].append(record)
    return record


def normalize_raw(wiki_dir: Path, keyword: str | None = None) -> dict:
    wiki_dir = Path(wiki_dir)
    raw_dir = wiki_dir / "raw"
    keyword = keyword or wiki_dir.parent.name
    summary = {"registered": 0, "skipped": 0, "errors": []}
    if not raw_dir.exists():
        return summary

    index_path = raw_dir / "_index.json"
    index = load_index(index_path)
    registered_paths = existing_meta_paths(raw_dir)

    for path in iter_manual_files(raw_dir):
        if path.resolve() in registered_paths:
            summary["skipped"] += 1
            continue
        try:
            if path.suffix.lower() == ".md":
                register_markdown(path, wiki_dir, keyword, index)
            else:
                register_document(path, wiki_dir, keyword, index)
            summary["registered"] += 1
        except Exception as exc:
            summary["errors"].append({"path": str(path), "error": str(exc)})

    if summary["registered"]:
        existing_paths = set()
        deduped = []
        for record in index.get("files", []):
            record_path = record.get("path")
            if not record_path or record_path in existing_paths:
                continue
            existing_paths.add(record_path)
            deduped.append(record)
        index["files"] = deduped
        save_index(index_path, index)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize manually uploaded files in wiki/raw/.")
    parser.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    parser.add_argument("--keyword", default=None)
    args = parser.parse_args()

    summary = normalize_raw(Path(args.wiki_dir), keyword=args.keyword)
    for error in summary["errors"]:
        print(f"warning: failed to normalize {error['path']}: {error['error']}", file=sys.stderr)
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
