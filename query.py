"""End-to-end grounded question answering for Milestone 5.

WSL usage:
    source .venv/bin/activate
    python3 query.py "What positive traits do students mention about Roman Stelmach?"
"""

from __future__ import annotations

import argparse
import os
import re
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from retrieval_pipeline import (
    CHROMA_DIR,
    CHUNKS_PATH,
    COLLECTION_NAME,
    DEFAULT_TOP_K,
    EMBEDDING_MODEL,
    RetrievedChunk,
    embed_and_store,
    get_chroma_collection,
    load_chunks,
    load_model,
    retrieve,
)


GROQ_MODEL = "llama-3.3-70b-versatile"
INSUFFICIENT_INFORMATION = "I don't have enough information on that."
MAX_ACCEPTABLE_DISTANCE = 0.55

SYSTEM_PROMPT = f"""You are a grounded question-answering assistant for a Hunter College unofficial guide.
Answer using only the provided retrieved documents.
Do not use outside knowledge, assumptions, or guesses.
For ranking or recommendation questions, answer only by comparing the retrieved review data and clearly explain the evidence used.
If the retrieved documents do not contain enough information to answer, respond exactly:
{INSUFFICIENT_INFORMATION}
When you answer, cite the source markers that support each claim, such as [S1] or [S2].
Keep the answer concise and directly tied to the retrieved evidence."""


@lru_cache(maxsize=1)
def get_retrieval_resources() -> tuple[Any, Any]:
    chunks = load_chunks(CHUNKS_PATH)
    model = load_model(EMBEDDING_MODEL)
    collection = get_chroma_collection(CHROMA_DIR, COLLECTION_NAME, rebuild=False)
    embed_and_store(chunks, model, collection)
    return model, collection


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Add it to .env before running Milestone 5.")
    return Groq(api_key=api_key)


def ask(question: str, top_k: int = DEFAULT_TOP_K) -> dict[str, Any]:
    question = question.strip()
    if not question:
        return {"answer": "Please enter a question.", "sources": [], "chunks": []}

    summary_result = answer_summary_question(question)
    if summary_result:
        return summary_result

    model, collection = get_retrieval_resources()
    chunks = retrieve(question, model, collection, top_k)

    if not chunks or chunks[0].distance > MAX_ACCEPTABLE_DISTANCE:
        return {
            "answer": INSUFFICIENT_INFORMATION,
            "sources": [],
            "chunks": chunks_to_dicts(chunks),
        }

    answer = generate_answer(question, chunks)
    return {
        "answer": answer,
        "sources": format_sources(chunks),
        "chunks": chunks_to_dicts(chunks),
    }


def answer_summary_question(question: str) -> dict[str, Any] | None:
    intent = summary_question_intent(question)
    if not intent:
        return None

    chunks = load_chunks(CHUNKS_PATH)
    summaries = [parse_professor_summary(chunk) for chunk in chunks]
    summaries = [summary for summary in summaries if summary]
    department_filter = requested_department(question)
    if department_filter:
        summaries = [summary for summary in summaries if summary["department"].lower() == department_filter.lower()]

    if not summaries:
        return {
            "answer": INSUFFICIENT_INFORMATION,
            "sources": [],
            "chunks": [],
        }

    selected = select_summary(summaries, intent)
    supporting_chunks = support_chunks_for_summary_query(chunks, selected["professor"], intent)
    sources = format_chunk_sources(supporting_chunks)
    chunks_for_output = [
        {
            "chunk_id": chunk["chunk_id"],
            "source_name": chunk["source_name"],
            "source_location": chunk["source_location"],
            "chunk_index": chunk["chunk_index"],
            "distance": 0.0,
            "text": chunk["text"],
        }
        for chunk in supporting_chunks
    ]

    answer = format_summary_answer(selected, intent)
    return {"answer": answer, "sources": sources, "chunks": chunks_for_output}


def summary_question_intent(question: str) -> str | None:
    normalized = question.lower()
    asks_about_professor = re.search(r"\b(professor|teacher|instructor)\b", normalized)
    if not asks_about_professor:
        return None
    if re.search(r"\b(most difficult|hardest|highest difficulty)\b", normalized):
        return "most_difficult"
    if re.search(r"\b(easiest|least difficult|lowest difficulty)\b", normalized):
        return "easiest"
    if re.search(r"\b(highest rated|best rating|top rated|best|top|recommend|recommended)\b", normalized):
        return "best"
    if re.search(r"\b(lowest rated|worst rating|worst)\b", normalized):
        return "worst"
    if re.search(r"\b(most reviewed|most ratings|largest number of ratings|popular)\b", normalized):
        return "most_reviewed"
    if re.search(r"\b(would take again|take again)\b", normalized):
        return "would_take_again"
    return None


def requested_department(question: str) -> str | None:
    normalized = question.lower()
    if "computer science" in normalized or re.search(r"\bcs\b", normalized):
        return "Computer Science"
    if "math" in normalized or "mathematics" in normalized:
        return "Mathematics"
    return None


def parse_professor_summary(chunk: dict[str, Any]) -> dict[str, Any] | None:
    text = str(chunk.get("text", ""))
    if "Department:" not in text or "Average rating:" not in text:
        return None

    professor = extract_field(text, r"Professor:\s*([^.]*)")
    department = extract_field(text, r"Department:\s*([^.]*)")
    avg_rating = extract_number(text, r"Average rating:\s*([0-9.]+)")
    num_ratings = extract_number(text, r"Number of ratings:\s*([0-9.]+)")
    avg_difficulty = extract_number(text, r"Average difficulty:\s*([0-9.]+)")
    would_take_again = extract_number(text, r"Would take again:\s*([0-9.]+)")
    if not professor or not department or avg_rating is None:
        return None

    return {
        "professor": professor,
        "department": department,
        "avg_rating": avg_rating,
        "num_ratings": int(num_ratings or 0),
        "avg_difficulty": avg_difficulty or 0.0,
        "would_take_again": would_take_again or 0.0,
        "chunk": chunk,
    }


