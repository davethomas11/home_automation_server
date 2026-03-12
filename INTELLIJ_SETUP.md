# IntelliJ IDEA – Configure Python Interpreter & Virtual Environment

## Quick Setup

Your virtual environment is located at:
```
C:\Users\davet\IdeaProjects\Home Automation Server\.venv\Scripts\python.exe
```

### Steps to Configure IntelliJ:

#### **1. Open Project Settings**
- Go to: **File → Settings** (Windows/Linux) or **IntelliJ IDEA → Preferences** (macOS)
- Or press: **Ctrl+Alt+S**

#### **2. Navigate to Python Interpreter**
- In the Settings window, go to: **Project: Home Automation Server → Python Interpreter**
- (On the left sidebar, find the project name and expand it)

#### **3. Add the Virtual Environment Interpreter**
- Click the **gear icon** (⚙️) at the top right of the interpreter dropdown
- Select **Add...**
- Choose **Add Local Interpreter → Existing Environment**

#### **4. Select the Python Executable**
- Browse to the `.venv` folder Python executable:
  ```
  C:\Users\davet\IdeaProjects\Home Automation Server\.venv\Scripts\python.exe
  ```
- Click **OK** to confirm

#### **5. Verify Interpreter is Set**
- Go back to **Project: Home Automation Server → Python Interpreter**
- You should see the virtual environment listed with all installed packages:
  - `fastapi`
  - `uvicorn`
  - `sqlmodel`
  - `pyatv`
  - `alembic`
  - `pytest`
  - And all dependencies (150+)

---

## Full Visual Walkthrough (If First Time)

### **Step 1: File → Settings**
```
┌─ IntelliJ IDEA ─────────────────┐
│ File  Edit  View  Run  Tools ...│
│ └─ Settings          (Ctrl+Alt+S)
└─────────────────────────────────┘
```

### **Step 2: Find Python Interpreter Section**
```
Settings Window:
├─ Project: Home Automation Server
│  ├─ Project Files
│  ├─ Python Interpreter    ← SELECT THIS
│  ├─ Package Manager
│  └─ ...
└─
```

### **Step 3: Configure Interpreter**
```
┌─ Python Interpreter ────────────────────────────┐
│                                              ⚙️   │
│ [Current Python 3.11 (.venv)]  ▼    [Add...]    │
│                                                  │
│ Project Interpreter: .venv (Python 3.11.7)     │
│                                                  │
│ Packages:                                        │
│ ├─ alembic                    1.18.4            │
│ ├─ anyio                       4.12.1            │
│ ├─ fastapi                     0.135.1           │
│ ├─ pytest                      9.0.2             │
│ ├─ pyatv                       0.17.0            │
│ ├─ sqlmodel                    0.0.37            │
│ ├─ uvicorn                     0.41.0            │
│ └─ ... (150+ total packages)                    │
│                                                  │
│  [Apply]  [OK]                                   │
└──────────────────────────────────────────────────┘
```

---

## Troubleshooting

### **Issue: Red squiggly lines on imports (e.g., `from fastapi import...`)**
**Solution:**
1. Make sure the interpreter is set (above)
2. Go to **File → Invalidate Caches** and restart IntelliJ
3. Wait a few seconds for IntelliJ to reindex

### **Issue: "No module named 'fastapi'"**
**Solution:**
- Your interpreter isn't pointing to `.venv`
- Follow **Step 3-4** above to explicitly select:
  ```
  C:\Users\davet\IdeaProjects\Home Automation Server\.venv\Scripts\python.exe
  ```

### **Issue: Interpreter dropdown shows multiple Pythons**
**Solution:**
- Click the dropdown and select the one that shows **(.venv)** or has the path ending in `.venv\Scripts\python.exe`

### **Issue: Packages not showing in the list**
**Solution:**
1. Right-click the interpreter in the list
2. Select **Show All** or **Refresh**
3. Wait for indexing to complete

---

## After Configuration – What You'll See

Once configured, IntelliJ will:

✅ **Recognize all imports:**
```python
from home_automation_server.main import app        # ✓ Green
from home_automation_server.models.models import *  # ✓ Green
from sqlmodel import Session, select                 # ✓ Green
from fastapi import FastAPI                         # ✓ Green
```

✅ **Provide autocomplete:**
- Press `Ctrl+Space` after typing `from fastapi import` → see all FastAPI classes
- Hover over classes to see docstrings
- Cmd+Click to jump to definitions

✅ **Show installed dependencies:**
- In **Project → Python Interpreter**, all 150+ packages will be listed
- You can search for specific packages

✅ **Enable testing:**
- Run pytest tests directly in IntelliJ
- Right-click `tests/` folder → **Run pytest**
- See test results in the Test pane

---

## Running the Server from IntelliJ

### **Option 1: Using the Run Configuration**

1. Go to **Run → Edit Configurations** (or press **Alt+Shift+F10**)
2. Click **+ Add New Configuration**
3. Select **Python** (or create a Shell Script config)
4. Set:
   - **Module name:** `uvicorn`
   - **Parameters:** `home_automation_server.main:app --reload`
   - **Working directory:** `C:\Users\davet\IdeaProjects\Home Automation Server`
5. Click **OK**
6. Click the **Run** button (or press **Shift+F10**)

The server will start and you can see logs in the Run pane.

### **Option 2: From Terminal in IntelliJ**

1. Open the built-in terminal (**View → Tool Windows → Terminal**)
2. Run:
   ```bash
   .venv\Scripts\Activate.ps1
   uvicorn home_automation_server.main:app --reload
   ```

---

## Summary

| Task | Action |
|------|--------|
| **Open Settings** | `Ctrl+Alt+S` |
| **Add Interpreter** | Settings → Project → Python Interpreter → Gear → Add |
| **Select .venv** | Browse to `.venv\Scripts\python.exe` |
| **Verify** | See FastAPI, SQLModel, PyATV in package list |
| **Restart IDE** | After changes, File → Invalidate Caches |
| **Run Server** | Right-click `home_automation_server/main.py` → Run or create Run Configuration |

---

## Your Specific Path

For this project, use **exactly**:
```
C:\Users\davet\IdeaProjects\Home Automation Server\.venv\Scripts\python.exe
```

That's it! After this, IntelliJ will recognize all your code, provide autocomplete, and show zero red errors.

