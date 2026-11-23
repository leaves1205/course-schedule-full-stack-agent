# Course Schedule Full Stack Agent

A campus course scheduling application with an authenticated AI assistant. Built with **Vue 3, FastAPI, LangChain, MCP, SQLAlchemy, and MySQL**.

The assistant queries the signed-in user's schedule through a JWT-bound MCP tool. Input guardrails review each request before the answering model runs, and the chat interface streams answers and tool activity over SSE.

## Features

- **Authentication:** registration, sign-in, JWT validation, profiles, avatars, and password changes. New passwords need at least 8 characters with a letter and a digit.
- **Abuse protection:** per-IP limits on sign-in and registration, per-account limits on chat (every message costs paid model calls), bounded chat input, and image-only avatar uploads with a byte limit.
- **Role-based management:** administrators manage users, courses, and class schedules; students view their own schedules and study plans.
- **Semester scheduling:** configure the first teaching Monday and semester length, then enter weekly meeting rows to generate dated class sessions in one transaction. Repeating the same request preserves existing sessions, including individual changes and cancellations.
- **Course assistant:** ask about dates, courses, class periods, and locations, including contextual follow-up questions.
- **Input guardrails:** classify requests as `allow`, `deny`, or `clarify`; unrelated requests receive a fixed response. Review failures stop processing.
- **Streaming chat:** display answer fragments, processing status, and tool activity; internal review output is excluded from the stream.
- **Short-term conversation memory:** restore chat history and drafts after page reloads or navigation within the same tab. Clear them on sign-out, session invalidation, or a new sign-in.
- **User isolation:** MCP resolves identity from the request JWT rather than a model-supplied user ID.
- **Course documents:** administrators upload `.txt`, `.md`, `.pdf`, and `.docx` materials, preview their extracted text, and manage saved documents. Uploads support multiple files with a 100 MiB limit per file; a failed upload rolls back the batch.
- **Blue and white interface:** responsive navigation, course and schedule tables, account forms, and a dashboard showing real schedule totals and recent study plans.
- **Tests and CI:** backend tests use isolated SQLite databases and mocked model responses; frontend tests cover chat restoration, logout cleanup, interrupted streams, role-based navigation, dashboard data, and failed requests. GitHub Actions runs lint, both test suites, the production build, and a Docker image build on every push and pull request.
- **Managed schema:** Alembic migrations create the schema and upgrade databases that predate them without touching existing rows. A test fails when a model changes without a migration.

The course assistant responds in English, including table headers and follow-up questions, while preserving course names and locations from the query results. The backend supplies today's weekday and the current week's date range. Language rules are configured in `backend/app/services/agent_service.py`; fixed guardrail messages are configured in `backend/app/hooks/course_guardrails.py`.

Document text extraction powers administrator previews. The assistant's data source is the authenticated schedule tool. Uploaded materials are stored locally in `backend/data/kb/`; the whole `backend/data/` directory is excluded from Git.

## Architecture

```mermaid
flowchart LR
    UI[Vue chat interface] -->|Authenticated HTTP request| API[FastAPI]
    API --> Review[Input review hook]
    Review -->|Allow| Agent[Course assistant]
    Review -->|Deny or clarify| Fixed[Fixed response]
    Agent -->|JWT-bound HTTP requests| MCP[FastMCP server]
    MCP --> DB[(MySQL)]
    Agent --> SSE[SSE response]
    Fixed --> SSE
    SSE --> UI
```

The MCP service uses stateless HTTP with JSON responses for short database queries. The browser chat uses a separate SSE connection to FastAPI.

## Requirements

- Python **3.12+**.
- Node.js **22.18+ in the 22.x line, or 24.12+**, as specified by `frontend/package.json`.
- MySQL **8.0+**.
- An LLM API key. The default provider is DeepSeek with `deepseek-flash`; alternative OpenAI-compatible providers must support tool calling and JSON output.

## Run with Docker

The quickest way to run everything (MySQL, API, MCP server and frontend) needs only Docker:

```bash
cp .env.example .env        # fill in the database passwords, JWT_SECRET_KEY and LLM_API_KEY
docker compose up --build
docker compose exec backend python manage.py create-admin YOUR_USERNAME
```

Open [http://localhost:8080](http://localhost:8080). The API and MCP server are not published to the host: the browser reaches the API through the frontend's nginx proxy, and only the API talks to MCP. Migrations run automatically when the API container starts.

The database password is placed in a connection URL, so generate URL-safe values (`openssl rand -hex 24`). The API container trusts forwarded headers because it is only reachable through nginx; do not publish its port directly, or clients could spoof the address that rate limiting is keyed on.

## Quick start

The commands below use macOS/Linux shell syntax. Run them from the repository root unless a step changes directories. This path runs each service on your machine for development; see [Run with Docker](#run-with-docker) for the one-command alternative.

### 1. Clone and configure

```bash
git clone https://github.com/leaves1205/course-schedule-full-stack-agent.git
cd course-schedule-full-stack-agent
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.development
```

Edit `backend/.env` with your own database credentials, JWT secret, and model API key:

```dotenv
DATABASE_URL=mysql+pymysql://your_mysql_user:replace-with-your-password@127.0.0.1:3306/course_schedule
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_EXPIRE_HOURS=24
JWT_ALGORITHM=HS256

MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_PATH=/mcp

LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=
LLM_MODEL_NAME=deepseek-flash
AGENT_RECURSION_LIMIT=15
```

The API refuses to start if `JWT_SECRET_KEY` is shorter than 32 characters or still the example placeholder. Generate a JWT secret locally and paste the result into `JWT_SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

`frontend/.env.development` only needs the backend address:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Frontend `VITE_*` values are browser-visible. Keep LLM keys, database passwords, and JWT secrets in the backend environment only. Real environment files are excluded from Git; only placeholder `.env.example` files are included.

### 2. Create the database

In MySQL, create a database matching `DATABASE_URL`:

```sql
CREATE DATABASE IF NOT EXISTS course_schedule
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

The configured MySQL account must have access to this database, and needs permission to create tables, alter `schedules` and create indexes. The tables themselves are created by the migrations in the next step.

### 3. Install backend dependencies and create the tables

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/alembic upgrade head
```

The schema is managed by [Alembic](https://alembic.sqlalchemy.org/) migrations in `backend/migrations/`; the API no longer creates tables when it starts. Run `alembic upgrade head` again after pulling changes that add a migration. It is safe to repeat.

A database that was created by an earlier version of this project (when the API created its own tables) can adopt migrations the same way: existing tables and rows are left alone, and only the missing semester-scheduling tables, columns and indexes are added. Parseable legacy periods such as `1-2` are backfilled into numeric bounds and unparseable text is preserved. `sql/backend.sql` is a reference snapshot of the final schema; the migrations are the source of truth.

To change a model, edit it and run `alembic revision -m "describe the change"`, then write the migration. The test suite compares a freshly migrated database with the models and fails if they differ.

### 4. Start FastAPI — terminal 1

From `backend/`:

```bash
./.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health check: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. Start MCP — terminal 2

From `backend/`:

```bash
./.venv/bin/python mcp_server.py
```

The MCP endpoint is `http://127.0.0.1:8001/mcp`. It is a protocol endpoint, not a browser UI. Keep this process running alongside FastAPI.

### 6. Start the frontend — terminal 3

From `frontend/`:

```bash
npm ci
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Register an account, then sign in.

On Windows, use `.venv\Scripts\python.exe` in place of `./.venv/bin/python` for the backend commands. Copy the example environment files using your shell's copy command.

## Set up an administrator and schedules

There are **no bundled login credentials or pre-created accounts**.

1. Register an account through the frontend. New accounts have the `student` role. Usernames are 3-50 letters, digits, dots, hyphens or underscores; passwords need at least 8 characters including a letter and a digit.
2. To make your account an administrator, run this from `backend/` (with Docker: `docker compose exec backend python manage.py ...`), substituting the username you registered:

   ```bash
   ./.venv/bin/python manage.py create-admin your_registered_username
   ```

   The command promotes an existing account without changing its password. For a username that does not exist yet it creates the administrator and prompts for a password (or reads `ADMIN_PASSWORD` for non-interactive use).

3. Sign out and sign in again to refresh the profile shown by the frontend.
4. Use the administrator pages to create courses and assign schedules to registered users.
5. Sign in as a student and query the assigned schedule in the course assistant.

## Generate a semester schedule

1. As an administrator, open **Semesters** and add a name, the Monday of teaching week 1, and the number of teaching weeks (for example, 16).
2. Open **Schedules → Generate semester schedule**. Select the semester, student, course, and inclusive week range.
3. Add one row per weekly meeting, for example Monday periods 1–2 and Thursday periods 3–4, both in A201. The form previews **32 planned classes** for weeks 1–16.
4. Save once. The backend validates the entire batch against existing classes and other meeting rows; any inclusive period overlap for the same student/date returns conflict details and saves nothing.
5. Use **Weekly rules** to see saved recurring patterns. **Generate missing classes** fills missing occurrences while preserving existing ones. Repeating the same generation request reuses its rules and does not duplicate classes.

**Edit this class** changes only one generated occurrence and marks it as adjusted. **Cancel class** keeps a cancellation record; **Restore** rechecks conflicts before reactivating it. Students and the MCP assistant see only classes that have not been cancelled. The immutable `source_date` prevents a moved or cancelled occurrence from being recreated at its original date.

**Add one-off class** remains available. Once a semester has weekly rules, its teaching start and week count are locked; its name can still be edited. This version supports weekly generation and individual adjustments. Editing a rule's future occurrences as a series is a separate operation for a later update.

## Chat behavior

Example requests:

- `What classes do I have tomorrow?`
- `Where is my Python class?`
- `What classes do I have this week?`
- `And the day after tomorrow?` after a schedule question.

A request such as `Write Tetris for my Python course` is outside the query-only scope. Greetings and vague requests receive a clarification prompt.

Each nonblank request normally adds one input-review model call. Review uses the latest question and up to eight recent messages, with a 15-second timeout. The review asks for a validated JSON decision; for the official DeepSeek endpoint, thinking is disabled only for this classification call.

Guardrails are model-based and can misclassify requests. They supplement JWT validation and server-side data access checks. They do not replace authorization.

Conversation memory is stored in the current tab's `sessionStorage`, scoped to the account and sign-in session. Closing the tab also clears this memory. Interrupted or failed answers remain outside the completed history sent to the model. Chat history is not stored in the database by this feature.

## API overview

| Endpoint or prefix | Purpose |
| --- | --- |
| `/api/auth` | Registration, login, and the Swagger OAuth2 token endpoint |
| `/api/user` | Profiles, password changes, and administrator user management |
| `/api/courses` | Course management |
| `/api/schedules` | Schedule management and personal schedule queries |
| `POST /api/schedules/generate` | Administrator batch generation from weekly meeting rows |
| `POST /api/schedules/{id}/restore` | Restore one cancelled generated class after conflict checks |
| `/api/semesters` | Administrator semester configuration |
| `/api/schedule-rules` | Administrator rule listing; `POST /{id}/generate` regenerates missing occurrences |
| `/api/study-plans` | Personal study plans |
| `/api/files` | File uploads |
| `/api/documents` | Administrator document uploads, listing, deletion, and text previews |
| `POST /api/chat/ask` | Complete assistant response |
| `POST /api/chat/stream` | SSE chat response |
| `GET /api/mcp/my-schedules` | Authenticated MCP query debugging |

Protected routes require `Authorization: Bearer <token>`. See the generated API documentation for schemas and role requirements.

Every response uses the envelope `{ "code", "message", "data" }`, and `code` equals the HTTP status: `400` for a rejected request, `401` for a missing or expired session, `403` for missing permission, `404` for a missing record, `409` for a conflict (a duplicate, or overlapping classes with the conflict list in `data`), `413` for an oversized upload, `422` for invalid input (the message names the problem), `429` when a rate limit is exceeded, and `5xx` for server or model-provider failures.

### Limits

| Limit | Default | Setting |
| --- | --- | --- |
| Sign-in attempts (`/auth/login` and `/auth/token` share one bucket) | 10 per minute per IP | `LOGIN_RATE_LIMIT` |
| Registrations | 10 per hour per IP | `REGISTER_RATE_LIMIT` |
| Chat messages (`/chat/ask` and `/chat/stream` share one bucket) | 20 per minute per account | `CHAT_RATE_LIMIT` |
| Chat question / one history message / history window | 2,000 / 8,000 characters / latest 20 messages | `backend/app/schemas/chat.py` |
| Avatar upload | JPG, PNG, GIF or WebP up to 5 MB | `backend/app/config.py` |
| Course document upload | `.txt`, `.md`, `.pdf`, `.docx` up to 100 MiB each | `backend/app/config.py` |

Counters are kept in memory by default, so each API process counts separately; set `RATE_LIMIT_STORAGE_URI` to a Redis URL when you run several workers. Limits are per client address, so behind a reverse proxy the proxy must pass the real address (see the Docker notes above).

## Tests

Backend tests use temporary SQLite databases and mocked external model responses; no live MySQL server or model API calls are required:

```bash
cd backend
./.venv/bin/python -m pip install -r requirements-dev.txt   # adds ruff
./.venv/bin/ruff check .
DATABASE_URL=sqlite:// JWT_SECRET_KEY=local-test-placeholder-secret-long-enough \
  ./.venv/bin/python -m unittest discover -s tests -v
```

Frontend tests and the production build:

```bash
cd frontend
npm test
npm run build
```

## Project layout

```text
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes
│   │   ├── common/          # Responses and exception handlers
│   │   ├── dependencies/    # Authentication and authorization
│   │   ├── hooks/           # Input-review middleware
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Request and response schemas, shared validators
│   │   ├── services/        # Business logic, agent, and MCP client
│   │   ├── rate_limit.py    # Limiter and 429 handler
│   │   └── db_migrate.py    # Runs Alembic from Python
│   ├── migrations/          # Alembic environment and versions
│   ├── tests/
│   ├── data/kb/             # Runtime course documents, excluded from Git
│   ├── uploads/             # Runtime files, excluded from Git
│   ├── .env.example
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── manage.py            # migrate, create-admin
│   ├── mcp_server.py
│   ├── pyproject.toml       # ruff configuration
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # HTTP and streaming clients
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── utils/           # Authentication, chat memory, request error handling, password rules
│   │   └── views/
│   ├── tests/
│   ├── .env.example
│   ├── Dockerfile
│   ├── nginx.conf           # Serves the build and proxies /api and /uploads
│   └── package.json
├── .github/workflows/ci.yml # Lint, tests, build, Docker image build
├── docker-compose.yml
├── sql/backend.sql          # Reference snapshot of the schema; migrations are the source of truth
├── .env.example             # Variables for docker-compose
├── .gitignore
└── README.md
```

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Backend cannot connect to MySQL | Verify the database exists and `DATABASE_URL` contains valid credentials. |
| Assistant cannot load tools | Start `mcp_server.py`; check `MCP_HOST`, `MCP_PORT`, and `MCP_PATH`. |
| Input review is unavailable | Check the backend review error log, model credentials, JSON output support, and provider connectivity. |
| No classes are returned | Create courses and assign schedules to the currently signed-in account. |
| Login expires | Sign in again. Chat memory is cleared when the application invalidates the session. |
| Browser reports CORS errors | Check backend errors first. Allowed origins come from `CORS_ORIGINS` in `backend/.env`. |
| API exits at startup with a `JWT_SECRET_KEY` error | Set a secret of at least 32 characters; the example placeholder is rejected on purpose. |
| `no such table` or `Table ... doesn't exist` | Run `alembic upgrade head` from `backend/`. The API does not create tables itself. |
| Requests fail with 429 | A rate limit was hit; wait a minute. Tune the limits in `backend/.env`, or check that a proxy forwards the real client address. |
| Registration says the password is invalid | Use at least 8 characters including a letter and a digit. |
| An Authlib deprecation warning appears | A warning alone does not indicate startup failure; check that Uvicorn reports a listening server. |

For deployment beyond localhost, configure HTTPS, process management, allowed frontend origins, and persistent database/upload storage. Keep the MCP service on a private interface unless your deployment explicitly requires exposing it.
