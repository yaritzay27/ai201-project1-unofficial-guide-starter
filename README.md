# The Unofficial Guide - Project 1

## Domain

My system covers Hunter College Computer Science and Mathematics professor reviews, course experiences, difficulty, workload, grading, and student advice. This information is valuable because official course descriptions do not usually explain how students experience a professor's teaching style, exams, grading, or workload. Students often rely on scattered Rate My Professors pages and informal advice, so this project brings those reviews into one searchable grounded assistant.

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Susan Epstein reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/192300 |
| 2 | Sven Dietrich reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/2674099 |
| 3 | Raman Kannan reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/2448249 |
| 4 | Subash Shankar reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/257190 |
| 5 | Tong Yi reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/2634841 |
| 6 | Justin Tojeira reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/1660967 |
| 7 | Roman Stelmach reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/535583 |
| 8 | Robert Thompson reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/421746 |
| 9 | Ilya Kapovich reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/2408145 |
| 10 | Yuna Won reviews | Rate My Professors page | https://www.ratemyprofessors.com/professor/2951672 |

The ingestion script saves fetched raw pages in `data/raw/`, cleaned text in `data/cleaned/`, and final chunks in `data/chunks.json` and `data/chunks.jsonl`.

## Chunking Strategy

**Chunk size:** One review per chunk when possible. Longer reviews are split around sentence boundaries with a maximum size of about 400-500 characters.

**Overlap:** I originally planned 50-100 characters of overlap for long posts, but I removed overlap for split review bodies because character overlap caused continuation chunks to begin mid-sentence. Splitting long reviews on sentence boundaries produced cleaner standalone chunks.

**Why these choices fit your documents:** The corpus is review-heavy, so each review usually contains one student experience about a professor, course, workload, or grading. Keeping each review together preserves context and makes retrieval more specific. Summary chunks are also kept for each professor so ranking questions such as "highest rated professor" can be answered from structured review data.

**Final chunk count:** 80 chunks across 10 Rate My Professors sources.

## Embedding Model

**Model used:** all-MiniLM-L6-v2 (Sentence Transformers)

I chose this model because it runs locally, does not require an API key, is fast enough for a small course project, and is commonly used for semantic retrieval. It embeds the cleaned review chunks into ChromaDB, where each vector is stored with source metadata including `source_name`, `source_location`, `source_id`, and `chunk_index`.

**Production tradeoff reflection:** If I were deploying this system for real students and cost was not a constraint, I would compare larger embedding models with stronger semantic accuracy and longer context support. A larger model might better understand nuanced student language, sarcasm, abbreviations, and course nicknames. The tradeoff would be higher latency, more memory usage, and possibly API cost. I would also consider whether local embeddings are enough or whether an API-hosted model is worth it for better ranking quality.

## Grounded Generation

**System prompt grounding instruction:**

```
You are a grounded question-answering assistant for a Hunter College unofficial guide.
Answer using only the provided retrieved documents.
Do not use outside knowledge, assumptions, or guesses.
For ranking or recommendation questions, answer only by comparing the retrieved review data and clearly explain the evidence used.
If the retrieved documents do not contain enough information to answer, respond exactly:
I don't have enough information on that.
When you answer, cite the source markers that support each claim, such as [S1] or [S2].
Keep the answer concise and directly tied to the retrieved evidence.
```

**How source attribution is surfaced in the response:** Retrieved chunks are formatted as `[S1]`, `[S2]`, etc. in the prompt, and the model is instructed to cite those markers in the answer. The Gradio app also appends a programmatic source list from chunk metadata, so the interface shows which Rate My Professors page the answer came from even if the model's wording changes. For unsupported questions, the app returns "I don't have enough information on that" and does not list supporting sources.

## Evaluation Report

I ran the system on the five questions from `planning.md`. The table below summarizes the behavior I observed. The exact wording can vary slightly because generation uses Groq's `llama-3.3-70b-versatile`, but each answer was checked against the retrieved chunks and source list.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What positive traits do students mention about Roman Stelmach? | Students describe him as caring, sweet, generous with grading, clear at teaching, and helpful with understanding the material. | The system returned Roman Stelmach chunks and summarized that students call him nice, sweet, caring, helpful, generous with grading, clear at teaching, and good at helping students understand material. | Relevant | Accurate |
| 2 | What complaints appear most often in reviews for Professor Subash Shankar? | Heavy homework and difficult exams | The system retrieved Subash Shankar chunks mentioning lots of homework, test-heavy grading, lecture confusion, limited resources, and difficult exams. | Relevant | Accurate |
| 3 | What course is Professor Tong Yi most frequently reviewed for? | CSCI 135 | The retrieved chunks and professor summary focused on CS135/CS13500/CSCI135. The system answered that Tong Yi is most often reviewed for the CSCI 135 course family. | Relevant | Accurate |
| 4 | What positive trait is most commonly mentioned about Professor Yuna Won? | Clear explanations | The system retrieved Yuna Won chunks with tags and comments about clear grading criteria, structured teaching, clear standards, and direct explanations. It answered that clarity/clear expectations are the main positive trait. | Relevant | Accurate |
| 5 | What negative trait is most commonly mentioned about Professor Justin Tojeira? | Self-Learning class | The system retrieved Justin Tojeira reviews mentioning that students felt they had to teach themselves, that support was limited, and that homework/projects/exams were difficult to navigate. This matched the expected self-learning theme. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

## Failure Case Analysis

**Question that failed:** What do students say about CSCI 135?

**What the system returned:** The system responded, "I don't have enough information on that." It also retrieved weak or unrelated chunks from professors such as Susan Epstein, Justin Tojeira, and Sven Dietrich instead of focusing on Tong Yi reviews, even though the corpus contains course variants like `CS135`, `CS13500`, and `CSCI135`.

**Root cause (tied to a specific pipeline stage):** This is a preprocessing and retrieval issue. The course appears in multiple formats in the source data, including `CS135`, `CS13500`, and `CSCI135`, while the user query used `CSCI 135` with a space. The pipeline currently stores course names as text inside chunks but does not normalize them into a shared metadata field, so the embedding model did not reliably treat all variants as equivalent.

**What you would change to fix it:** I would normalize course codes during ingestion and query handling. For example, `CSCI 135`, `CS 135`, `CS13500`, and `CSCI135` should all map to a shared metadata value such as `CSCI135`. Then the retrieval pipeline could filter or boost chunks with matching normalized course metadata before sending context to the LLM.

## Spec Reflection

**One way the spec helped you during implementation:** The planning spec forced me to decide early that the project would focus on Hunter College CS and Math professor reviews, which kept the pipeline scoped. The chunking strategy also helped because it made review-level chunks the default, rather than arbitrary fixed-size text windows. That decision made the retrieved chunks easier to inspect and cite because each chunk usually represented one student experience.

**One way your implementation diverged from the spec, and why:** The original plan mentioned BeautifulSoup and character overlap for longer chunks. In practice, Rate My Professors pages contained useful review data inside embedded JSON, so I extracted `window.__RELAY_STORE__` instead of scraping visible HTML with BeautifulSoup. I also removed overlap for split review bodies because character overlap caused continuation chunks to start mid-sentence, which made retrieval results harder to read.

## AI Usage

**Instance 1**

- *What I gave the AI:* I gave Codex my `planning.md` domain, document list, and chunking strategy for Milestone 3.
- *What it produced:* Codex produced `document_pipeline.py`, which fetches Rate My Professors pages, saves raw text, extracts review data from embedded JSON, cleans it, and writes chunk files.
- *What I changed or overrode:* I asked Codex to fix chunk overlap because some continuation chunks started in the middle of a sentence. The final implementation splits long review bodies on sentence boundaries with no overlap.

**Instance 2**

- *What I gave the AI:* I gave Codex my Retrieval Approach section and asked it to implement Milestone 4 with `all-MiniLM-L6-v2`, ChromaDB, source metadata, and test queries.
- *What it produced:* Codex produced `retrieval_pipeline.py`, which embeds chunks, stores them in ChromaDB, retrieves top-k chunks, and prints distance scores.
- *What I changed or overrode:* I changed the first evaluation question from a simple rating lookup to a semantic question about Roman Stelmach's positive traits. I also had Codex add a stale-data hash check so the Chroma collection does not silently reuse outdated chunks.

**Instance 3**

- *What I gave the AI:* I gave Codex the Milestone 5 grounding requirement and asked for a Groq-based answer generator plus a Gradio interface.
- *What it produced:* Codex produced `query.py` and `app.py`, including a grounded system prompt, programmatic source attribution, and a Hunter College purple-themed interface.
- *What I changed or overrode:* When the app overgeneralized on "best professor" questions, I asked Codex to add a deterministic summary-query path. Ranking questions now compare professor summary chunks directly instead of relying only on semantic retrieval and the LLM.

## How to Run

In WSL:

```bash
cd /mnt/c/ai201-project1-unofficial-guide-starter
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 document_pipeline.py --use-planning-urls
python3 retrieval_pipeline.py --rebuild --test
python3 app.py
```

Then open `http://localhost:7860`.

To run the evaluation helper:

```bash
python3 run_evaluation.py
```

## Stretch Feature: Chunking Strategy Comparison

I compared two chunking strategies on the same retrieval query set:

1. **Review-aware chunking:** the main project strategy, where each professor summary or individual review is kept together when possible.
2. **Fixed-size chunking:** an alternate strategy generated from the cleaned documents using 500-character chunks with 75-character overlap.

The comparison uses `all-MiniLM-L6-v2` for both strategies and checks the top retrieved chunk for three queries:

- What positive traits do students mention about Roman Stelmach?
- What complaints appear most often in reviews for Professor Subash Shankar?
- What course is Professor Tong Yi most frequently reviewed for?

To reproduce the comparison, run:

```bash
python3 compare_chunking.py
```

The review-aware strategy produced 80 chunks. The fixed-size strategy produced 59 chunks.

| Query | Strategy | Top source | Distance | Relevance | Top chunk excerpt |
|---|---|---|---:|---|---|
| What positive traits do students mention about Roman Stelmach? | Review-aware | Rate My Professors - Roman Stelmach | 0.3332 | Relevant | Professor: Roman Stelmach. Course: STAT213. Date: 2026-01-07... |
| What positive traits do students mention about Roman Stelmach? | Fixed-size 500 chars | Rate My Professors - Roman Stelmach | 0.4136 | Relevant | ng. Review: Was a very great professor, was very caring... |
| What complaints appear most often in reviews for Professor Subash Shankar? | Review-aware | Rate My Professors - Subash Shankar | 0.3066 | Relevant | Professor: Subash Shankar. Course: 260. Date: 2026-03-31... |
| What complaints appear most often in reviews for Professor Subash Shankar? | Fixed-size 500 chars | Rate My Professors - Subash Shankar | 0.3545 | Relevant | Brightspace, nor answers to homework. No practice material... |
| What course is Professor Tong Yi most frequently reviewed for? | Review-aware | Rate My Professors - Tong Yi | 0.2484 | Relevant | Professor: Tong Yi. Course: CS13500. Date: 2025-08-28... |
| What course is Professor Tong Yi most frequently reviewed for? | Fixed-size 500 chars | Rate My Professors - Tong Yi | 0.3200 | Relevant | k. Review: The professor is a tough grader... |

Both strategies retrieved the correct professor for all three queries, but the review-aware strategy performed better on every query because its distance scores were lower. It also produced cleaner top chunks: the review-aware chunks begin with professor metadata and preserve the course, ratings, tags, and review text together. The fixed-size chunks were relevant, but their excerpts often started in the middle of words or sentences, such as "ng. Review..." or "Brightspace, nor answers...". This makes them harder for the LLM and the user to interpret. Based on these results, the review-aware chunking strategy is the better fit for this review-heavy corpus.
