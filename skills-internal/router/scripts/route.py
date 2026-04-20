#!/usr/bin/env python3
"""
route.py — Route a user question to the most relevant knowledge base(s).

v2.1: BM25Okapi scoring engine (inlined, zero pip dependency).
Expects Agent-expanded query strings with synonyms and English terms.

Tokenization strategy:
  - English: lowercase word splitting
  - Chinese: character bigrams (2-grams) for meaningful IDF discrimination
  - Mixed: both strategies applied, results merged

Usage:
  python route.py --query "claude code AI编程 agentic coding anthropic" --registry .prism/registry.json
  python route.py -q "codex openai code generation 代码生成" -r .prism/registry.json --out .prism/route_result.json
  python route.py -q "codex claude 对比 comparison" -r .prism/registry.json --verbose
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path


# ── Tokenizer ─────────────────────────────────────────────────────────────────

# CJK Unicode ranges (Chinese, Japanese, Korean)
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
ENGLISH_WORD_RE = re.compile(r'[a-z0-9]+(?:[-_][a-z0-9]+)*')


def tokenize(text: str) -> list[str]:
    """
    Hybrid tokenizer: English words + Chinese character bigrams.

    English: "Claude Code" → ["claude", "code"]
    Chinese: "代码生成" → ["代码", "码生", "生成"]
    Mixed:   "Claude代码" → ["claude", "代码"]

    Bigrams give dramatically better IDF discrimination than single chars.
    A single character like "代" is ubiquitous; "代码" is far more specific.
    """
    text_lower = text.lower()
    tokens: list[str] = []

    # Extract English tokens
    tokens.extend(ENGLISH_WORD_RE.findall(text_lower))

    # Extract Chinese characters, then build bigrams
    # Process each contiguous CJK run separately
    cjk_runs = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+', text_lower)
    for run in cjk_runs:
        if len(run) == 1:
            tokens.append(run)  # single char — no bigram possible
        else:
            for i in range(len(run) - 1):
                tokens.append(run[i:i+2])

    return tokens


# ── BM25Okapi (inlined — no external dependency) ─────────────────────────────

class BM25:
    """
    BM25Okapi implementation. ~30 lines, zero dependency.

    Parameters:
        k1 = 1.5  — term frequency saturation
        b  = 0.75 — document length normalization
    """

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.n_docs = len(corpus)
        self.doc_lens = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_lens) / self.n_docs if self.n_docs > 0 else 1.0

        # Build document frequency table
        self.df: dict[str, int] = {}
        for doc in corpus:
            seen: set[str] = set()
            for token in doc:
                if token not in seen:
                    self.df[token] = self.df.get(token, 0) + 1
                    seen.add(token)

    def _idf(self, term: str) -> float:
        """Robertson-Sparck Jones IDF with floor at 0."""
        df = self.df.get(term, 0)
        return max(0.0, math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1.0))

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        """Score a single document against the query."""
        doc = self.corpus[doc_idx]
        dl = self.doc_lens[doc_idx]

        # Build term frequency for this document
        tf: dict[str, int] = {}
        for token in doc:
            tf[token] = tf.get(token, 0) + 1

        score = 0.0
        for term in query_tokens:
            if term not in tf:
                continue
            freq = tf[term]
            idf = self._idf(term)
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            score += idf * numerator / denominator

        return score

    def rank(self, query_tokens: list[str]) -> list[tuple[int, float]]:
        """Rank all documents. Returns list of (doc_idx, score) sorted desc."""
        scores = [(i, self.score(query_tokens, i)) for i in range(self.n_docs)]
        scores.sort(key=lambda x: -x[1])
        return scores


# ── Fast-path: ID exact match ─────────────────────────────────────────────────

def check_id_match(query_lower: str, kbs: list[dict]) -> list[dict]:
    """
    Fast-path: if the expanded query contains a KB id as a substring,
    that's the strongest possible signal. Returns matched KBs.
    """
    matches = []
    for kb in kbs:
        kb_id = (kb.get("id") or "").lower()
        if kb_id and kb_id in query_lower:
            matches.append(kb)
    return matches


# ── Routing ───────────────────────────────────────────────────────────────────

# Minimum BM25 score to be considered a candidate
SCORE_THRESHOLD = 1.0


def route(query: str, registry: dict, verbose: bool = False) -> dict:
    """
    Route a query against all knowledge bases using BM25.

    The query is expected to be Agent-expanded (synonyms, English terms, etc).
    """
    kbs = registry.get("knowledgeBases", [])
    if not kbs:
        return {"question": query, "strategy": "no_match", "matches": []}

    query_lower = query.lower()

    # ── Fast-path: KB id exact match ──────────────────────────────────
    id_matches = check_id_match(query_lower, kbs)
    if id_matches:
        if verbose:
            for m in id_matches:
                print(f"  ⚡ Fast-path ID match: [{m['id']}]", file=sys.stderr)
        # If only one ID matched and it's strong, return immediately
        # If multiple matched (e.g. "codex vs claude"), fall through to BM25
        # to get proper scoring
        if len(id_matches) == 1:
            kb = id_matches[0]
            return {
                "question": query,
                "strategy": "single_kb",
                "matches": [{
                    "kb_id":      kb["id"],
                    "confidence": 1.0,
                    "score":      999.0,
                    "match_type": "id_exact",
                    "wiki_path":  kb.get("path", ""),
                    "abs_path":   kb.get("abs_path", ""),
                    "page_count": kb.get("page_count", 0),
                }],
            }
        # Multiple ID matches → fall through to BM25 for ranking

    # ── BM25 scoring ──────────────────────────────────────────────────

    # Build tokenized corpus from bm25_corpus field
    corpus_texts = [kb.get("bm25_corpus", kb.get("id", "")) for kb in kbs]
    tokenized_corpus = [tokenize(text) for text in corpus_texts]

    if verbose:
        for i, (kb, tokens) in enumerate(zip(kbs, tokenized_corpus)):
            print(f"  [{kb['id']}] corpus tokens ({len(tokens)}): {tokens[:20]}...", file=sys.stderr)

    # Tokenize the Agent-expanded query
    query_tokens = tokenize(query)
    if verbose:
        print(f"  Query tokens ({len(query_tokens)}): {query_tokens}", file=sys.stderr)

    # Score
    bm25 = BM25(tokenized_corpus)
    rankings = bm25.rank(query_tokens)

    if verbose:
        print(f"\n  BM25 Scores:", file=sys.stderr)
        for idx, score in rankings:
            icon = "✅" if score >= SCORE_THRESHOLD else "  "
            print(f"    {icon} [{kbs[idx]['id']}] score={score:.3f}", file=sys.stderr)

    # Filter by threshold
    candidates = []
    for idx, score in rankings:
        if score < SCORE_THRESHOLD:
            continue
        kb = kbs[idx]
        candidates.append({
            "kb_id":      kb["id"],
            "confidence": round(min(score / 10.0, 1.0), 3),  # normalize to 0-1 range
            "score":      round(score, 3),
            "match_type": "bm25",
            "wiki_path":  kb.get("path", ""),
            "abs_path":   kb.get("abs_path", ""),
            "page_count": kb.get("page_count", 0),
        })

    # Determine strategy
    if len(candidates) == 0:
        strategy = "no_match"
    elif len(candidates) == 1:
        strategy = "single_kb"
    else:
        strategy = "multi_kb"

    return {
        "question": query,
        "strategy": strategy,
        "matches":  candidates,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Route an Agent-expanded query to matching knowledge base(s) via BM25'
    )
    parser.add_argument(
        '--query', '-q',
        required=True,
        help='Agent-expanded query string (with synonyms, English terms, etc)'
    )
    parser.add_argument(
        '--registry', '-r',
        default='.prism/registry.json',
        help='Path to registry.json (default: .prism/registry.json)'
    )
    parser.add_argument(
        '--out', '-o',
        default=None,
        help='Output path for route_result.json. If omitted, prints to stdout.'
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
        result = {"question": args.query, "strategy": "no_match", "matches": []}
    else:
        if args.verbose:
            print(f"📚 Routing against {kb_count} knowledge bases...\n", file=sys.stderr)
        result = route(args.query, registry, verbose=args.verbose)

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding='utf-8')
        print(f"\n✅ Route result written to {out_path}", file=sys.stderr)
    else:
        print(output)

    # Summary to stderr
    strategy = result["strategy"]
    if strategy == "no_match":
        print("\n🔍 No matching knowledge base found.", file=sys.stderr)
    elif strategy == "single_kb":
        m = result["matches"][0]
        t = m.get("match_type", "")
        print(f"\n✅ Routed to: [{m['kb_id']}] (score={m['score']}, type={t})", file=sys.stderr)
    else:
        print(f"\n✅ Multi-KB route ({len(result['matches'])} databases):", file=sys.stderr)
        for m in result["matches"]:
            print(f"   - [{m['kb_id']}] score={m['score']} ({m.get('match_type', '')})", file=sys.stderr)


if __name__ == "__main__":
    main()
