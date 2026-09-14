from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 4
    doc_id: Optional[str] = None

class SourceOut(BaseModel):
    doc_id: str
    chunk_index: int
    page: int 
    relevance_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceOut]

class DocumentOut(BaseModel):
    doc_id: str
    filename: str
    num_chunks: int