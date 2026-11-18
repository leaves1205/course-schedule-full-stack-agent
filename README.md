# Course Schedule Full Stack Agent

A campus course scheduling application with an authenticated AI assistant. Built with **Vue 3, FastAPI, LangChain, MCP, SQLAlchemy, and MySQL**.

The assistant queries the signed-in user's schedule through a JWT-bound MCP tool. Input guardrails review each request before the answering model runs, and the chat interface streams answers and tool activity over SSE.

## Features

- **Authentication:** registration, sign-in, JWT validation, profiles, avatars, and password changes.
- **Role-based management:** administrators manage users, courses, and class schedules; students view their own schedules and study plans.
- **Course assistant:** ask about dates, courses, class periods, and locations, including contextual follow-up questions.
- **Input guardrails:** classify requests as `allow`, `deny`, or `clarify`; unrelated requests receive a fixed response. Review failures stop processing.
- **Streaming chat:** display answer fragments, processing status, and tool activity; internal review output is excluded from the stream.
- **Short-term conversation memory:** restore chat history and drafts after page reloads or navigation within the same tab. Clear them on sign-out, session invalidation, or a new sign-in.
- **User isolation:** MCP resolves identity from the request JWT rather than a model-supplied user ID.
- **Course documents:** administrators upload `.txt`, `.md`, `.pdf`, and `.docx` materials, preview their extracted text, and manage saved documents. Uploads support multiple files with a 100 MiB limit per file; a failed upload rolls back the batch.
- **Blue and white interface:** responsive navigation, course and schedule tables, account forms, and a dashboard showing real schedule totals and recent study plans.
- **Local tests:** backend tests use isolated SQLite databases and mocked model responses; frontend tests cover chat restoration, logout cleanup, interrupted streams, role-based navigation, dashboard data, and failed requests.

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

## Quick start

The commands below use macOS/Linux shell syntax. Run them from the repository root unless a step changes directories.

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

Generate a JWT secret locally and paste the result into `JWT_SECRET_KEY`:

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

The configured MySQL account must have access to this database. FastAPI creates missing application tables on startup.

Alternatively, import the schema-only script:

```bash
mysql -u your_mysql_user -p course_schedule < sql/backend.sql
```

The script includes the `users`, `course`, `schedules`, and `study_plan` tables. It contains no user records, password hashes, contact details, or uploaded files, and does not drop existing tables.

### 3. Install backend dependencies

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

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

1. Register an account through the frontend. New accounts have the `student` role.
2. To make your own account an administrator, run the following against your local database, substituting the username you registered:

   ```sql
   UPDATE users
   SET role = 'admin', update_time = NOW()
   WHERE username = 'your_registered_username';
   ```

3. Sign out and sign in again to refresh the profile shown by the frontend.
4. Use the administrator pages to create courses and assign schedules to registered users.
5. Sign in as a student and query the assigned schedule in the course assistant.

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
| `/api/study-plans` | Personal study plans |
| `/api/files` | File uploads |
| `/api/documents` | Administrator document uploads, listing, deletion, and text previews |
| `POST /api/chat/ask` | Complete assistant response |
| `POST /api/chat/stream` | SSE chat response |
| `GET /api/mcp/my-schedules` | Authenticated MCP query debugging |

Protected routes require `Authorization: Bearer <token>`. See the generated API documentation for schemas and role requirements.

## Tests

Backend tests use temporary SQLite databases and mocked external model responses; no live MySQL server or model API calls are required:

```bash
cd backend
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
│   │   ├── schemas/         # Request and response schemas
│   │   └── services/        # Business logic, agent, and MCP client
│   ├── tests/
│   ├── data/kb/             # Runtime course documents, excluded from Git
│   ├── uploads/             # Runtime files, excluded from Git
│   ├── .env.example
│   ├── mcp_server.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # HTTP and streaming clients
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── utils/           # Authentication and chat memory
│   │   └── views/
│   ├── tests/
│   ├── .env.example
│   └── package.json
├── sql/backend.sql         # Schema only; no personal or demo records
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
| Browser reports CORS errors | Check backend errors first. Allowed local origins are configured in `backend/app/main.py`. |
| An Authlib deprecation warning appears | A warning alone does not indicate startup failure; check that Uvicorn reports a listening server. |

For deployment beyond localhost, configure HTTPS, process management, allowed frontend origins, and persistent database/upload storage. Keep the MCP service on a private interface unless your deployment explicitly requires exposing it.
