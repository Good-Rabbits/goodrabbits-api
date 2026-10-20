import json
import logging
from typing import List, Tuple
import redis.asyncio as aioredis
from app.core.config import settings
from app.db.firebase import async_get_user_blocklist

logger = logging.getLogger(__name__)


class BlocklistService:
    """
    Service responsible for serving blocked domain lists.
    
    FIRESTORE SHIELD PATTERN:
    Browser extensions and background processes check blocklists with high frequency
    (e.g., on tab creation, domain changes, or periodic syncs). Reading directly from
    Firestore on every request would quickly exhaust Firestore quotas and increase latency.
    
    Flow:
    1. Check Redis for 'blocklist:{uid}'.
    2. Cache Hit -> Return immediately from Redis (ultra-low latency, 0 Firestore cost).
    3. Cache Miss -> Fallback to Firestore, serialize and store in Redis with a 24-hour TTL,
       and return the list to the caller.
    """

    @staticmethod
    def get_cache_key(uid: str) -> str:
        """Generates a standardized Redis key for the user's blocklist."""
        return f"blocklist:{uid}"

    @classmethod
    async def get_user_blocklist(cls, uid: str, redis: aioredis.Redis) -> Tuple[List[str], bool]:
        """
        Retrieves the blocked domains for a user.
        
        Returns:
            Tuple[List[str], bool]: (domain_list, from_cache_flag)
        """
        cache_key = cls.get_cache_key(uid)

        # 1. Attempt reading from Redis Shield
        try:
            cached_data = await redis.get(cache_key)
            if cached_data is not None:
                domains = json.loads(cached_data)
                logger.debug("Redis cache HIT for blocklist (uid: %s)", uid)
                return domains, True
        except Exception as err:
            logger.error("Failed to read from Redis cache for uid %s: %s", uid, str(err))

        # 2. Cache Miss: Fallback to Firestore persistent store
        logger.info("Redis cache MISS for blocklist (uid: %s). Fetching from Firestore...", uid)
        domains = await async_get_user_blocklist(uid)

        # 3. Cache the result in Redis with a 24-hour TTL
        try:
            serialized = json.dumps(domains)
            await redis.set(
                name=cache_key,
                value=serialized,
                ex=settings.BLOCKLIST_CACHE_TTL_SECONDS
            )
            logger.debug("Cached blocklist in Redis with %ds TTL (uid: %s)", settings.BLOCKLIST_CACHE_TTL_SECONDS, uid)
        except Exception as err:
            logger.error("Failed to write blocklist to Redis cache for uid %s: %s", uid, str(err))

        return domains, False
