from app.query import answer_question

result = answer_question("What is this report about?")
print("Answer:", result["answer"])
print("\nSources:")
for s in result["sources"]:
    print(f"  doc: {s['doc_id']}, chunk: {s['chunk_index']}, score: {s['relevance_score']}")