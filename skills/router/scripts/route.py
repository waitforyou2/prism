#!/usr/bin/env python3
"""
route.py — Route a user question to the most relevant knowledge base(s).

Reads a registry.json (produced by discover.py) and scores each knowledge base
against the user's question using a multi-level keyword matching algorithm.
No LLM API calls — zero additional cost.

Usage:
  python route.py --question "Claude Code 最新功能" --registry .prism/registry.json
  python route.py -q "Codex 和 Claude Code 对比" -r .prism/registry.json
  python route.py -q "今天天气" -r .prism/registry.json --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ── Scoring weights ───────────────────────────────────────────────────────────

WEIGHT_KB_ID    = 0.60   # Level 1: KB id found in question
WEIGHT_TAG      = 0.30   # Level 2: Any tag found in question
WEIGHT_TOPIC    = 0.40   # Level 3: Any topic found in question
WEIGHT_DESC_MAX = 0.25   # Level 4: Description word-overlap (scaled)
THRESHOLD       = 0.10   # Minimum score to be included as a candidate


# ── Utilities ─────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Lowercase and strip punctuation for matching."""
    return re.sub(r'[^\w\s]', ' ', text.lower())


def tokenize(text: str) -> set[str]:
    """Split normalized text into word tokens, filtering short words."""
    return {w for w in normalize(text).split() if len(w) > 1}


def word_overlap(a: str, b: str) -> float:
    """
    Jaccard-like overlap between two text strings.
    Returns a float in [0, 1].
    """
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ── Routing algorithm ─────────────────────────────────────────────────────────

def score_kb(question: str, kb: dict) -> tuple[float, list[str]]:
    """
    Score a single knowledge base against the user's question.

    Returns:
        score   — float in [0, 1+]
        reasons — list of human-readable match reasons
    """
    q = normalize(question)
    score = 0.0
    reasons: list[str] = []

    kb_id = (kb.get("id") or "").lower()
    tags  = [t.lower() for t in kb.get("tags", [])]
    # Topics may be multi-word; check as substrings
    topics      = [normalize(t) for t in kb.get("topics", [])]
    description = kb.get("description", "")

    # Level 1: KB id exact substring match (highest signal)
    if kb_id and kb_id in q:
        score += WEIGHT_KB_ID
        reasons.append(f"kb_id_match: '{kb_id}'")

    # Level 2: Tag match (any tag found as substring in question)
    for tag in tags:
        if tag in q:
            score += WEIGHT_TAG
            reasons.append(f"tag_match: '{tag}'")
            break   # count once

    # Level 3: Topic match (any topic phrase found as substring)
    for topic in topics:
        if topic in q:
            score += WEIGHT_TOPIC
            reasons.append(f"topic_match: '{topic}'")
            break   # count once

    # Level 4: Description fuzzy overlap (only if no strong signal yet)
    if score < THRESHOLD and description:
        overlap = word_overlap(question, description)
        if overlap > 0.15:
            contrib = overlap * WEIGHT_DESC_MAX
            score   += contrib
            reasons.append(f"desc_fuzzy: overlap={overlap:.2f}")

    return score, reasons


def route(question: str, registry: dict) -> dict:
    """
    Match a question against all knowledge bases in the registry.

    Returns a routing result dict with strategy and matches list.
    """
    candidates = []

    for kb in registry.get("knowledgeBases", []):
        score, reasons = score_kb(question, kb)
        if score >= THRESHOLD:
            candidates.append({
                "kb_id":        kb["id"],
                "confidence":   round(min(score, 1.0), 3),
                "match_reason": "; ".join(reasons),
                "wiki_path":    kb.get("path", ""),
                "abs_path":     kb.get("abs_path", ""),
                "page_count":   kb.get("page_count", 0),
            })

    # Sort by confidence descending
    candidates.sort(key=lambda m: -m["confidence"])

    if len(candidates) == 0:
        strategy = "no_match"
    elif len(candidates) == 1:
        strategy = "single_kb"
    else:
        strategy = "multi_kb"

    return {
        "question": question,
        "strategy": strategy,
        "matches":  candidates,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Route a question to the best matching knowledge base(s)'
    )
    parser.add_argument(
        '--question', '-q',
        required=True,
        help='The user question to route'
    )
    parser.add_argument(
        '--registry', '-r',
        default='.prism/registry.json',
        help='Path to registry.json (default: .prism/registry.json)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print scoring details to stderr'
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(
            f"❌ Registry not found: {registry_path}\n"
            f"   Run discover.py first to build the registry.",
            file=sys.stderr
        )
        sys.exit(1)

    try:
        registry = json.loads(registry_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ Failed to read registry: {e}", file=sys.stderr)
        sys.exit(1)

    kb_count = len(registry.get("knowledgeBases", []))
    if kb_count == 0:
        print(
            "⚠️  Registry is empty — no knowledge bases found.\n"
            "   Run harvest + prism to build knowledge bases first.",
            file=sys.stderr
        )
        result = {
            "question": args.question,
            "strategy": "no_match",
            "matches": [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.verbose:
        print(f"📚 Routing against {kb_count} knowledge bases...", file=sys.stderr)
        for kb in registry["knowledgeBases"]:
            score, reasons = score_kb(args.question, kb)
            icon = "✅" if score >= THRESHOLD else "  "
            print(f"  {icon} [{kb['id']}] score={score:.3f} → {'; '.join(reasons) or 'no match'}", file=sys.stderr)

    result = route(args.question, registry)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Human-readable summary to stderr
    strategy = result["strategy"]
    if strategy == "no_match":
        print(
            "\n🔍 No matching knowledge base found.\n"
            "   Suggest running `harvest` for this topic.",
            file=sys.stderr
        )
    elif strategy == "single_kb":
        m = result["matches"][0]
        print(f"\n✅ Routed to: [{m['kb_id']}] (confidence: {m['confidence']})", file=sys.stderr)
    else:
        print(f"\n✅ Multi-KB route ({len(result['matches'])} databases):", file=sys.stderr)
        for m in result["matches"]:
            print(f"   - [{m['kb_id']}] confidence={m['confidence']} | {m['match_reason']}", file=sys.stderr)


if __name__ == "__main__":
    main()
