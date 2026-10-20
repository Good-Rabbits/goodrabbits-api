import logging
from fastapi import APIRouter, Depends, status
import redis.asyncio as aioredis

from app.core.security import get_current_user_uid
from app.db.redis import get_redis
from app.schemas.focus import FocusStartResponse, FocusEndResponse
from app.services.focus_service import FocusService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/focus", tags=["Focus Session"])


@router.post(
    "/start",
    response_model=FocusStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a focus session",
    description="Registers the start of a focus session by recording server timestamp in Redis with a 4-hour TTL."
)
async def start_focus_session(
    uid: str = Depends(get_current_user_uid),
    redis: aioredis.Redis = Depends(get_redis)
) -> FocusStartResponse:
    """
    Initiates distraction blocking and records the server-side start time in Redis.
    """
    return await FocusService.start_session(uid=uid, redis=redis)


@router.post(
    "/end",
    response_model=FocusEndResponse,
    status_code=status.HTTP_200_OK,
    summary="End an active focus session",
    description="Calculates session duration server-side, awards XP & Carrots, updates Firestore, and purges Redis key."
)
async def end_focus_session(
    uid: str = Depends(get_current_user_uid),
    redis: aioredis.Redis = Depends(get_redis)
) -> FocusEndResponse:
    """
    Calculates duration and grants gamification rewards based purely on server-side state.
    Anti-cheat guarantees no client-side values are trusted for rewards.
    """
    return await FocusService.end_session(uid=uid, redis=redis)
