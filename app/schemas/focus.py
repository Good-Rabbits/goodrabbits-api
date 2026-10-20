from datetime import datetime
from pydantic import BaseModel, Field


class FocusStartResponse(BaseModel):
    """
    Response schema for session initiation.
    """
    status: str = Field(default="success", description="Status of the session start operation")
    message: str = Field(..., description="User feedback message")
    started_at: datetime = Field(..., description="Session start UTC timestamp")
    session_ttl_seconds: int = Field(..., description="TTL in seconds allocated for this session in Redis")


class FocusEndResponse(BaseModel):
    """
    Response schema for session completion and gamification rewards.
    All rewards are strictly computed server-side.
    """
    status: str = Field(default="success", description="Status of the session end operation")
    focused_minutes: int = Field(..., description="Validated total focused minutes")
    xp_earned: int = Field(..., description="Server-calculated XP earned")
    carrots_earned: int = Field(..., description="Server-calculated Carrots currency earned")
    total_xp: int = Field(..., description="Updated total user XP in Firestore")
    total_carrots: int = Field(..., description="Updated total user Carrots in Firestore")
    message: str = Field(..., description="Reward congratulatory or informative message")
