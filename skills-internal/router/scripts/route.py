#!/usr/bin/env python3
"""Route a user question to the most relevant knowledge base(s)."""

import argparse
import json
import logging
import math
import re
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)

ENGLISH_WORD_RE = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*")
SCORE_THRESHOLD = 1.0


def configure_logging() -> None:
    """Configure stderr logging for command-line execution."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Route an expanded query to matching knowledge base(s) via BM25",
    )
    parser.add_argument("--query", "-q", required=True, help="Expanded query string")
    parser.add_argument(
        "--registry",
        "-r",
        default=".prism/registry.json",
        help="Path to registry.json",
    )
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help="Output path for route_result.json",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print scoring details to stderr",
    )
    return parser.parse_args()


def tokenize(text: str) -> list[str]:
    """Tokenize text into English words and Chinese bigrams."""
    lowered_text = text.lower()
    tokens = ENGLISH_WORD_RE.findall(lowered_text)
    cjk_runs = re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+", lowered_text)
    for run in cjk_runs:
        tokens.extend(build_cjk_tokens(run))
    return tokens


def build_cjk_tokens(run: str) -> list[str]:
    """Build CJK bigram tokens from a contiguous CJK run."""
    if len(run) == 1:
        return [run]
    return [run[index:index + 2] for index in range(len(run) - 1)]


class BM25:
    """Minimal BM25Okapi implementation."""

    def __init__(
        self,
        corpus: list[list[str]],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.n_docs = len(corpus)
        self.doc_lens = [len(document) for document in corpus]
        self.avgdl = sum(self.doc_lens) / self.n_docs if self.n_docs > 0 else 1.0
        self.df: dict[str, int] = {}
        for document in corpus:
            seen_terms: set[str] = set()
            for token in document:
                if token not in seen_terms:
                    self.df[token] = self.df.get(token, 0) + 1
                    seen_terms.add(token)

    def _idf(self, term: str) -> float:
        document_frequency = self.df.get(term, 0)
        return max(
            0.0,
            math.log((self.n_docs - document_frequency + 0.5) / (document_frequency + 0.5) + 1.0),
        )

    def score(self, query_tokens: list[str], document_index: int) -> float:
        """Score a single document against the query."""
        document = self.corpus[document_index]
        document_length = self.doc_lens[document_index]
        term_frequencies: dict[str, int] = {}
        for token in document:
            term_frequencies[token] = term_frequencies.get(token, 0) + 1
        score = 0.0
        for term in query_tokens:
            if term not in term_frequencies:
                continue
            frequency = term_frequencies[term]
            idf = self._idf(term)
            numerator = frequency * (self.k1 + 1)
            denominator = frequency + self.k1 * (
                1 - self.b + self.b * document_length / self.avgdl
            )
            score += idf * numerator / denominator
        return score

    def rank(self, query_tokens: list[str]) -> list[tuple[int, float]]:
        """Rank all documents for the query."""
        scored_documents = [
            (index, self.score(query_tokens, index))
            for index in range(self.n_docs)
        ]
        scored_documents.sort(key=lambda entry: -entry[1])
        return scored_documents


def check_id_match(query_lower: str, knowledge_bases: list[dict]) -> list[dict]:
    """Return knowledge bases whose id appears in the query."""
    matches: list[dict] = []
    for knowledge_base in knowledge_bases:
        kb_id = (knowledge_base.get("id") or "").lower()
        if kb_id and kb_id in query_lower:
            matches.append(knowledge_base)
    return matches


def route(query: str, registry: dict, verbose: bool = False) -> dict:
    """Route a query against all knowledge bases using BM25."""
    knowledge_bases = registry.get("knowledgeBases", [])
    if not knowledge_bases:
        return {"question": query, "strategy": "no_match", "matches": []}
    id_matches = check_id_match(query.lower(), knowledge_bases)
    if id_matches:
        return handle_id_matches(query, id_matches, verbose)
    return score_query(query, knowledge_bases, verbose)


def handle_id_matches(query: str, id_matches: list[dict], verbose: bool) -> dict:
    """Handle fast-path matches for direct knowledge-base id references."""
    if verbose:
        for match in id_matches:
            LOGGER.info("Fast-path ID match: [%s]", match["id"])
    if len(id_matches) == 1:
        knowledge_base = id_matches[0]
        return {
            "question": query,
            "strategy": "single_kb",
            "matches": [
                {
                    "kb_id": knowledge_base["id"],
                    "confidence": 1.0,
                    "score": 999.0,
                    "match_type": "id_exact",
                    "wiki_path": knowledge_base.get("path", ""),
                    "abs_path": knowledge_base.get("abs_path", ""),
                    "page_count": knowledge_base.get("page_count", 0),
                }
            ],
        }
    return score_query(query, id_matches, verbose)


def score_query(query: str, knowledge_bases: list[dict], verbose: bool) -> dict:
    """Score a query against knowledge bases and determine routing strategy."""
    corpus_texts = [
        knowledge_base.get("bm25_corpus", knowledge_base.get("id", ""))
        for knowledge_base in knowledge_bases
    ]
    tokenized_corpus = [tokenize(text) for text in corpus_texts]
    query_tokens = tokenize(query)
    if verbose:
        log_scoring_inputs(knowledge_bases, tokenized_corpus, query_tokens)
    bm25 = BM25(tokenized_corpus)
    rankings = bm25.rank(query_tokens)
    if verbose:
        log_rankings(rankings, knowledge_bases)
    matches = build_candidates(rankings, knowledge_bases)
    return {
        "question": query,
        "strategy": determine_strategy(matches),
        "matches": matches,
    }


def log_scoring_inputs(
    knowledge_bases: list[dict],
    tokenized_corpus: list[list[str]],
    query_tokens: list[str],
) -> None:
    """Log tokenization inputs for verbose mode."""
    for knowledge_base, tokens in zip(knowledge_bases, tokenized_corpus):
        LOGGER.info(
            "[%s] corpus tokens (%s): %s...",
            knowledge_base["id"],
            len(tokens),
            tokens[:20],
        )
    LOGGER.info("Query tokens (%s): %s", len(query_tokens), query_tokens)


def log_rankings(rankings: list[tuple[int, float]], knowledge_bases: list[dict]) -> None:
    """Log BM25 rankings for verbose mode."""
    LOGGER.info("BM25 scores:")
    for knowledge_base_index, score in rankings:
        icon = "*" if score >= SCORE_THRESHOLD else "-"
        LOGGER.info(
            "  %s [%s] score=%.3f",
            icon,
            knowledge_bases[knowledge_base_index]["id"],
            score,
        )


def build_candidates(
    rankings: list[tuple[int, float]],
    knowledge_bases: list[dict],
) -> list[dict]:
    """Build route candidates above the score threshold."""
    candidates: list[dict] = []
    for knowledge_base_index, score in rankings:
        if score < SCORE_THRESHOLD:
            continue
        knowledge_base = knowledge_bases[knowledge_base_index]
        candidates.append(
            {
                "kb_id": knowledge_base["id"],
                "confidence": round(min(score / 10.0, 1.0), 3),
                "score": round(score, 3),
                "match_type": "bm25",
                "wiki_path": knowledge_base.get("path", ""),
                "abs_path": knowledge_base.get("abs_path", ""),
                "page_count": knowledge_base.get("page_count", 0),
            }
        )
    return candidates


def determine_strategy(matches: list[dict]) -> str:
    """Determine the route strategy from the candidate list."""
    if not matches:
        return "no_match"
    if len(matches) == 1:
        return "single_kb"
    return "multi_kb"


def load_registry(registry_path: Path) -> dict:
    """Load the router registry from disk."""
    return json.loads(registry_path.read_text(encoding="utf-8-sig"))


def write_result(result: dict, output_path: str | None) -> None:
    """Write the route result to stdout or a file."""
    rendered_result = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered_result, encoding="utf-8")
        LOGGER.info("Route result written to %s", destination)
        return
    sys.stdout.write(rendered_result)
    sys.stdout.write("\n")


def log_summary(result: dict) -> None:
    """Log a summary of the routing outcome."""
    strategy = result["strategy"]
    if strategy == "no_match":
        LOGGER.info("No matching knowledge base found.")
        return
    if strategy == "single_kb":
        match = result["matches"][0]
        LOGGER.info(
            "Routed to [%s] (score=%s, type=%s)",
            match["kb_id"],
            match["score"],
            match.get("match_type", ""),
        )
        return
    LOGGER.info("Multi-KB route (%s databases):", len(result["matches"]))
    for match in result["matches"]:
        LOGGER.info(
            "- [%s] score=%s (%s)",
            match["kb_id"],
            match["score"],
            match.get("match_type", ""),
        )


def main() -> int:
    """Run the router command."""
    configure_logging()
    args = parse_args()
    registry_path = Path(args.registry)
    if not registry_path.exists():
        LOGGER.error("Registry not found: %s", registry_path)
        LOGGER.error("Run discover.py first to build the registry.")
        return 1
    try:
        registry = load_registry(registry_path)
    except Exception as exc:
        LOGGER.error("Failed to read registry: %s", exc)
        return 1
    if args.verbose:
        LOGGER.info(
            "Routing against %s knowledge bases...",
            len(registry.get("knowledgeBases", [])),
        )
    result = route(args.query, registry, verbose=args.verbose)
    write_result(result, args.out)
    log_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
