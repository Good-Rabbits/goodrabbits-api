import os
import logging
from typing import Optional, List, Dict, Any
import anyio
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton Firestore client reference
_firestore_client: Optional[firestore.firestore.Client] = None


def init_firebase() -> firestore.firestore.Client:
    """
    Initializes the Firebase Admin SDK if not already initialized
    and returns a Firestore client instance.
    """
    global _firestore_client

    if not firebase_admin._apps:
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if cred_path and os.path.exists(cred_path):
            logger.info("Initializing Firebase Admin with service account key: %s", cred_path)
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            logger.info("Initializing Firebase Admin with Application Default Credentials.")
            firebase_admin.initialize_app()

    if _firestore_client is None:
        _firestore_client = firestore.client()

    return _firestore_client


def get_firestore() -> firestore.firestore.Client:
    """
    Returns the initialized Firestore client.
    """
    global _firestore_client
    if _firestore_client is None:
        return init_firebase()
    return _firestore_client


# Asynchronous Firestore Wrappers (Non-blocking I/O)
# Running sync Firestore I/O operations in a thread pool prevents
# blocking FastAPI's asyncio event loop.

async def async_get_user_blocklist(uid: str) -> List[str]:
    """
    Fetches the user's blocked sites list from Firestore asynchronously.
    Reads from the document: users/{uid} (field: blocklist).
    """
    db = get_firestore()

    def _sync_fetch() -> List[str]:
        doc_ref = db.collection("users").document(uid)
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            return data.get("blocklist", [])
        return []

    return await anyio.to_thread.run_sync(_sync_fetch)


async def async_update_user_rewards(uid: str, xp_earned: int, carrots_earned: int, session_minutes: int) -> Dict[str, Any]:
    """
    Updates the user's gamified profile in Firestore atomically using Increment.
    Sets default values if document does not exist using merge=True.
    """
    db = get_firestore()

    def _sync_update() -> Dict[str, Any]:
        user_ref = db.collection("users").document(uid)
        
        # Atomic increments guarantee no race conditions across concurrent sessions
        update_data = {
            "xp": firestore.Increment(xp_earned),
            "carrots": firestore.Increment(carrots_earned),
            "total_focus_minutes": firestore.Increment(session_minutes),
            "last_focus_completed_at": firestore.SERVER_TIMESTAMP,
        }
        
        user_ref.set(update_data, merge=True)

        # Retrieve the updated state for API response and client synchronization
        updated_snap = user_ref.get()
        return updated_snap.to_dict() if updated_snap.exists else {}

    return await anyio.to_thread.run_sync(_sync_update)
