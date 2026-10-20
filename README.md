# GoodRabbits API 🐰⚡

**GoodRabbits API** is a high-performance asynchronous backend built with **FastAPI**, **Firebase Admin SDK**, and **Redis Cloud** for the "GoodRabbits" application and Chrome extension (a gamified productivity RPG with an integrated distraction blocker).

---

## 🏗️ Architecture & Design Principles

### 1. Zero-Trust Security & Mandatory Auth
- **Strict CORS**: Only trusted origins (including your authorized Chrome extension prefix `chrome-extension://<EXTENSION_ID>`) are accepted via `CORSMiddleware`.
- **JWT Verification**: All business routes require the `get_current_user_uid` dependency (`app.core.security`), which cryptographically verifies Firebase tokens with `firebase_admin.auth.verify_id_token` and extracts the authenticated user `uid`. Expired, revoked, or invalid tokens return `401 Unauthorized`.

### 2. Firestore Shield (Redis Cache Layer)
- High-frequency queries (such as the extension checking the `blocklist` on every browser navigation) query Redis first (`blocklist:{uid}`).
- **Cache Hit**: Instant in-memory response (< 5ms) with zero read quota cost on Firestore.
- **Cache Miss**: The blocklist is fetched from Firestore, stored in Redis with a **24-hour TTL**, and returned to the client.

### 3. Server-Side Anti-Cheat & Game Economy
- The client **NEVER** supplies the earned XP or coins (Carrots).
- `/api/v1/focus/start`: The server records the exact UTC start timestamp in Redis (`focus:session:{uid}`) with a **4-hour TTL** (preventing orphaned keys if the user abruptly closes the browser).
- `/api/v1/focus/end`: The server retrieves the start timestamp from Redis, calculates elapsed minutes using the server clock, applies reward formulas (10 XP / min and 5 Carrots / min), and updates Firestore atomically using `firestore.Increment()`. The Redis session key is purged immediately.

---

## 📁 Project Structure

```text
goodrabbits-api/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── serviceAccountKey.example.json
└── app/
    ├── __init__.py
    ├── main.py                     # FastAPI entry point, lifespan events & CORS
    ├── core/
    │   ├── __init__.py
    │   ├── config.py               # Pydantic Settings & environment variables
    │   └── security.py             # Firebase Auth JWT verification dependency
    ├── db/
    │   ├── __init__.py
    │   ├── firebase.py             # Firebase Admin initialization & Firestore async wrappers
    │   └── redis.py                # Asynchronous Redis connection (redis.asyncio)
    ├── schemas/
    │   ├── __init__.py
    │   ├── blocklist.py            # Pydantic models for Blocklist
    │   └── focus.py                # Pydantic models for Focus Sessions
    ├── services/
    │   ├── __init__.py
    │   ├── blocklist_service.py    # Business logic & Firestore Shield cache layer
    │   └── focus_service.py        # Anti-cheat logic, time delta calculation & rewards
    └── api/
        ├── __init__.py
        └── v1/
            ├── __init__.py
            ├── api.py              # v1 route aggregator
            └── endpoints/
                ├── __init__.py
                ├── blocklist.py    # GET /api/v1/blocklist route
                └── focus.py        # POST /api/v1/focus/start and end routes
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Redis instance (Redis Cloud, Upstash, or local instance on port 6379)
- Firebase Project with Authentication and Firestore enabled

### 1. Create a virtual environment & install dependencies

```bash
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Update the values in `.env`:
- `ALLOWED_ORIGINS`: Add your Chrome Extension ID (`chrome-extension://<YOUR_EXTENSION_ID>`).
- `REDIS_URL`: Redis connection string (e.g., `redis://default:<password>@<host>:<port>`).
- `FIREBASE_CREDENTIALS_PATH`: Path to your `serviceAccountKey.json` downloaded from the Firebase Console.

### 3. Run the development server

```bash
uvicorn app.main:app --reload --port 8000
```

- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📡 MVP Endpoints

### 1. `GET /api/v1/blocklist`
Retrieves the list of blocked domains for the authenticated user via Redis Shield.

**Headers:**
```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

**Response:**
```json
{
  "domains": ["youtube.com", "instagram.com", "tiktok.com", "twitter.com"],
  "from_cache": true
}
```

---

### 2. `POST /api/v1/focus/start`
Starts a focus session and stores the start timestamp in Redis with a 4-hour expiration.

**Headers:**
```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

**Response:**
```json
{
  "status": "success",
  "message": "Focus session successfully started. Distraction blocker is active.",
  "started_at": "2026-10-20T13:00:00Z",
  "session_ttl_seconds": 14400
}
```

---

### 3. `POST /api/v1/focus/end`
Ends the focus session. Calculates elapsed duration using the server clock, awards XP and Carrots, updates Firestore atomically via `Increment`, and clears the active session from Redis.

**Headers:**
```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

**Response:**
```json
{
  "status": "success",
  "focused_minutes": 25,
  "xp_earned": 250,
  "carrots_earned": 125,
  "total_xp": 1450,
  "total_carrots": 725,
  "message": "Awesome work! You completed 25 focus minute(s) and earned 250 XP & 125 Carrots!"
}
```
