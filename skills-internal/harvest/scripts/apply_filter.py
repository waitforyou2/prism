#!/usr/bin/env python3
"""Merge AI annotations with raw search results."""

import argparse
import json
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Merge minimal AI annotations with raw search results.",
    )
    parser.add_argument("--raw", required=True, help="Raw search results JSON")
    parser.add_argument("--ann", required=True, help="AI annotations JSON")
    parser.add_argument("--out", required=True, help="Output annotated JSON")
    parser.add_argument(
        "--min-relevance",
        type=int,
        default=70,
        help="Minimum relevance score to keep",
    )
    parser.add_argument("--keyword", required=True, help="Keyword to inject")
    return parser.parse_args()


def load_json_file(file_path: str) -> object:
    """Load a JSON file and raise a readable error when loading fails."""
    try:
        return json.loads(Path(file_path).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError(f"Error reading {file_path}: {exc}") from exc


def build_annotation_maps(annotation_data: object) -> tuple[dict[int, dict], dict[str, dict]]:
    """Convert annotations into index-based and URL-based lookup maps."""
    index_annotations: dict[int, dict] = {}
    url_annotations: dict[str, dict] = {}

    if isinstance(annotation_data, dict):
        for annotation_key, annotation_value in annotation_data.items():
            if annotation_key.isdigit():
                index_annotations[int(annotation_key)] = annotation_value
            elif annotation_key.startswith("http"):
                url_annotations[annotation_key] = annotation_value
    elif isinstance(annotation_data, list):
        for result_index, annotation_value in enumerate(annotation_data):
            if annotation_value is not None:
                index_annotations[result_index] = annotation_value

    return index_annotations, url_annotations


def annotate_item(
    raw_item: dict,
    item_index: int,
    index_annotations: dict[int, dict],
    url_annotations: dict[str, dict],
    keyword: str,
) -> dict:
    """Merge a raw item with its matching annotation."""
    annotation = index_annotations.get(item_index)
    if not annotation:
        annotation = url_annotations.get(raw_item.get("url"))
    if not annotation:
        annotation = {}

    return {
        **raw_item,
        "isReal": annotation.get("isReal", True),
        "relevance": annotation.get("relevance", 0),
        "importance": annotation.get("importance", "low"),
        "summary": annotation.get("summary", ""),
        "keyword": keyword,
    }


def split_items(
    raw_items: list[dict],
    index_annotations: dict[int, dict],
    url_annotations: dict[str, dict],
    keyword: str,
    min_relevance: int,
) -> tuple[list[dict], list[tuple[int, str, int, bool]]]:
    """Split items into kept and discarded groups."""
    kept_items: list[dict] = []
    discarded_items: list[tuple[int, str, int, bool]] = []

    for result_index, raw_item in enumerate(raw_items):
        annotated_item = annotate_item(
            raw_item,
            result_index,
            index_annotations,
            url_annotations,
            keyword,
        )
        if annotated_item["isReal"] and annotated_item["relevance"] >= min_relevance:
            kept_items.append(annotated_item)
            continue
        discarded_items.append(
            (
                result_index,
                raw_item.get("title", "")[:50],
                annotated_item["relevance"],
                annotated_item["isReal"],
            )
        )

    return kept_items, discarded_items


def log_summary(
    raw_items: list[dict],
    kept_items: list[dict],
    discarded_items: list[tuple[int, str, int, bool]],
    min_relevance: int,
) -> None:
    """Log a summary of keep and discard decisions."""
    LOGGER.info(
        "Original: %s | Keep: %s | Discard: %s",
        len(raw_items),
        len(kept_items),
        len(discarded_items),
    )
    for result_index, title, relevance, is_real in discarded_items:
        reason = "not real" if not is_real else f"relevance {relevance} < {min_relevance}"
        LOGGER.info("  Discard [%s]: %s (%s)", result_index, title, reason)


def write_output(file_path: str, kept_items: list[dict]) -> None:
    """Persist kept items as formatted JSON."""
    Path(file_path).write_text(
        json.dumps(kept_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LOGGER.info("Saved to %s", file_path)


def main() -> int:
    """Run the annotation merge command."""
    configure_logging()
    args = parse_args()

    try:
        raw_items = load_json_file(args.raw)
        annotation_data = load_json_file(args.ann)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return 1

    if not isinstance(raw_items, list):
        LOGGER.error("Raw data must be a JSON array.")
        return 1

    index_annotations, url_annotations = build_annotation_maps(annotation_data)
    kept_items, discarded_items = split_items(
        raw_items,
        index_annotations,
        url_annotations,
        args.keyword,
        args.min_relevance,
    )
    log_summary(raw_items, kept_items, discarded_items, args.min_relevance)
    write_output(args.out, kept_items)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
