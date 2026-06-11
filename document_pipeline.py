"""Milestone 3 document ingestion, cleaning, and chunking pipeline.

Run examples:
    .venv/bin/python document_pipeline.py
    .venv/bin/python document_pipeline.py --use-planning-urls
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import random
import re
import sys
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
OUTPUT_DIR = PROJECT_ROOT / "data"
RAW_DIR = OUTPUT_DIR / "raw"
CLEAN_DIR = OUTPUT_DIR / "cleaned"
CHUNKS_JSON = OUTPUT_DIR / "chunks.json"
CHUNKS_JSONL = OUTPUT_DIR / "chunks.jsonl"

SUPPORTED_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".json", ".csv"}
MAX_CHARS = 500
OVERLAP_CHARS = 75
MIN_CHARS = 30


@dataclass
class Document:
    source_id: str
    source_name: str
    source_location: str
    raw_text: str
    clean_text: str = ""


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    source_name: str
    source_location: str
    chunk_index: int
    text: str


class TextExtractor(HTMLParser):
    """Small stdlib HTML-to-text extractor so the project needs no new package."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "div", "li", "section", "article", "tr", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def get_text(self) -> str:
        return " ".join(self._parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load, clean, and chunk project documents.")
    parser.add_argument("--documents-dir", type=Path, default=DOCUMENTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--use-planning-urls",
        action="store_true",
        help="Also fetch URLs listed in planning.md. Rate My Professors may block these requests.",
    )
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def load_local_documents(documents_dir: Path) -> list[Document]:
    docs: list[Document] = []
    if not documents_dir.exists():
        return docs

    for path in sorted(documents_dir.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"Skipping unsupported file type: {path}", file=sys.stderr)
            continue

        raw_text = read_document_file(path)
        docs.append(
            Document(
                source_id=slugify(path.stem),
                source_name=path.stem,
                source_location=str(path.relative_to(PROJECT_ROOT)),
                raw_text=raw_text,
            )
        )
    return docs


def read_document_file(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".md", ".html", ".htm"}:
        return path.read_text(encoding="utf-8", errors="replace")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(data, ensure_ascii=False, indent=2)

    if path.suffix.lower() == ".csv":
        rows: list[str] = []
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                for row in reader:
                    cells = [f"{key}: {value}" for key, value in row.items() if value]
                    if cells:
                        rows.append(" | ".join(cells))
            else:
                f.seek(0)
                plain_reader = csv.reader(f)
                rows.extend(" | ".join(cell for cell in row if cell) for row in plain_reader)
        return "\n\n".join(rows)

    raise ValueError(f"Unsupported file type: {path}")


def load_planning_urls(planning_path: Path) -> list[Document]:
    if not planning_path.exists():
        return []

    planning_text = planning_path.read_text(encoding="utf-8", errors="replace")
    docs: list[Document] = []
    for match in re.finditer(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|[^|]*\|\s*(https?://[^|\s]+)", planning_text):
        source_id = f"planning-url-{match.group(1)}"
        source_name = match.group(2).strip()
        url = match.group(3).strip()
        try:
            raw_text = fetch_url(url)
        except URLError as exc:
            print(f"Could not fetch {url}: {exc}", file=sys.stderr)
            continue
        docs.append(Document(source_id=source_id, source_name=source_name, source_location=url, raw_text=raw_text))
    return docs


def fetch_url(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def clean_text(raw_text: str) -> str:
    relay_text = extract_rmp_relay_text(raw_text)
    if relay_text:
        return relay_text

    text = html.unescape(raw_text)
    if looks_like_html(text):
        parser = TextExtractor()
        parser.feed(text)
        text = parser.get_text()

    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)

    boilerplate_patterns = [
        r"\bSign up\b.*?\bLog in\b",
        r"\bAccept all cookies\b",
        r"\bCookie Policy\b",
        r"\bPrivacy Policy\b",
        r"\bTerms of Use\b",
        r"\bAdvertisement\b",
        r"\bShare\b",
        r"\bRead more\b",
        r"\bSkip to main content\b",
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE | re.DOTALL)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_rmp_relay_text(raw_text: str) -> str:
    match = re.search(r"window\.__RELAY_STORE__\s*=\s*(\{.*?\});", raw_text, flags=re.DOTALL)
    if not match:
        return ""

    try:
        store = json.loads(match.group(1))
    except json.JSONDecodeError:
        return ""

    school_names = {
        item.get("__id"): item.get("name")
        for item in store.values()
        if isinstance(item, dict) and item.get("__typename") == "School"
    }
    teachers = [
        item
        for item in store.values()
        if isinstance(item, dict) and item.get("__typename") == "Teacher" and item.get("firstName")
    ]
    ratings = [
        item
        for item in store.values()
        if isinstance(item, dict) and item.get("__typename") == "Rating" and item.get("comment")
    ]

    lines: list[str] = []
    for teacher in teachers:
        name = f"{teacher.get('firstName', '').strip()} {teacher.get('lastName', '').strip()}".strip()
        school = resolve_ref_name(teacher.get("school"), school_names)
        summary_parts = [
            f"Professor: {name}",
            f"Department: {teacher.get('department')}",
            f"School: {school}",
            f"Average rating: {teacher.get('avgRating')}/5",
            f"Number of ratings: {teacher.get('numRatings')}",
            f"Average difficulty: {teacher.get('avgDifficulty')}/5",
            f"Would take again: {format_percent(teacher.get('wouldTakeAgainPercent'))}",
        ]
        courses = course_names_for_teacher(store, teacher)
        if courses:
            summary_parts.append(f"Reviewed courses: {', '.join(courses)}")
        lines.append(". ".join(part for part in summary_parts if not part.endswith(": None")) + ".")

    seen_rating_ids: set[str] = set()
    for rating in ratings:
        rating_id = str(rating.get("legacyId") or rating.get("id") or "")
        if rating_id in seen_rating_ids:
            continue
        seen_rating_ids.add(rating_id)
        lines.append(format_rating(rating, teachers))

    return "\n\n".join(line for line in lines if line.strip())


def resolve_ref_name(ref_obj: object, id_to_name: dict[str | None, str | None]) -> str | None:
    if not isinstance(ref_obj, dict):
        return None
    return id_to_name.get(ref_obj.get("__ref"))


def course_names_for_teacher(store: dict[str, object], teacher: dict[str, object]) -> list[str]:
    course_refs = teacher.get("courseCodes")
    if not isinstance(course_refs, dict):
        return []
    refs = course_refs.get("__refs")
    if not isinstance(refs, list):
        return []

    courses: list[str] = []
    for ref in refs:
        item = store.get(str(ref))
        if isinstance(item, dict) and item.get("courseName"):
            courses.append(str(item["courseName"]))
    return courses


def format_rating(rating: dict[str, object], teachers: list[dict[str, object]]) -> str:
    professor_name = ""
    if len(teachers) == 1:
        professor_name = f"{teachers[0].get('firstName', '').strip()} {teachers[0].get('lastName', '').strip()}".strip()

    fields = [
        ("Professor", professor_name),
        ("Course", rating.get("class")),
        ("Date", short_date(rating.get("date"))),
        ("Quality", rating.get("helpfulRating")),
        ("Clarity", rating.get("clarityRating")),
        ("Difficulty", rating.get("difficultyRating")),
        ("Attendance", rating.get("attendanceMandatory")),
        ("Would take again", yes_no(rating.get("wouldTakeAgain"))),
        ("Grade", rating.get("grade")),
        ("Tags", tags_text(rating.get("ratingTags"))),
        ("Review", rating.get("comment")),
    ]
    return ". ".join(f"{label}: {value}" for label, value in fields if value not in {None, "", "None"}) + "."


def format_percent(value: object) -> str:
    if value in {None, ""}:
        return "unknown"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"{value}%"
    rounded = round(number, 1)
    if rounded.is_integer():
        return f"{int(rounded)}%"
    return f"{rounded}%"


def short_date(value: object) -> str | None:
    if not value:
        return None
    return str(value).split(" +", maxsplit=1)[0]


def yes_no(value: object) -> str | None:
    if value == 1:
        return "Yes"
    if value == 0:
        return "No"
    return None


def tags_text(value: object) -> str | None:
    if not value:
        return None
    return ", ".join(part.strip(" -") for part in str(value).split("--") if part.strip(" -"))


def looks_like_html(text: str) -> bool:
    return bool(re.search(r"</?(html|body|div|span|p|script|style|article|section)\b", text, re.IGNORECASE))


def chunk_document(doc: Document) -> list[Chunk]:
    blocks = review_or_paragraph_blocks(doc.clean_text)
    chunks: list[Chunk] = []
    chunk_index = 0

    for block in blocks:
        if len(block) <= MAX_CHARS:
            pieces = [block]
        else:
            pieces = split_review_block(block, MAX_CHARS, OVERLAP_CHARS)

        for piece in pieces:
            piece = normalize_chunk(piece)
            if len(piece) < MIN_CHARS:
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.source_id}-{chunk_index:04d}",
                    source_id=doc.source_id,
                    source_name=doc.source_name,
                    source_location=doc.source_location,
                    chunk_index=chunk_index,
                    text=piece,
                )
            )
            chunk_index += 1

    return chunks


