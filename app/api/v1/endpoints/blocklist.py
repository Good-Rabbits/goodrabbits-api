import logging
from fastapi import APIRouter, Depends, status
import redis.asyncio as aioredis

from app.core.security import get_current_user_uid
from app.db.redis import get_redis
from app.schemas.blocklist import BlocklistResponse
from app.services.blocklist_service import BlocklistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blocklist", tags=["Blocklist"])


@router.get(
    "",
    response_model=BlocklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user blocked domains list",
    description="Ultra-fast route reading from Redis cache shield. Falls back to Firestore on cache miss with 24h TTL."
)
async def get_blocklist(
    uid: str = Depends(get_current_user_uid),
    redis: aioredis.Redis = Depends(get_redis)
) -> BlocklistResponse:
    """
    Returns the user's blocked domains.
    Guaranteed ultra-low latency via the Redis Shield.
    """
    domains, from_cache = await BlocklistService.get_user_blocklist(uid=uid, redis=redis)
    return BlocklistResponse(domains=domains, from_cache=from_cache)
