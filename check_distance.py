from app.query import retrieve_chunks

results = retrieve_chunks("What technologies were used to build NewsLink?")
for r in results:
    print("distance:", r["distance"])
    print("text:", r["text"][:300])
    print("---")