def split_review_block(text: str, max_chars: int, overlap: int) -> list[str]:
    review_marker = ". Review: "
    if review_marker not in text:
        return split_long_text(text, max_chars, overlap)

    prefix, review = text.split(review_marker, maxsplit=1)
    prefix = f"{prefix}{review_marker}"
    available_chars = max(max_chars - len(prefix), 120)
    pieces = split_long_text(review, available_chars, overlap=0)
    return [f"{prefix}{piece}".strip() for piece in pieces]


def review_or_paragraph_blocks(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = [normalize_chunk(block) for block in re.split(r"\n\s*\n", text)]
    paragraphs = [block for block in paragraphs if len(block) >= MIN_CHARS]
    if len(paragraphs) >= 2:
        return paragraphs
    if ". Review:" in text:
        return [normalize_chunk(text)]

    review_splits = re.split(
        r"(?=\b(?:Review|Student Review|Professor Review)\b[:\s])",
        text,
        flags=re.IGNORECASE,
    )
    review_blocks = [normalize_chunk(block) for block in review_splits if len(normalize_chunk(block)) >= MIN_CHARS]
    if len(review_blocks) >= 2:
        return review_blocks

    if paragraphs:
        return paragraphs

    return [normalize_chunk(text)]


def split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(split_by_words(sentence, max_chars, overlap))
            continue

        proposed = f"{current} {sentence}".strip()
        if len(proposed) <= max_chars:
            current = proposed
        else:
            chunks.append(current.strip())
            current = add_overlap(current, overlap)
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current.strip())
    return chunks


