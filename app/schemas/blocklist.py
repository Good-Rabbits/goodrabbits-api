from typing import List
from pydantic import BaseModel, Field


class BlocklistResponse(BaseModel):
    """
    Schema for user's distraction blocklist.
    """
    domains: List[str] = Field(
        default_factory=list,
        description="List of domain names blocked during focus sessions"
    )
    from_cache: bool = Field(
        default=False,
        description="Indicates whether the response was served from the Redis shield cache"
    )
