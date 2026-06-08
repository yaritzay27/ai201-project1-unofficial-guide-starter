"""Gradio interface for the Milestone 5 grounded RAG app."""

from __future__ import annotations

import gradio as gr

from query import ask


HUNTER_CSS = """
:root {
    --hunter-purple: #3f0157;
    --hunter-purple-dark: #260034;
    --hunter-purple-soft: #f5eff8;
    --hunter-gold: #f2b705;
    --ink: #1c1524;
    --muted: #6b6072;
    --line: #e7ddeb;
}

.gradio-container {
    background:
        linear-gradient(180deg, rgba(63, 1, 87, 0.08), rgba(255, 255, 255, 0) 260px),
        #fbf9fc;
    color: var(--ink);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.hunter-shell {
    max-width: 980px;
    margin: 0 auto;
}

.hunter-title h1 {
    color: var(--hunter-purple);
    font-size: 2.1rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}

.hunter-title {
    border-bottom: 4px solid var(--hunter-gold);
    margin-bottom: 1.1rem;
    padding-bottom: 0.55rem;
}

.hunter-panel {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 10px 28px rgba(42, 0, 58, 0.08);
    padding: 16px;
}

.hunter-panel textarea,
.hunter-panel input {
    border-color: var(--line) !important;
    border-radius: 8px !important;
}

.hunter-panel textarea:focus,
.hunter-panel input:focus {
    border-color: var(--hunter-purple) !important;
    box-shadow: 0 0 0 3px rgba(63, 1, 87, 0.14) !important;
}

.hunter-primary {
    background: var(--hunter-purple) !important;
    border: 1px solid var(--hunter-purple) !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

.hunter-primary:hover {
    background: var(--hunter-purple-dark) !important;
    border-color: var(--hunter-purple-dark) !important;
}

.hunter-secondary {
    background: var(--hunter-purple-soft) !important;
    border: 1px solid var(--line) !important;
    color: var(--hunter-purple) !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

.hunter-output textarea {
    background: #fffefe !important;
}

.hunter-sources textarea {
    background: var(--hunter-purple-soft) !important;
    color: var(--hunter-purple-dark) !important;
}

.hunter-debug textarea {
    font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
    font-size: 0.86rem !important;
}

.gradio-container label,
.gradio-container .label-wrap {
    color: var(--muted) !important;
    font-weight: 700 !important;
}
"""

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


with gr.Blocks(title="Hunter Unofficial Guide", css=HUNTER_CSS) as demo:
    with gr.Column(elem_classes=["hunter-shell"]):
        gr.Markdown("# Hunter Unofficial Guide", elem_classes=["hunter-title"])

        with gr.Group(elem_classes=["hunter-panel"]):
            question = gr.Textbox(
                label="Your question",
                lines=2,
                placeholder="Ask about professors, courses, workload, exams...",
            )
            with gr.Row():
                ask_button = gr.Button("Ask", variant="primary", elem_classes=["hunter-primary"])
                clear_button = gr.Button("Clear", elem_classes=["hunter-secondary"])

        with gr.Group(elem_classes=["hunter-panel"]):
            answer = gr.Textbox(label="Answer", lines=8, elem_classes=["hunter-output"])
            sources = gr.Textbox(label="Retrieved from", lines=5, elem_classes=["hunter-sources"])
            retrieved_chunks = gr.Textbox(label="Retrieved chunks", lines=12, elem_classes=["hunter-debug"])

        gr.Examples(examples=EXAMPLES, inputs=question)

        ask_button.click(handle_query, inputs=question, outputs=[answer, sources, retrieved_chunks])
        question.submit(handle_query, inputs=question, outputs=[answer, sources, retrieved_chunks])
        clear_button.click(lambda: ("", "", "", ""), outputs=[question, answer, sources, retrieved_chunks])


if __name__ == "__main__":
    demo.launch()
