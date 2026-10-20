from fastapi import APIRouter
from app.api.v1.endpoints import blocklist, focus

api_router = APIRouter()

# Register endpoint routers under API v1
api_router.include_router(blocklist.router)
api_router.include_router(focus.router)
