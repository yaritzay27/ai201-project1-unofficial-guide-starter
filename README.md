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

**Five labeled sample chunks:**

1. `planning-url-3-0000` - Raman Kannan summary: "Professor: Raman Kannan. Department: Computer Science. School: Hunter College. Average rating: 4.2/5..."
2. `planning-url-3-0001` - Raman Kannan review: "Overall, Mr. Raman has been an incredible professor. He takes time to break down each subject..."
3. `planning-url-4-0001` - Subash Shankar review: "No material to review, lectures made on the fly by hand with frequent mistakes..."
4. `planning-url-5-0000` - Tong Yi summary: "Professor: Tong Yi. Department: Computer Science... Reviewed courses: CS135, CS13500, CSCI127, CSCI135..."
5. `planning-url-7-0002` - Roman Stelmach review: "Was a very great professor, was very caring. He grades lightly and cares if you understand the work."

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

**Full example response with visible source attribution:**

Question: `What positive traits do students mention about Roman Stelmach?`

Answer: Students mention that Roman Stelmach is nice, sweet, caring, gives good feedback, has amazing lectures, is a good grader, grades generously, and helps students understand the material [S1, S2, S3, S4, S5].

Retrieved from:

- Rate My Professors - Roman Stelmach (https://www.ratemyprofessors.com/professor/535583)

**Out-of-scope example response:**

Question: `What do students say about Hunter College parking?`

Answer: I don't have enough information on that.

The retrieved chunks were weak and scattered across unrelated professor pages, so the app declined instead of generating an unsupported answer.

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

**Top retrieved chunks for representative queries:**

| Query | Top returned chunks | Why relevant |
|---|---|---|
| What positive traits do students mention about Roman Stelmach? | `planning-url-7-0005` distance 0.3332; `planning-url-7-0003` distance 0.3745; `planning-url-7-0002` distance 0.3801 | All top chunks are Roman Stelmach reviews and mention traits such as nice, sweet, caring, generous grading, and helping students understand material. |
| What complaints appear most often in reviews for Professor Subash Shankar? | `planning-url-4-0001` distance 0.3066; `planning-url-4-0008` distance 0.3102; `planning-url-4-0004` distance 0.3436 | The top chunks are Subash Shankar reviews and mention homework, limited resources, lecture confusion, and difficult grading/exams. |
| What course is Professor Tong Yi most frequently reviewed for? | `planning-url-5-0004` distance 0.2484; `planning-url-5-0007` distance 0.2782; `planning-url-5-0006` distance 0.2836 | The top chunks are Tong Yi reviews and show course variants such as `CS13500` and `CS135`, supporting the CSCI 135 answer. |

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

**Sample Gradio interaction transcript:**

User: `What positive traits do students mention about Roman Stelmach?`

Answer: The app summarized that students describe Roman Stelmach as nice, sweet, caring, helpful, generous with grading, and good at explaining material. The answer cited `[S1]` through `[S5]`.

Retrieved from: `Rate My Professors - Roman Stelmach`.

User: `What do students say about CSCI 135?`

Answer: `I don't have enough information on that.`

Retrieved from: weak closest matches from unrelated or only partially related professor chunks, demonstrating the course-code normalization failure discussed above.

To run the evaluation helper:

```bash
python3 run_evaluation.py
```

To run deterministic unit tests for parsing, cleaning, and chunking:

```bash
python3 -m unittest tests.test_document_pipeline
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

## Stretch Feature: Metadata Filtering

The Gradio interface includes a `Professor/source filter` dropdown. This filters retrieval by the ChromaDB metadata field `source_name`, which is stored for every chunk. For example, selecting `Rate My Professors - Subash Shankar` and asking `What do students say about exams?` restricts retrieved chunks to Subash Shankar's page only. Without the filter, the same broad exam question may retrieve chunks from several professors. With the filter, the returned sources and retrieved chunks visibly come only from the selected professor.

This is implemented in `retrieval_pipeline.py` by passing a Chroma `where` filter:

```python
where = {"source_name": source_filter} if source_filter else None
collection.query(..., where=where)
```

## Stretch Feature: Conversational Memory

The Gradio app stores recent turns in `gr.State` and displays them in the `Conversation memory` box. Follow-up questions are contextualized with the previous user question and answer before retrieval. This lets the second query refer back to the first instead of starting from scratch.

Example multi-turn exchange:

1. User asks: `What positive traits do students mention about Roman Stelmach?`
2. The app answers with Roman Stelmach traits such as caring, sweet, generous grading, and helpful teaching, with Roman Stelmach sources.
3. User asks a follow-up: `What about his difficulty?`
4. The app uses the previous turn to understand that `his` refers to Roman Stelmach, retrieves Roman Stelmach chunks again, and answers using his difficulty information rather than switching to an unrelated professor.

This is implemented in `query.py` with `contextualize_question()`, which prepends the previous turn when the new question looks like a follow-up.
