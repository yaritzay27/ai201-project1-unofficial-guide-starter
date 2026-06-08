"""Run the five planning.md evaluation questions and print README-ready results.

WSL usage:
    source .venv/bin/activate
    python3 run_evaluation.py
"""

from __future__ import annotations

from query import ask


EVALUATION_ITEMS = [
    {
        "question": "What positive traits do students mention about Roman Stelmach?",
        "expected": "Students describe him as caring, sweet, generous with grading, clear at teaching, and helpful with understanding the material.",
    },
    {
        "question": "What complaints appear most often in reviews for Professor Subash Shankar?",
        "expected": "Heavy homework and difficult exams",
    },
    {
        "question": "What course is Professor Tong Yi most frequently reviewed for?",
        "expected": "CSCI 135",
    },
    {
        "question": "What positive trait is most commonly mentioned about Professor Yuna Won?",
        "expected": "Clear explanations",
    },
    {
        "question": "What negative trait is most commonly mentioned about Professor Justin Tojeira?",
        "expected": "Slow grading",
    },
]

FAILURE_PROBE = "What do students say about Hunter College parking?"


def main() -> int:
    print("# Evaluation Results\n")
    for index, item in enumerate(EVALUATION_ITEMS, start=1):
        result = ask(item["question"])
        print(f"## {index}. {item['question']}")
        print(f"Expected: {item['expected']}\n")
        print("System response:")
        print(result["answer"])
        print("\nSources:")
        for source in result["sources"]:
            print(f"- {source}")
        print("\nRetrieved chunks:")
        for chunk in result["chunks"]:
            print(f"- {chunk['chunk_id']} | distance={chunk['distance']:.4f} | {chunk['source_name']}")
        print("\n")

    failure = ask(FAILURE_PROBE)
    print(f"## Failure/coverage probe: {FAILURE_PROBE}")
    print(failure["answer"])
    print("\nClosest retrieved chunks:")
    for chunk in failure["chunks"]:
        print(f"- {chunk['chunk_id']} | distance={chunk['distance']:.4f} | {chunk['source_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
