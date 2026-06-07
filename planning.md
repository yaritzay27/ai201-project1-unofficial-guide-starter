# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
My Unofficial Guide focuses on Hunter College Computer Science and Mathematics course experiences, professor reviews, and student advice. This knowledge is valuable because students often rely on scattered sources such as Reddit discussions, Rate My Professors reviews, and word-of-mouth recommendations when choosing classes. By bringing these sources together into a searchable system, students can quickly find information about workload, teaching styles, course difficulty, and academic success strategies.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Hunter College CS Department Professors | All hunter college professor ratings in the Computer Science department | https://www.ratemyprofessors.com/search/professors/226?q=*&did=11 |
| 2 | Hunter College Mathematics Department Professors | All hunter college professor ratings in the Mathematics department | https://www.ratemyprofessors.com/search/professors/226?q=*&did=38 |
| 3 | Rate My Professors - CS Professor 1 | Raman Kannan, Professor in the Computer Science department at Hunter College | https://www.ratemyprofessors.com/professor/2448249 |
| 4 | Rate My Professors - CS Professor 2 | Subash Shankar, Professor in the Computer Science department at Hunter College | https://www.ratemyprofessors.com/professor/257190 |
| 5 | Rate My Professors - CS Professor 3 | Tong Yi, Professor in the Computer Science department at Hunter College, teaches CSCI 135 | https://www.ratemyprofessors.com/professor/2634841 |
| 6 | Rate My Professors - CS Professor 4 | Justin Tojeira, Professor in the Computer Science department at Hunter College, teaches CSCI 265, 235, 335| https://www.ratemyprofessors.com/professor/1660967 |
| 7 | Rate My Professors - Math Professor 1 | Roman Stelmach, Professor in the Mathematics department at Hunter College | https://www.ratemyprofessors.com/professor/535583|
| 8 | Rate My Professors - Math Professor 2 | Robert Thompson, Professor in the Mathematics department at Hunter College | https://www.ratemyprofessors.com/professor/421746 |
| 9 | Rate My Professors - Math Professor 3 | Ilya Kapovich, Professor in the Mathematics department at Hunter College | https://www.ratemyprofessors.com/professor/2408145 |
| 10 | Rate My Professors - Math Professor 4 | Yuna Won, Professor in the Philosophy department at Hunter College, teaches CSCI/MATH/PHILO 275 - Symbolic Logic | https://www.ratemyprofessors.com/professor/2951672 |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** One review per chunk whenever possible. For longer reviews or discussion posts, split by paragraph with a maximum size of approximately 400–500 characters.

**Overlap:** 50–100 characters between adjacent chunks for longer posts.

**Reasoning:** Most of my documents are short professor reviews where a single review contains a complete opinion or experience. Keeping each review intact preserves context and allows the retrieval system to return individual student experiences accurately. For longer department pages, paragraph-based chunking with overlap helps ensure important information is not split across chunk boundaries while still keeping chunks focused on a single topic.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** all-MiniLM-L6-v2 (Sentence Transformers)

**Top-k:** 5

**Production tradeoff reflection:** If cost and latency were not concerns, I would consider using a larger embedding model with stronger semantic understanding and support for longer context windows. Larger models may improve retrieval accuracy for nuanced student reviews and complex questions, but they require more computational resources and slower response times.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What rating does Professor Roman Stelmach have on Rate My Professors? | 4.9/5 |
| 2 | What complaints appear most often in reviews for Professor Subash Shankar? | Heavy homework and difficult exams |
| 3 | What course is Professor Tong Yi most frequently reviewed for? | CSCI 135 |
| 4 | What positive trait is most commonly mentioned about Professor Yuna Won? | Clear explanations |
| 5 | What negative trait is most commonly mentioned about Professor Justin Tojeira? | Slow grading |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Student reviews may contain subjective opinions, inconsistent information, or conflicting experiences that make retrieval more difficult.

2. Important information may be spread across multiple comments or reviews, making it harder for retrieval to return complete answers from a single chunk.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

Source Documents 
(Rate My Professors Reviews, Rate My professor Main Page for Mathematics & CS Professors) 
| 
v 
Document Ingestion (Python + BeautifulSoup) 
| 
v 
Chunking (Custom chunk_text() Function) 
| 
v 
Embeddings (sentence-transformers all-MiniLM-L6-v2) 
| 
v 
Vector Store (ChromaDB) 
| 
v Retrieval (Top-k Semantic Search) 
| 
v 
Generation (Groq API llama-3.3-70b-versatile) 
| 
v 
Grounded Response with Source Citations

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
I will use ChatGPT and Codex to help implement document ingestion and chunking functions. I will provide my Domain, Documents, and Chunking Strategy sections from this planning document and ask the AI tools to generate Python code that loads professor review pages, cleans unnecessary content, and creates chunks according to my specified strategy. I will verify the output by manually inspecting chunk boundaries and confirming that individual reviews remain intact whenever possible.

**Milestone 4 — Embedding and retrieval:**
I will use ChatGPT and Codex to help implement the embedding and retrieval pipeline. I will provide my Retrieval Approach section and ask the AI tools to generate code that creates embeddings using all-MiniLM-L6-v2, stores them in ChromaDB, and retrieves the top-k most relevant chunks for a query. I will verify the implementation by running test queries and checking whether the returned chunks are relevant to the user's question.

**Milestone 5 — Generation and interface:**
I will use ChatGPT and Codex to help implement the retrieval-augmented generation workflow and command-line interface. I will provide the Architecture diagram, Evaluation Plan, and project requirements and ask the AI tools to generate code that sends retrieved context to the Groq LLM while requiring source attribution in every response. I will verify the implementation by running my evaluation questions and comparing the generated answers against the expected answers listed in my Evaluation Plan. 