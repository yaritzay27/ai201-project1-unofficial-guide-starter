"""Unit tests for deterministic document transformation logic."""

from __future__ import annotations

import json
import unittest

from document_pipeline import Document, chunk_document, clean_text, extract_rmp_relay_text


def relay_store_page(store: dict[str, object]) -> str:
    return f"<html><script>window.__RELAY_STORE__ = {json.dumps(store)};</script></html>"


class DocumentPipelineTests(unittest.TestCase):
    def test_extract_rmp_relay_text_parses_teacher_summary_and_rating(self) -> None:
        store = {
            "teacher-1": {
                "__id": "teacher-1",
                "__typename": "Teacher",
                "firstName": "Test",
                "lastName": "Professor",
                "department": "Computer Science",
                "school": {"__ref": "school-1"},
                "avgRating": 4.5,
                "numRatings": 12,
                "avgDifficulty": 2.1,
                "wouldTakeAgainPercent": 88.88,
                "courseCodes": {"__refs": ["course-1"]},
            },
            "school-1": {
                "__id": "school-1",
                "__typename": "School",
                "name": "Hunter College",
            },
            "course-1": {
                "__id": "course-1",
                "__typename": "Course",
                "courseName": "CSCI135",
            },
            "rating-1": {
                "__id": "rating-1",
                "__typename": "Rating",
                "legacyId": 123,
                "comment": "Very clear lectures and helpful office hours.",
                "date": "2026-01-01 00:00:00 +0000 UTC",
                "class": "CSCI135",
                "helpfulRating": 5,
                "clarityRating": 5,
                "difficultyRating": 2,
                "attendanceMandatory": "mandatory",
                "wouldTakeAgain": 1,
                "grade": "A",
                "ratingTags": "Amazing lectures--Accessible outside class",
            },
        }

        extracted = extract_rmp_relay_text(relay_store_page(store))

        self.assertIn("Professor: Test Professor", extracted)
        self.assertIn("Average rating: 4.5/5", extracted)
        self.assertIn("Would take again: 88.9%", extracted)
        self.assertIn("Course: CSCI135", extracted)
        self.assertIn("Review: Very clear lectures", extracted)

    def test_clean_text_removes_html_artifacts(self) -> None:
        raw = "<html><body><nav>Skip to main content</nav><p>Professor is helpful &amp; clear.</p></body></html>"

        cleaned = clean_text(raw)

        self.assertIn("Professor is helpful & clear.", cleaned)
        self.assertNotIn("<p>", cleaned)
        self.assertNotIn("&amp;", cleaned)

    def test_chunk_document_preserves_review_metadata_when_splitting(self) -> None:
        long_review = (
            "Professor: Split Tester. Course: CSCI135. Date: 2026-01-01. Quality: 5. "
            "Clarity: 5. Difficulty: 2. Review: "
            "This professor explains concepts clearly. "
            "Students mention that lectures are organized and examples are useful. "
            "Office hours are helpful for debugging assignments. "
            "The class has projects, quizzes, and exams that require steady practice. "
            "Review sessions help students understand what to focus on before tests. "
            "Overall the course is manageable when students attend class and practice regularly. "
            "Students also mention that the instructor connects examples back to homework. "
            "The review is intentionally long enough to trigger sentence-based splitting."
        )
        doc = Document(
            source_id="test-doc",
            source_name="Test Source",
            source_location="memory",
            raw_text=long_review,
            clean_text=long_review,
        )

        chunks = chunk_document(doc)

        self.assertGreaterEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertTrue(chunk.text.startswith("Professor: Split Tester. Course: CSCI135"))
            self.assertNotIn("Review: concepts clearly", chunk.text)


if __name__ == "__main__":
    unittest.main()
