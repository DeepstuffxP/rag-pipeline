import os
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

chroma_client = chromadb.HttpClient(
    host=os.getenv("CHROMA_HOST", "localhost"),
    port=int(os.getenv("CHROMA_PORT", 8001)),
)

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = chroma_client.get_or_create_collection(
    name="documents",
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"},
)

def extract_pages(pdf_path: str) -> list[tuple[int, str]]:
    reader = PdfReader(pdf_path)
    return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

def ingest_pdf(pdf_path: str, doc_id: str):
    pages = extract_pages(pdf_path)

    all_chunks = []
    all_metadatas = []
    chunk_counter = 0

    for page_num, page_text in pages:
        if not page_text.strip():
            continue
        page_chunks = chunk_text(page_text)
        for chunk in page_chunks:
            all_chunks.append(chunk)
            all_metadatas.append({
                "doc_id": doc_id,
                "chunk_index": chunk_counter,
                "page": page_num,
            })
            chunk_counter += 1

    if not all_chunks:
        return 0

    collection.add(
        documents=all_chunks,
        ids=[f"{doc_id}_chunk_{i}" for i in range(len(all_chunks))],
        metadatas=all_metadatas,
    )
    return len(all_chunks)