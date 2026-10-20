import time
import logging
from datetime import datetime, timezone
import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.firebase import async_update_user_rewards
from app.schemas.focus import FocusStartResponse, FocusEndResponse

logger = logging.getLogger(__name__)


class FocusService:
    """
    Service responsible for managing focus sessions and gamification rewards.

    ANTI-CHEAT & DISTRIBUTED STATE PATTERN:
    1. Zero Trust Client Input: The client never passes elapsed time, XP, or coin numbers.
       All reward values are derived server-side from timestamps stored securely in Redis.
    2. Redis Session Shield: The session start timestamp is saved with an automatic TTL of 4 hours
       (configurable). This guarantees orphan keys (e.g. browser crash, lost connection) expire
       naturally without manual cleanup jobs.
    3. Firestore Atomic Updates: When a session completes, rewards are calculated from server delta
       and committed via Firestore atomic `Increment` operators, avoiding race conditions.
    """

    @staticmethod
    def get_session_key(uid: str) -> str:
        """Generates the Redis key storing an active focus session for a user."""
        return f"focus:session:{uid}"

    @classmethod
    async def start_session(cls, uid: str, redis: aioredis.Redis) -> FocusStartResponse:
        """
        Initiates a focus session by recording the current server timestamp in Redis.
        """
        session_key = cls.get_session_key(uid)
        now_utc = datetime.now(timezone.utc)
        start_timestamp = now_utc.timestamp()

        # TTL in seconds (4 hours = 14400s) to prevent orphan active sessions
        ttl_seconds = settings.MAX_SESSION_HOURS * 3600

        # Save float timestamp into Redis with expiration
        await redis.set(
            name=session_key,
            value=str(start_timestamp),
            ex=ttl_seconds
        )

        logger.info("Focus session started for uid %s at %s (TTL: %ds)", uid, now_utc.isoformat(), ttl_seconds)

        return FocusStartResponse(
            status="success",
            message="Focus session successfully started. Distraction blocker is active.",
            started_at=now_utc,
            session_ttl_seconds=ttl_seconds
        )

    @classmethod
    async def end_session(cls, uid: str, redis: aioredis.Redis) -> FocusEndResponse:
        """
        Concludes an active focus session:
        1. Validates session existence in Redis.
        2. Calculates elapsed time server-side (anti-cheat).
        3. Computes XP and Carrots earned.
        4. Atomically updates the user's document in Firestore.
        5. Deletes the active session key from Redis.
        """
        session_key = cls.get_session_key(uid)

        # 1. Fetch start timestamp from Redis
        raw_start_time = await redis.get(session_key)
        if raw_start_time is None:
            logger.warning("Attempted to end non-existent or expired focus session for uid %s", uid)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active focus session found or session has expired (max 4 hours limit)."
            )

        try:
            start_timestamp = float(raw_start_time)
        except ValueError:
            await redis.delete(session_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Corrupted session timestamp in cache. Session reset."
            )

        # 2. Server-side Anti-Cheat Delta Calculation
        current_timestamp = datetime.now(timezone.utc).timestamp()
        elapsed_seconds = current_timestamp - start_timestamp

        # Guard against clock skew or anomalous negative duration
        if elapsed_seconds < 0:
            elapsed_seconds = 0

        # Check if the user focused for the minimum required threshold (e.g., 60 seconds)
        if elapsed_seconds < settings.MINIMUM_FOCUS_SECONDS:
            # Clean up the session key without awarding game economy rewards
            await redis.delete(session_key)
            logger.info(
                "Focus session ended prematurely for uid %s (elapsed: %.1fs < min: %ds). No rewards granted.",
                uid, elapsed_seconds, settings.MINIMUM_FOCUS_SECONDS
            )
            return FocusEndResponse(
                status="success",
                focused_minutes=0,
                xp_earned=0,
                carrots_earned=0,
                total_xp=0,
                total_carrots=0,
                message="Session was shorter than the 1-minute minimum requirement. Keep trying to earn rewards!"
            )

        # 3. Calculate Rewards Server-Side
        focused_minutes = int(elapsed_seconds // 60)
        xp_earned = focused_minutes * settings.XP_PER_MINUTE
        carrots_earned = focused_minutes * settings.CARROTS_PER_MINUTE

        logger.info(
            "Focus session ended for uid %s: %d minutes completed. Awarding %d XP and %d Carrots.",
            uid, focused_minutes, xp_earned, carrots_earned
        )

        # 4. Atomic update to Firestore
        updated_profile = await async_update_user_rewards(
            uid=uid,
            xp_earned=xp_earned,
            carrots_earned=carrots_earned,
            session_minutes=focused_minutes
        )

        # 5. Clear Redis session key
        await redis.delete(session_key)

        return FocusEndResponse(
            status="success",
            focused_minutes=focused_minutes,
            xp_earned=xp_earned,
            carrots_earned=carrots_earned,
            total_xp=int(updated_profile.get("xp", xp_earned)),
            total_carrots=int(updated_profile.get("carrots", carrots_earned)),
            message=f"Awesome work! You completed {focused_minutes} focus minute(s) and earned {xp_earned} XP & {carrots_earned} Carrots!"
        )
