#!/usr/bin/env python3
"""
apply_filter.py — Merge AI-generated minimal annotations with raw search results.

Usage:
  python apply_filter.py --raw search_results_raw.json --ann annotations.json --out annotated_results.json --keyword "harness engineering"
"""

import json
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Merge minimal AI annotations with raw search results.")
    parser.add_argument("--raw", required=True, help="Raw search results JSON")
    parser.add_argument("--ann", required=True, help="AI annotations JSON (dict indexing by array index or URL)")
    parser.add_argument("--out", required=True, help="Output annotated JSON")
    parser.add_argument("--min-relevance", type=int, default=70, help="Minimum relevance score to keep")
    parser.add_argument("--keyword", required=True, help="Keyword to inject")
    args = parser.parse_args()

    try:
        with open(args.raw, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"Error reading {args.raw}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.ann, 'r', encoding='utf-8') as f:
            ann_data = json.load(f)
    except Exception as e:
        print(f"Error reading {args.ann}: {e}", file=sys.stderr)
        sys.exit(1)

    # ann_data can be dict indexed by string representation of digit, or array, or URL
    ann_dict = {}
    url_to_ann = {}

    if isinstance(ann_data, dict):
        for k, v in ann_data.items():
            if k.isdigit():
                ann_dict[int(k)] = v
            elif k.startswith("http"):
                url_to_ann[k] = v
    elif isinstance(ann_data, list):
        for i, v in enumerate(ann_data):
            if v is not None:
                ann_dict[i] = v

    keep = []
    discard = []

    for i, item in enumerate(raw_data):
        ann = ann_dict.get(i)
        if not ann:
            ann = url_to_ann.get(item.get("url"))
        if not ann:
            ann = {}

        # default values if omitted
        is_real = ann.get("isReal", True)
        relevance = ann.get("relevance", 0)  # default low relevance to drop if not explicitly annotated
        importance = ann.get("importance", "low")
        summary = ann.get("summary", "")

        annotated = {
            **item,
            "isReal": is_real,
            "relevance": relevance,
            "importance": importance,
            "summary": summary,
            "keyword": args.keyword
        }

        if is_real and relevance >= args.min_relevance:
            keep.append(annotated)
        else:
            discard.append((i, item.get("title", "")[:50], relevance, is_real))

    print(f"Original: {len(raw_data)} | Keep: {len(keep)} | Discard: {len(discard)}", file=sys.stderr)
    for i, title, rel, is_real in discard:
        reason = "not real" if not is_real else f"relevance {rel} < {args.min_relevance}"
        print(f"  Discard [{i}]: {title} ({reason})", file=sys.stderr)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(keep, f, ensure_ascii=False, indent=2)

    print(f"Saved to {args.out}", file=sys.stderr)

if __name__ == "__main__":
    main()
