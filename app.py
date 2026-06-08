"""Gradio interface for the Milestone 5 grounded RAG app."""

from __future__ import annotations

import gradio as gr

from query import ask


EXAMPLES = [
    "Who is the highest rated professor?",
    "Who is the best Computer Science professor?",
    "Who is the best math professor?",
    "Which professor is the most difficult?",
    "What positive traits do students mention about Roman Stelmach?",
    "What complaints appear most often in reviews for Professor Subash Shankar?",
    "What course is Professor Tong Yi most frequently reviewed for?",
    "What do students say about Hunter College parking?",
]


def handle_query(question: str) -> tuple[str, str, str]:
    result = ask(question)
    sources = "\n".join(f"- {source}" for source in result["sources"]) or "No supporting sources found."
    chunks = "\n\n".join(
        (
            f"{chunk['chunk_id']} | distance={chunk['distance']:.4f} | {chunk['source_name']}\n"
            f"{chunk['text']}"
        )
        for chunk in result["chunks"]
    )
    return result["answer"], sources, chunks


with gr.Blocks(title="Hunter Unofficial Guide") as demo:
    gr.Markdown("# Hunter Unofficial Guide")

    question = gr.Textbox(label="Your question", lines=2, placeholder="Ask about professors, courses, workload, exams...")
    with gr.Row():
        ask_button = gr.Button("Ask", variant="primary")
        clear_button = gr.Button("Clear")

    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=5)
    retrieved_chunks = gr.Textbox(label="Retrieved chunks", lines=12)

    gr.Examples(examples=EXAMPLES, inputs=question)

    ask_button.click(handle_query, inputs=question, outputs=[answer, sources, retrieved_chunks])
    question.submit(handle_query, inputs=question, outputs=[answer, sources, retrieved_chunks])
    clear_button.click(lambda: ("", "", "", ""), outputs=[question, answer, sources, retrieved_chunks])


if __name__ == "__main__":
    demo.launch()
