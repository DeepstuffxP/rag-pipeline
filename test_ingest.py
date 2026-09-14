from app.ingest import ingest_pdf, collection

# Point this at any PDF you have lying around
pdf_path = "uploads/test.pdf"
doc_id = "test_doc_1"

num_chunks = ingest_pdf(pdf_path, doc_id)
print(f"Ingested {num_chunks} chunks from {pdf_path}")

# Confirm it's actually in Chroma
result = collection.get(where={"doc_id": doc_id})
print(f"Chroma has {len(result['ids'])} chunks stored for this doc")
print("First chunk preview:", result["documents"][0][:200])