def split_by_words(text: str, max_chars: int, overlap: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current_words: list[str] = []

    for word in words:
        proposed = " ".join(current_words + [word])
        if len(proposed) <= max_chars:
            current_words.append(word)
            continue
        if current_words:
            current = " ".join(current_words)
            chunks.append(current)
            current_words = add_overlap(current, overlap).split()
        current_words.append(word)

    if current_words:
        chunks.append(" ".join(current_words))
    return chunks


def add_overlap(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    if len(text) <= overlap:
        return text
    overlap_text = text[-overlap:]
    first_space = overlap_text.find(" ")
    return overlap_text[first_space + 1 :] if first_space >= 0 else overlap_text


def source_name_from_clean_text(default: str, clean_text: str) -> str:
    match = re.search(r"\bProfessor:\s*([^.\n]+)", clean_text)
    if not match:
        return default
    professor_name = match.group(1).strip()
    if not professor_name:
        return default
    if "Rate My Professors" in default:
        return f"Rate My Professors - {professor_name}"
    return professor_name


def normalize_chunk(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -|\t\r\n")


def write_outputs(docs: Iterable[Document], chunks: list[Chunk], output_dir: Path) -> None:
    raw_dir = output_dir / "raw"
    clean_dir = output_dir / "cleaned"
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    for doc in docs:
        safe_id = slugify(doc.source_id)
        (raw_dir / f"{safe_id}.txt").write_text(doc.raw_text, encoding="utf-8")
        (clean_dir / f"{safe_id}.txt").write_text(doc.clean_text, encoding="utf-8")

    chunks_data = [asdict(chunk) for chunk in chunks]
    (output_dir / "chunks.json").write_text(json.dumps(chunks_data, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for chunk in chunks_data:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def print_report(docs: list[Document], chunks: list[Chunk], sample_size: int, seed: int) -> None:
    print(f"Loaded documents: {len(docs)}")
    for doc in docs:
        print(f"- {doc.source_name}: raw={len(doc.raw_text)} chars, cleaned={len(doc.clean_text)} chars")
    print(f"\nTotal chunks: {len(chunks)}")
    print(f"Output files: {CHUNKS_JSON.relative_to(PROJECT_ROOT)}, {CHUNKS_JSONL.relative_to(PROJECT_ROOT)}")

    if not chunks:
        return

    random.seed(seed)
    sample = random.sample(chunks, min(sample_size, len(chunks)))
    print(f"\nRandom checkpoint chunks ({len(sample)}):")
    for chunk in sample:
        print("\n" + "=" * 72)
        print(f"{chunk.chunk_id} | {chunk.source_name} | {len(chunk.text)} chars")
        print(chunk.text)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "document"


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()

    docs = load_local_documents(args.documents_dir)
    if args.use_planning_urls:
        docs.extend(load_planning_urls(PROJECT_ROOT / "planning.md"))

    if not docs:
        print(
            "No documents found. Add .txt, .md, .html, .json, or .csv files to the documents/ "
            "folder, or run with --use-planning-urls to attempt URL collection."
        )
        return 1

    for doc in docs:
        doc.clean_text = clean_text(doc.raw_text)
        doc.source_name = source_name_from_clean_text(doc.source_name, doc.clean_text)

    chunks: list[Chunk] = []
    for doc in docs:
        chunks.extend(chunk_document(doc))

    write_outputs(docs, chunks, output_dir)
    print_report(docs, chunks, args.sample_size, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
