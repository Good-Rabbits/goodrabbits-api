import logging
from typing import Optional
import anyio
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)

# Security scheme that extracts the Bearer token from the Authorization header
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user_uid(
    credentials_auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> str:
    """
    FastAPI dependency enforcing Zero-Trust authentication.
    Intercepts the Authorization: Bearer <TOKEN> header, validates the Firebase Auth JWT
    cryptographic signature using firebase_admin.auth.verify_id_token, and extracts the user's uid.
    
    Rejects any unauthenticated or invalid request with HTTP 401 Unauthorized.
    """
    if credentials_auth is None or not credentials_auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <TOKEN>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials_auth.credentials

    try:
        # Offload JWT verification to thread pool to prevent blocking the async event loop
        decoded_token = await anyio.to_thread.run_sync(
            auth.verify_id_token,
            token,
            True  # Check if token is revoked
        )
        uid = decoded_token.get("uid")

        if not uid:
            logger.warning("Decoded token does not contain a valid uid.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing user identifier (uid).",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return uid

    except auth.ExpiredIdTokenError:
        logger.warning("Firebase ID token has expired.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.RevokedIdTokenError:
        logger.warning("Firebase ID token has been revoked.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (auth.InvalidIdTokenError, ValueError) as err:
        logger.warning("Invalid Firebase ID token: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature or structure.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except FirebaseError as err:
        logger.error("Firebase Auth verification failed unexpectedly: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication verification failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as err:
        logger.critical("Unexpected error during token verification: %s", str(err), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
