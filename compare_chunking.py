"""Compare two chunking strategies for the stretch feature.

Strategies:
1. Review-aware chunks from data/chunks.json.
2. Fixed-size character chunks generated from data/cleaned/*.txt.

WSL usage:
    source .venv/bin/activate
    python3 compare_chunking.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent
CURRENT_CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks.json"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

FIXED_CHUNK_SIZE = 500
FIXED_OVERLAP = 75

QUERIES = [
    {
        "query": "What positive traits do students mention about Roman Stelmach?",
        "expected_source": "Roman Stelmach",
    },
    {
        "query": "What complaints appear most often in reviews for Professor Subash Shankar?",
        "expected_source": "Subash Shankar",
    },
    {
        "query": "What course is Professor Tong Yi most frequently reviewed for?",
        "expected_source": "Tong Yi",
    },
]


@dataclass
class SearchResult:
    chunk_id: str
    source_name: str
    distance: float
    text: str


def load_review_aware_chunks() -> list[dict[str, object]]:
    return json.loads(CURRENT_CHUNKS_PATH.read_text(encoding="utf-8"))


def load_fixed_size_chunks() -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    for path in sorted(CLEANED_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        source_name = source_name_from_text(path.stem, text)
        for index, chunk_text in enumerate(fixed_size_split(text, FIXED_CHUNK_SIZE, FIXED_OVERLAP)):
            chunks.append(
                {
                    "chunk_id": f"{path.stem}-fixed-{index:04d}",
                    "source_name": source_name,
                    "text": chunk_text,
                }
            )
    return chunks


def source_name_from_text(default: str, text: str) -> str:
    match = re.search(r"\bProfessor:\s*([^.\n]+)", text)
    if match:
        return f"Rate My Professors - {match.group(1).strip()}"
    return default


def fixed_size_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if len(chunk) >= 30:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(embeddings)


def search(query: str, chunks: list[dict[str, object]], embeddings: np.ndarray, model: SentenceTransformer) -> SearchResult:
    query_embedding = embed_texts(model, [query])[0]
    similarities = embeddings @ query_embedding
    best_index = int(np.argmax(similarities))
    best = chunks[best_index]
    return SearchResult(
        chunk_id=str(best["chunk_id"]),
        source_name=str(best["source_name"]),
        distance=float(1 - similarities[best_index]),
        text=str(best["text"]),
    )


def abbreviated(text: str, max_len: int = 130) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def relevance(result: SearchResult, expected_source: str) -> str:
    return "Relevant" if expected_source.lower() in result.source_name.lower() else "Off-target"


def main() -> int:
    review_chunks = load_review_aware_chunks()
    fixed_chunks = load_fixed_size_chunks()
    model = SentenceTransformer(EMBEDDING_MODEL)

    print(f"Review-aware chunk count: {len(review_chunks)}")
    print(f"Fixed-size chunk count: {len(fixed_chunks)}")

    review_embeddings = embed_texts(model, [str(chunk["text"]) for chunk in review_chunks])
    fixed_embeddings = embed_texts(model, [str(chunk["text"]) for chunk in fixed_chunks])

    print("\n| Query | Strategy | Top source | Distance | Relevance | Top chunk excerpt |")
    print("|---|---|---|---:|---|---|")
    for item in QUERIES:
        review_result = search(item["query"], review_chunks, review_embeddings, model)
        fixed_result = search(item["query"], fixed_chunks, fixed_embeddings, model)
        for strategy, result in [
            ("Review-aware", review_result),
            ("Fixed-size 500 chars", fixed_result),
        ]:
            print(
                "| "
                + " | ".join(
                    [
                        item["query"],
                        strategy,
                        result.source_name,
                        f"{result.distance:.4f}",
                        relevance(result, item["expected_source"]),
                        abbreviated(result.text).replace("|", "/"),
                    ]
                )
                + " |"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
