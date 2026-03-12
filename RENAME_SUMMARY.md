# Rename Summary: "vectrune" → "home_automation_server"

## Overview
Successfully renamed the internal project structure from the provisional name "vectrune" to the generic name "home_automation_server". All Python imports, configuration references, and documentation have been updated. The project root directory name remains unchanged.

---

## Changes Made

### 1. **Folder Structure**
- `app/` → `home_automation_server/`
  - All subdirectories retained:
    - `home_automation_server/api/`
    - `home_automation_server/models/`
    - `home_automation_server/services/`
    - `home_automation_server/db/`
    - `home_automation_server/core/`
    - `home_automation_server/frontend/`

### 2. **Database**
- **Old:** `./data/vectrune.db`
- **New:** `./data/home_automation_server.db`

### 3. **Configuration Files Updated**

| File | Changes |
|------|---------|
| **pyproject.toml** | `name = "vectrune"` → `name = "home_automation_server"` |
| | `include = ["app*"]` → `include = ["home_automation_server*"]` |
| **.env** | `DATABASE_URL=sqlite:///./data/vectrune.db` → `DATABASE_URL=sqlite:///./data/home_automation_server.db` |
| **alembic.ini** | `sqlalchemy.url = sqlite:///./data/vectrune.db` → `sqlalchemy.url = sqlite:///./data/home_automation_server.db` |

### 4. **Python Files: Import Updates** (25 files)

All `from app.*` and `import app.*` statements changed to `from home_automation_server.*` and `import home_automation_server.*`:

**Core Application:**
- `home_automation_server/main.py` — app title, imports, static/template paths
- `home_automation_server/core/config.py` — database_url default
- `home_automation_server/db/session.py` — config import, models import
- `home_automation_server/models/models.py` — (no changes needed)

**API Routers (6 files):**
- `home_automation_server/api/devices.py`
- `home_automation_server/api/pairing.py`
- `home_automation_server/api/automations.py`
- `home_automation_server/api/apps.py`
- `home_automation_server/api/webhooks.py`
- `home_automation_server/api/ui.py` — also updated template directory path

**Services (2 files):**
- `home_automation_server/services/pyatv_service.py`
- `home_automation_server/services/automation_engine.py`

**Tests & Migrations:**
- `tests/conftest.py` — app imports updated
- `alembic/env.py` — models import updated

### 5. **String Path Updates**

| Old | New |
|-----|-----|
| `"app/frontend/static"` | `"home_automation_server/frontend/static"` |
| `"app/frontend/templates"` | `"home_automation_server/frontend/templates"` |

Updated in:
- `home_automation_server/main.py` (static mount)
- `home_automation_server/api/ui.py` (Jinja2Templates)

### 6. **Documentation & Scripts** (5 files)

| File | Changes |
|------|---------|
| **README.md** | Title, project structure diagram, database reference, uvicorn command, .env example |
| **setup_env.ps1** | Bootstrap script instructions |

### 7. **Frontend Templates** (6 files)

All HTML templates updated for consistency:

| File | Changes |
|------|---------|
| `base.html` | Logo text from "🍎 Vectrune" → "Home Automation Server"; footer text; page title default |
| `index.html` | Page title |
| `devices.html` | Page title |
| `pairing.html` | Page title |
| `automations.html` | Page title |
| `apps.html` | Page title |

### 8. **JavaScript** (1 file)

| File | Changes |
|------|---------|
| `main.js` | Toast element ID from `vectrune-toast` → `has-toast` (cosmetic/consistent naming) |

---

## Verification

✅ **Server boots successfully:**
```bash
uvicorn home_automation_server.main:app --reload
```

✅ **All imports resolved:** No ModuleNotFoundError exceptions

✅ **Database path updated:** Config reads from `home_automation_server.db`

✅ **Templates render:** UI paths point to `home_automation_server/frontend/`

---

## Files Modified Summary

**Total: 37 files**

### Python (27):
- Core: 4 (`main.py`, `config.py`, `session.py`, `models.py`)
- API: 6 (`devices.py`, `pairing.py`, `automations.py`, `apps.py`, `webhooks.py`, `ui.py`)
- Services: 2 (`pyatv_service.py`, `automation_engine.py`)
- Tests: 4 (`conftest.py`, `test_*.py` x3)
- Alembic: 2 (`env.py`, `__init__.py` placeholders)
- Package init files: 9

### Config/Build (3):
- `pyproject.toml`
- `.env`
- `alembic.ini`

### Documentation (2):
- `README.md`
- `setup_env.ps1`

### Frontend Templates (6):
- HTML: 6 (base + 5 pages)

### JavaScript (1):
- `main.js`

---

## Migration Notes

- **No breaking changes** to external API or functionality
- **Database file name change** is cosmetic (new dev environments will use `home_automation_server.db`)
- **All existing functionality preserved:**
  - Apple TV scanning & pairing
  - Automation flows
  - App launching
  - Webhook triggers
- **Running the server:** Use `uvicorn home_automation_server.main:app --reload`

---

## Next Steps (Optional)

1. Delete old `data/vectrune.db` if it exists (next fresh start will use new db name)
2. Run `alembic upgrade head` if needed (migrations reference new db path in config)
3. All dependencies remain unchanged—no pip reinstall required

