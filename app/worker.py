from arq.connections import RedisSettings
from app.ingest import ingest_pdf
import os

async def process_document(ctx, doc_id: str, file_path: str):
    redis = ctx["redis"]
    key = f"doc:{doc_id}"

    try:
        num_chunks = ingest_pdf(file_path, doc_id)
        await redis.hset(key, "status", "completed")
        await redis.hset(key, "num_chunks", num_chunks)
        await redis.hset(key, "error", "")
    except Exception as e:
        await redis.hset(key, "status", "failed")
        await redis.hset(key, "num_chunks", 0)
        await redis.hset(key, "error", str(e))

class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )