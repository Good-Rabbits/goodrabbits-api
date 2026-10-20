# GoodRabbits API 🐰⚡

O **GoodRabbits API** é o backend assíncrono de alto desempenho construído com **FastAPI**, **Firebase Admin SDK** e **Redis Cloud** para o aplicativo e extensão "GoodRabbits" (RPG de produtividade gamificado com bloqueador de distrações).

---

## 🏗️ Arquitetura & Diretrizes de Design

### 1. Zero-Trust Security & Mandatory Auth
- **CORS Estrito**: Apenas origens autorizadas (incluindo o prefixo `chrome-extension://<EXTENSION_ID>`) são aceitas via `CORSMiddleware`.
- **JWT Verification**: Todas as rotas de negócio exigem a dependência `get_current_user_uid` (`app.core.security`), que valida criptograficamente a assinatura do token Firebase com `firebase_admin.auth.verify_id_token` e extrai o `uid` do usuário. Tokens expirados, revogados ou inválidos recebem `401 Unauthorized`.

### 2. Firestore Shield (Redis Cache Layer)
- Consultas de altíssima frequência (como a leitura da `blocklist` pela extensão a cada navegação) batem primariamente no Redis (`blocklist:{uid}`).
- Em caso de **Cache Hit**, o retorno é imediato em memória (< 5ms), com custo 0 de leitura no Firestore.
- Em caso de **Cache Miss**, a lista é lida do Firestore, armazenada no Redis com TTL de **24 horas**, e devolvida ao cliente.

### 3. Anti-Cheat & Game Economy Server-Side
- O cliente **NUNCA** envia a quantidade de XP ou moedas (Carrots) conquistadas.
- `/api/v1/focus/start`: O servidor armazena o timestamp UTC exato de início no Redis (`focus:session:{uid}`) com TTL de **4 horas** (evitando chaves órfãs caso o usuário feche o navegador abruptamente).
- `/api/v1/focus/end`: O servidor resgata o timestamp do Redis, calcula a diferença em minutos decorridos, aplica as fórmulas de recompensa (10 XP / min e 5 Carrots / min), e atualiza o Firestore atomicamente usando `firestore.Increment()`. A chave do Redis é expurgada logo em seguida.

---

## 📁 Estrutura do Projeto

```text
goodrabbits-api/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── serviceAccountKey.example.json
└── app/
    ├── __init__.py
    ├── main.py                     # Entry point do FastAPI, Lifespan e CORS
    ├── core/
    │   ├── __init__.py
    │   ├── config.py               # Pydantic Settings & variáveis de ambiente
    │   └── security.py             # Dependência de autenticação Firebase Auth JWT
    ├── db/
    │   ├── __init__.py
    │   ├── firebase.py             # Inicialização do Firebase Admin e Firestore async wrappers
    │   └── redis.py                # Conexão assíncrona com Redis (redis.asyncio)
    ├── schemas/
    │   ├── __init__.py
    │   ├── blocklist.py            # Schemas Pydantic da Blocklist
    │   └── focus.py                # Schemas Pydantic das Sessões de Foco
    ├── services/
    │   ├── __init__.py
    │   ├── blocklist_service.py    # Lógica de negócio e Firestore Shield
    │   └── focus_service.py        # Lógica anti-cheat, delta de tempo e recompensas
    └── api/
        ├── __init__.py
        └── v1/
            ├── __init__.py
            ├── api.py              # Agregador de rotas v1
            └── endpoints/
                ├── __init__.py
                ├── blocklist.py    # Rota GET /api/v1/blocklist
                └── focus.py        # Rotas POST /api/v1/focus/start e end
```

---

## 🚀 Como Executar

### Pré-requisitos
- Python 3.10+
- Instância do Redis (Redis Cloud, Upstash ou local na porta 6379)
- Projeto Firebase com Authentication e Firestore ativos

### 1. Criar ambiente virtual e instalar dependências

```bash
python -m venv .venv
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

Ajuste as chaves no `.env`:
- `ALLOWED_ORIGINS`: Adicione o ID real da sua extensão do Chrome (`chrome-extension://<SEU_ID>`).
- `REDIS_URL`: URL de conexão com o Redis (ex: `redis://default:<password>@<host>:<port>`).
- `FIREBASE_CREDENTIALS_PATH`: Caminho para o seu arquivo `serviceAccountKey.json` baixado do Console do Firebase.

### 3. Rodar o servidor de desenvolvimento

```bash
uvicorn app.main:app --reload --port 8000
```

- Documentação Swagger UI interativa: [http://localhost:8000/docs](http://localhost:8000/docs)
- Documentação ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📡 Endpoints do MVP

### 1. `GET /api/v1/blocklist`
Recupera a lista de domínios bloqueados para o usuário autenticado via Redis Shield.

**Headers:**
```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

**Resposta:**
```json
{
  "domains": ["youtube.com", "instagram.com", "tiktok.com", "twitter.com"],
  "from_cache": true
}
```

---

### 2. `POST /api/v1/focus/start`
Inicia uma sessão de foco e registra a marca temporal no Redis com 4h de expiração.

**Headers:**
```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

**Resposta:**
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
Encerra a sessão de foco. Calcula a duração decorrida pelo relógio do servidor, concede XP e Carrots, persiste no Firestore via `Increment` e purga a sessão do Redis.

**Headers:**
```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

**Resposta:**
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
