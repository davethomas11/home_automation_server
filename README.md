# Home Automation Server

A local automation server for controlling Apple TVs via the [`pyatv`](https://pyatv.dev/) library.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI |
| ORM / Models | SQLModel |
| Database | SQLite (`./data/home_automation_server.db`) |
| Migrations | Alembic |
| Frontend | Jinja2 Templates |
| Apple TV Control | pyatv |

---

## Project Structure

```
/home_automation_server
  /api          – FastAPI routers
  /models       – SQLModel ORM models + Pydantic schemas
  /services     – Business logic (pyatv wrapper, automation engine)
  /db           – Database session & engine setup
  /frontend
    /templates  – Jinja2 HTML templates
    /static     – CSS / JS assets
  main.py       – FastAPI application factory
/alembic        – Alembic migration environment
/tests          – pytest test suite
/data           – SQLite database file (auto-created)
pyproject.toml
```

---

## Quick Start

### 1. Create & activate a virtual environment

```bash
python3.11 -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn home_automation_server.main:app --reload
```

The API will be available at **http://127.0.0.1:8000**  
Interactive docs at **http://127.0.0.1:8000/docs**  
Frontend UI at **http://127.0.0.1:8000/ui**

---

## API Routers

| Prefix | Description |
|--------|-------------|
| `/devices` | Scan & manage Apple TV devices |
| `/pairing` | Pair via MRP, Companion, AirPlay |
| `/automations` | Create & trigger automation flows |
| `/apps` | Launch apps by bundle ID |
| `/webhooks` | External webhook triggers |

---

## Pairing Workflow

1. **Scan** – `POST /devices/scan` discovers Apple TVs on the local network.
2. **Start pairing** – `POST /pairing/start` initiates pairing for a given protocol (MRP, Companion, AirPlay).
3. **Finish pairing** – `POST /pairing/finish` submits the PIN shown on the TV and saves credentials.
4. Credentials are stored in `AppleTVPairing` and used for future connections.

---

## Automation Flows

Flows are stored in `AutomationFlow`. Each flow has:
- `trigger_type`: `webhook` | `schedule` | `manual`
- `trigger_payload`: JSON string (e.g., webhook secret or cron expression)
- `action_type`: `launch_app` | `remote_command` | `power`
- `action_payload`: JSON string (e.g., `{"bundle_id": "com.netflix.Netflix"}`)

Trigger a flow manually:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/trigger/{flow_id}
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite:///./data/home_automation_server.db
LOG_LEVEL=INFO
```

---

## Running Tests

```bash
pytest
```

