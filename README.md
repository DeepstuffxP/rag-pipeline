# Reading Room — RAG Pipeline for PDF Q&A

Upload a PDF, then ask it questions in plain English. Answers cite the exact page they came from, so you can actually verify them instead of just trusting whatever the model says.

Built to go a level deeper than a basic RAG tutorial — async ingestion (so uploading a big PDF doesn't block anything), multi-document support, page-level citations, and a fully containerized deployment on EC2.

## How it works

1. You upload a PDF (`POST /documents`). The API saves it and hands off to a background worker immediately — you get a response in milliseconds, not whenever the AI finishes reading.
2. A separate ARQ worker picks up the job: extracts text page by page, splits it into overlapping chunks, embeds each chunk, and stores it in Chroma with metadata (which document, which page).
3. You ask a question (`POST /query`). The question gets embedded the same way, Chroma finds the most semantically similar chunks, and those get stuffed into a prompt for Groq — along with an instruction to cite sources and say "I don't know" instead of making things up.
4. You get back an answer plus a list of sources, each with a page number and a similarity score, so you can trace exactly where the answer came from.

```
Client -> POST /documents -> saved to disk -> job pushed to Redis
                                                    |
                                    ARQ worker: extract -> chunk -> embed -> store in Chroma
Client -> GET /documents/{id} -> poll for ingestion status

Client -> POST /query -> embed question -> search Chroma -> Groq (with context) -> cited answer
```

## Stack

- FastAPI
- Chroma (running as its own server, not embedded — more on why below)
- Redis + ARQ for the background ingestion queue
- sentence-transformers (`all-MiniLM-L6-v2`) for embeddings, runs locally
- Groq API (`openai/gpt-oss-20b`) for the actual answers
- Docker Compose for running all four services together
- Deployed on EC2

## Running it locally

**Without Docker:**
```bash
pip install -r requirements.txt
cp .env.example .env   # add your Groq API key
chroma run --path ./data/chroma_db --port 8001   # terminal 1
uvicorn app.main:app --reload                    # terminal 2
arq app.worker.WorkerSettings                    # terminal 3
```
Then open `http://localhost:8000/`

**With Docker:**
```bash
docker compose up --build
```
Same URL, no juggling three terminals.

## A few things worth knowing

**Chroma runs as its own server, not embedded.** I started with `PersistentClient` (Chroma opens local files directly), which worked fine until I had two processes — the API and the worker — both writing to it at once. Got a cryptic "nothing found on disk" error that only showed up under real concurrent use. Turns out embedded Chroma isn't safe for that, same reason you don't have two processes directly opening the same SQLite file. Fixed by running Chroma as a standalone server both processes connect to over HTTP.

**Chunking is currently pretty naive.** It splits by raw word count with some overlap, not by section or sentence boundaries. I found a real case where this hurt: asking about a document's tech stack retrieved the cover page instead of the actual "Technologies Used" section, because the chunker doesn't know where one topic ends and another begins. The fix would be smarter chunking, plus hybrid search (keyword + vector) with a reranking step — noted as the next real improvement, not done yet.

**No auth yet.** Anyone who can reach the API can query anything that's been uploaded. Deliberately deferred to get the actual RAG mechanics solid first — but unlike a lot of side projects, this one has a real reason to eventually need it (documents belonging to different people), not just "auth exists in real apps."

**Storage is local to the instance for now.** Uploaded PDFs and the vector store both live on disk, not S3 — fine for a single instance, but it means the data doesn't survive if the EC2 instance gets terminated (found this out the hard way after a key-pair mishap forced a fresh instance).

## What I'd do next

- Better chunking (section/sentence-aware, not just word count)
- Hybrid search + reranking for better retrieval on specific factual questions
- S3 for file storage instead of local disk
- Auth + per-user document isolation