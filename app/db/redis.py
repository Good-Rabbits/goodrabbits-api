from typing import AsyncGenerator, Optional
import redis.asyncio as aioredis
from app.core.config import settings

# Global reference to the async Redis client connection pool
redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """
    Initializes the asynchronous Redis connection pool.
    Called on FastAPI application startup.
    """
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def close_redis() -> None:
    """
    Closes the Redis connection pool gracefully.
    Called on FastAPI application shutdown.
    """
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """
    FastAPI dependency yielding an active async Redis client instance.
    """
    if redis_client is None:
        await init_redis()
    yield redis_client
