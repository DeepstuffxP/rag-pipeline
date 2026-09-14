import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from arq import create_pool
from arq.connections import RedisSettings

from app.ingest import collection
from app.query import answer_question
from app.models import QueryRequest, QueryResponse, DocumentOut

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
     app.state.redis = await create_pool(RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    ))
     yield
     await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

def sanitize_doc_id(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name).lower()

@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    doc_id = sanitize_doc_id(file.filename)
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    key = f"doc:{doc_id}"
    await app.state.redis.hset(key, "status", "processing")
    await app.state.redis.hset(key, "num_chunks", 0)
    await app.state.redis.hset(key, "error", "")
    await app.state.redis.hset(key, "filename", file.filename)

    await app.state.redis.enqueue_job("process_document", doc_id, file_path)

    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}

@app.get("/documents/{doc_id}")
async def get_document_status(doc_id: str):
    data = await app.state.redis.hgetall(f"doc:{doc_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "doc_id": doc_id,
        "filename": data.get("filename", ""),
        "status": data.get("status", "unknown"),
        "num_chunks": int(data.get("num_chunks", 0)),
        "error": data.get("error") or None,
    }

@app.get("/documents", response_model=list[DocumentOut])
async def list_documents():
    all_data = collection.get()
    doc_map = {}
    for metadata in all_data["metadatas"]:
        doc_id = metadata["doc_id"]
        doc_map[doc_id] = doc_map.get(doc_id, 0) + 1

    return [
        DocumentOut(doc_id=doc_id, filename=f"{doc_id}.pdf", num_chunks=count)
        for doc_id, count in doc_map.items()
    ]

@app.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest):
    result = answer_question(payload.question, top_k=payload.top_k, doc_id=payload.doc_id)
    return QueryResponse(answer=result["answer"], sources=result["sources"])


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")