def select_summary(summaries: list[dict[str, Any]], intent: str) -> dict[str, Any]:
    if intent == "most_difficult":
        return max(summaries, key=lambda item: (item["avg_difficulty"], item["num_ratings"]))
    if intent == "easiest":
        return min(summaries, key=lambda item: (item["avg_difficulty"], -item["num_ratings"]))
    if intent == "worst":
        return min(summaries, key=lambda item: (item["avg_rating"], -item["num_ratings"]))
    if intent == "most_reviewed":
        return max(summaries, key=lambda item: (item["num_ratings"], item["avg_rating"]))
    if intent == "would_take_again":
        return max(summaries, key=lambda item: (item["would_take_again"], item["num_ratings"]))
    return max(summaries, key=lambda item: (item["avg_rating"], item["would_take_again"], item["num_ratings"]))


def support_chunks_for_summary_query(chunks: list[dict[str, Any]], professor: str, intent: str) -> list[dict[str, Any]]:
    professor_chunks = [chunk for chunk in chunks if f"Professor: {professor}." in str(chunk.get("text", ""))]
    summary_chunks = [chunk for chunk in professor_chunks if "Average rating:" in str(chunk.get("text", ""))]
    if intent in {"most_difficult", "easiest", "worst", "most_reviewed", "would_take_again"}:
        return summary_chunks[:5]

    positive_reviews = [
        chunk
        for chunk in professor_chunks
        if re.search(r"Quality:\s*5\b", str(chunk.get("text", "")))
        or re.search(r"\b(Amazing lectures|Caring|Accessible outside class|Clear grading criteria|Respected)\b", str(chunk.get("text", "")))
    ]
    return (summary_chunks + positive_reviews)[:5]


def format_summary_answer(summary: dict[str, Any], intent: str) -> str:
    professor = summary["professor"]
    department = summary["department"]
    base = (
        f"{professor} is the matching {department} professor based on the summary data in this corpus. "
        f"The summary lists an average rating of {summary['avg_rating']:g}/5, "
        f"an average difficulty of {summary['avg_difficulty']:g}/5, "
        f"{summary['num_ratings']} total ratings, and "
        f"{summary['would_take_again']:g}% would take again."
    )
    if intent == "most_difficult":
        return f"{professor} appears to be the most difficult {department} professor in the corpus. {base}"
    if intent == "easiest":
        return f"{professor} appears to be the least difficult {department} professor in the corpus. {base}"
    if intent == "worst":
        return f"{professor} appears to be the lowest-rated {department} professor in the corpus. {base}"
    if intent == "most_reviewed":
        return f"{professor} has the most ratings among the matching {department} professors in the corpus. {base}"
    if intent == "would_take_again":
        return f"{professor} has the highest would-take-again percentage among the matching {department} professors in the corpus. {base}"
    return f"{professor} appears to be the highest-rated {department} professor in the corpus. {base}"


def format_chunk_sources(chunks: list[dict[str, Any]]) -> list[str]:
    seen: set[tuple[str, str]] = set()
    sources: list[str] = []
    for chunk in chunks:
        key = (str(chunk.get("source_name", "")), str(chunk.get("source_location", "")))
        if key in seen:
            continue
        seen.add(key)
        sources.append(f"{key[0]} ({key[1]})")
    return sources


def extract_field(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def extract_number(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    context = format_context(chunks)
    user_prompt = f"""Question:
{question}

Retrieved documents:
{context}

Answer the question using only the retrieved documents above."""

    response = get_groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=450,
    )
    return response.choices[0].message.content.strip()


def format_context(chunks: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[S{index}] Source: {chunk.source_name}",
                    f"URL: {chunk.source_location}",
                    f"Chunk ID: {chunk.chunk_id}",
                    f"Distance: {chunk.distance:.4f}",
                    f"Text: {chunk.text}",
                ]
            )
        )
    return "\n\n".join(blocks)


def format_sources(chunks: list[RetrievedChunk]) -> list[str]:
    seen: set[tuple[str, str]] = set()
    sources: list[str] = []
    for chunk in chunks:
        key = (chunk.source_name, chunk.source_location)
        if key in seen:
            continue
        seen.add(key)
        sources.append(f"{chunk.source_name} ({chunk.source_location})")
    return sources


def chunks_to_dicts(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "source_name": chunk.source_name,
            "source_location": chunk.source_location,
            "chunk_index": chunk.chunk_index,
            "distance": chunk.distance,
            "text": chunk.text,
        }
        for chunk in chunks
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask a grounded question over retrieved professor-review chunks.")
    parser.add_argument("question", nargs="?", help="Question to ask.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    question = args.question or input("Question: ").strip()
    result = ask(question, top_k=args.top_k)

    print("\nAnswer:")
    print(result["answer"])
    print("\nRetrieved from:")
    for source in result["sources"]:
        print(f"- {source}")
    print("\nRetrieved chunks:")
    for chunk in result["chunks"]:
        print(f"- {chunk['chunk_id']} | distance={chunk['distance']:.4f} | {chunk['source_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
