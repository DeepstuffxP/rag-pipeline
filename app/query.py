import os
from dotenv import load_dotenv
from groq import Groq
from app.ingest import collection

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def retrieve_chunks(question: str, top_k: int = 4, doc_id: str = None):
    query_kwargs = {"query_texts": [question], "n_results": top_k}
    if doc_id:
        query_kwargs["where"] = {"doc_id": doc_id}

    results = collection.query(**query_kwargs)
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "text": chunks[i],
            "doc_id": metadatas[i]["doc_id"],
            "chunk_index": metadatas[i]["chunk_index"],
            "page": metadatas[i].get("page", "unknown"),
            "distance": distances[i],
        }
        for i in range(len(chunks))
    ]

def answer_question(question: str, top_k: int = 4, doc_id: str = None):
    retrieved = retrieve_chunks(question, top_k, doc_id)

    if not retrieved:
        return {"answer": "No relevant documents found.", "sources": []}

    context = "\n\n".join(
        f"[{r['doc_id']}, page {r['page']}]: {r['text']}" for r in retrieved
    )

    prompt = f"""Answer the question using only the context below. If the answer isn't in the context, say you don't know. Cite sources exactly like [document_name, page N] where relevant, matching the labels shown in the context.

Context:
{context}

Question: {question}"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": [
            {
                "doc_id": r["doc_id"],
                "chunk_index": r["chunk_index"],
                "page": r["page"],
                "relevance_score": round(1 - r["distance"], 3),
            }
            for r in retrieved
        ],
    }