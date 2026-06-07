"""Milestone 4 embedding and retrieval pipeline.

WSL usage:
    source .venv/bin/activate
    python3 retrieval_pipeline.py --rebuild --test
    python3 retrieval_pipeline.py --query "What complaints appear most often in reviews for Professor Subash Shankar?"
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent
CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks.json"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "hunter_professor_reviews"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 5

EVALUATION_QUERIES = [
    "What positive traits do students mention about Roman Stelmach?",
    "What complaints appear most often in reviews for Professor Subash Shankar?",
    "What course is Professor Tong Yi most frequently reviewed for?",
]


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    source_name: str
    source_location: str
    chunk_index: int
    distance: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed chunks in ChromaDB and test retrieval.")
    parser.add_argument("--chunks-path", type=Path, default=CHUNKS_PATH)
    parser.add_argument("--chroma-dir", type=Path, default=CHROMA_DIR)
    parser.add_argument("--collection", default=COLLECTION_NAME)
    parser.add_argument("--model", default=EMBEDDING_MODEL)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--rebuild", action="store_true", help="Delete and rebuild the Chroma collection.")
    parser.add_argument("--test", action="store_true", help="Run the first 3 evaluation queries from planning.md.")
    parser.add_argument("--query", help="Run one retrieval query.")
    return parser.parse_args()


def load_chunks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing chunks file: {path}. Run document_pipeline.py first.")

    chunks = json.loads(path.read_text(encoding="utf-8"))
    cleaned_chunks: list[dict[str, Any]] = []
    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        cleaned_chunks.append(chunk)
    if not cleaned_chunks:
        raise ValueError(f"No non-empty chunks found in {path}.")
    return cleaned_chunks


def load_model(model_name: str) -> SentenceTransformer:
    print(f"Loading embedding model: {model_name}")
    return SentenceTransformer(model_name)


def get_chroma_collection(chroma_dir: Path, collection_name: str, rebuild: bool) -> Any:
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))

    if rebuild:
        try:
            client.delete_collection(collection_name)
            print(f"Deleted existing Chroma collection: {collection_name}")
        except Exception as exc:
            message = str(exc).lower()
            if "does not exist" not in message and "not found" not in message:
                raise
            print(f"No existing Chroma collection to delete: {collection_name}")

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def embed_and_store(chunks: list[dict[str, Any]], model: SentenceTransformer, collection: Any) -> None:
    if collection_matches_chunks(collection, chunks):
        print(f"Chroma collection already has {collection.count()} current chunks; skipping embedding.")
        return

    print(f"Embedding {len(chunks)} chunks...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    ids = [str(chunk["chunk_id"]) for chunk in chunks]
    metadatas = [chunk_metadata(chunk) for chunk in chunks]

    batch_size = 64
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=texts[start:end],
            embeddings=embeddings[start:end].tolist(),
            metadatas=metadatas[start:end],
        )
    print(f"Stored {collection.count()} chunks in Chroma collection: {collection.name}")


def chunk_metadata(chunk: dict[str, Any]) -> dict[str, str | int]:
    return {
        "source_id": str(chunk.get("source_id", "")),
        "source_name": str(chunk.get("source_name", "")),
        "source_location": str(chunk.get("source_location", "")),
        "chunk_index": int(chunk.get("chunk_index", 0)),
        "text_hash": text_hash(str(chunk.get("text", ""))),
    }


def collection_matches_chunks(collection: Any, chunks: list[dict[str, Any]]) -> bool:
    if collection.count() != len(chunks):
        return False

    expected_hashes = {str(chunk["chunk_id"]): text_hash(str(chunk.get("text", ""))) for chunk in chunks}
    existing = collection.get(ids=list(expected_hashes.keys()), include=["metadatas"])
    existing_ids = existing.get("ids", [])
    existing_metadatas = existing.get("metadatas", [])
    if len(existing_ids) != len(expected_hashes):
        return False

    for chunk_id, metadata in zip(existing_ids, existing_metadatas):
        if not metadata or metadata.get("text_hash") != expected_hashes.get(chunk_id):
            return False
    return True


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def retrieve(query: str, model: SentenceTransformer, collection: Any, top_k: int) -> list[RetrievedChunk]:
    query_embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: list[RetrievedChunk] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        metadata = metadata or {}
        retrieved.append(
            RetrievedChunk(
                chunk_id=str(chunk_id),
                text=str(document),
                source_name=str(metadata.get("source_name", "")),
                source_location=str(metadata.get("source_location", "")),
                chunk_index=int(metadata.get("chunk_index", 0)),
                distance=float(distance),
            )
        )
    return retrieved


def print_results(query: str, results: list[RetrievedChunk]) -> None:
    print("\n" + "=" * 88)
    print(f"Query: {query}")
    for rank, result in enumerate(results, start=1):
        print("\n" + "-" * 88)
        print(
            f"{rank}. {result.chunk_id} | distance={result.distance:.4f} | "
            f"{result.source_name} | chunk {result.chunk_index}"
        )
        print(f"Source: {result.source_location}")
        print(result.text)


def run_queries(queries: list[str], model: SentenceTransformer, collection: Any, top_k: int) -> None:
    for query in queries:
        results = retrieve(query, model, collection, top_k)
        print_results(query, results)


def main() -> int:
    args = parse_args()
    chunks = load_chunks(args.chunks_path)
    model = load_model(args.model)
    collection = get_chroma_collection(args.chroma_dir, args.collection, args.rebuild)
    embed_and_store(chunks, model, collection)

    if args.query:
        run_queries([args.query], model, collection, args.top_k)
    if args.test or not args.query:
        run_queries(EVALUATION_QUERIES, model, collection, args.top_k)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
