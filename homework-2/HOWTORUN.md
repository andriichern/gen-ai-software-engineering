# How to Run the Application

This guide walks you through setting up and running the **Intelligent Customer Support Ticket System** — a full-stack application with a FastAPI backend and a Svelte frontend.

## Quick Start (Recommended)

The fastest way to get the app running is to use the provided demo scripts. They handle dependency installation automatically.

### Option A: Start Everything Together

```bash
./demo/run-all.sh
```

This starts both the API and the frontend in the same terminal, with prefixed output and clean shutdown on Ctrl+C.

- **API**: http://localhost:8000
- **Frontend**: http://localhost:5173

### Option B: Start API and Frontend Separately (in Different Terminals)

**Terminal 1: API**

```bash
./demo/run-api.sh
```

**Terminal 2: Frontend**

```bash
./demo/run-app.sh
```

Both will auto-install dependencies on first run.

---

## Prerequisites

Make sure you have these installed:

- **Python 3.9 or later** (check: `python3 --version`)
- **Node.js 18+ and npm** (check: `node --version` and `npm --version`)
- **Bash** (macOS/Linux included; Windows users can use WSL or Git Bash)

---

## Manual Setup (If You Prefer)

If you want to understand what's happening or run without the demo scripts:

### Backend Setup

1. **Navigate to the API directory:**

   ```bash
   cd src/api
   ```

2. **Create a Python virtual environment** (if not already done):

   ```bash
   python3.9 -m venv .venv
   ```

3. **Activate the virtual environment:**

   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

5. **Start the API server:**

   ```bash
   cd ../..  # Go back to project root
   cd src
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will be running at **http://localhost:8000**

### Frontend Setup

In a new terminal:

1. **Navigate to the frontend directory:**

   ```bash
   cd src/app
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Start the development server:**

   ```bash
   npm run dev
   ```

   The frontend will be running at **http://localhost:5173**

---

## Verify It's Working

Once both servers are running:

1. **Check the API health:**

   ```bash
   curl http://localhost:8000/health
   ```

   You should see: `{"status":"ok"}`

2. **Open the frontend in your browser:**
   Visit **http://localhost:5173** and you should see the Tickets page.

---

## Available Features

### Tickets Management

- **Create tickets** with customer info, subject, description, and optional metadata
- **Auto-classify** tickets into categories (bug_report, billing_question, etc.) based on keywords
- **Filter** by category, priority, status, customer, or tags
- **Edit/delete** existing tickets
- **Resolve/close** tickets with automatic tracking of resolution timestamps

### Bulk Import

- Upload CSV/JSON/XML files with multiple tickets
- Auto-classify imported tickets
- View import summary with error reporting

### Category Management

- View all ticket categories and their keywords
- Create new custom categories
- Add/merge keywords into existing categories

### Classification System

- Keyword-based, deterministic classification (no LLM calls)
- Confidence scoring based on keyword matches
- Manual override support

---

## Troubleshooting

### API won't start: "Address already in use"

Port 8000 is already in use. Either:

- Kill the existing process: `pkill -f "uvicorn api.main"`
- Use a different port: `--port 8001`

### Frontend won't start: "Port 5173 in use"

Port 5173 is already in use. Either:

- Kill the existing process: `pkill -f "node .*vite"`
- Use a different port via `VITE_PORT=5174 npm run dev`

### `run-api.sh` or `run-app.sh` fails to run

Make sure scripts are executable:

```bash
chmod +x demo/run-api.sh demo/run-app.sh demo/run-all.sh
```

### Module/package import errors

Make sure you're running from the correct directory:

- **API**: always run from `src` directory (so `api` package resolves correctly)
- **Frontend**: always run from `src/app` directory

### CORS errors in the browser console

The API is configured to allow all origins locally (for development). If you see CORS errors, ensure:

- Both servers are running
- API is on http://localhost:8000 (not 127.0.0.1)
- Frontend is on http://localhost:5173

---

## Running Tests

### Backend Tests (pytest)

```bash
cd src/api
.venv/bin/python -m pytest -q
```

All 72 tests should pass.

### Linting

**Frontend (ESLint + Prettier):**

```bash
cd src/app
npm run lint    # Check for issues
npm run format  # Auto-fix formatting
```

**Backend (pylint):**

```bash
cd src
PYTHONPATH=.. api/.venv/bin/python -m pylint --rcfile=api/pyproject.toml api
```

### E2E Tests (Playwright)

```bash
cd src/tests/e2e
npx playwright test
```

Runs 6 tests across desktop and mobile viewports.

---

## Development Workflow

### Editing the API

- Edit files in `src/api/`
- The server automatically reloads on file changes (due to `--reload`)
- Check the terminal for any errors

### Editing the Frontend

- Edit `.svelte` or `.js` files in `src/app/src/`
- Vite hot-reloads automatically
- Errors appear in the browser console

### Adding Dependencies

- **Backend**: add to `src/api/requirements.txt`, then run `pip install -r requirements.txt`
- **Frontend**: run `npm install <package>` from `src/app/`

---

## Stopping the Application

- If using `run-all.sh`: Press **Ctrl+C** — both servers stop cleanly
- If using separate terminals: Press **Ctrl+C** in each terminal
