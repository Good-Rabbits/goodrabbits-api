import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.firebase import init_firebase
from app.db.redis import init_redis, close_redis

# Configure standard application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("goodrabbits-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes infrastructure clients (Redis connection pool, Firebase Admin SDK) on startup,
    and safely closes open sockets and pools on shutdown.
    """
    logger.info("Starting up GoodRabbits API services...")
    
    # 1. Initialize Firebase Admin SDK & Firestore client
    try:
        init_firebase()
        logger.info("Firebase Admin initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin: %s", exc)

    # 2. Initialize Redis connection pool
    try:
        await init_redis()
        logger.info("Redis async client pool established at %s", settings.REDIS_URL)
    except Exception as exc:
        logger.error("Failed to connect to Redis: %s", exc)

    yield

    # Shutdown logic
    logger.info("Shutting down GoodRabbits API services...")
    await close_redis()
    logger.info("Redis connection pool closed.")


# Initialize FastAPI instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Strict CORS Middleware Configuration
# Zero Trust: Only explicitly allow specified origins, such as chrome extensions and official apps
logger.info("Configuring CORS with allowed origins: %s", settings.ALLOWED_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Service health check endpoint.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }
