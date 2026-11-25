# AGENTS.md – F&O Portfolio Tracker

Read atlas/architecture.md and atlas/CONSTRAINTS.md first.

## Stack
- Backend: Python 3.12, FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2, PyJWT, bcrypt, pytest 8 + httpx
- Frontend: React 18.3, TypeScript 5, Vite 5.4, react-router 6, Recharts 2.12, Vitest, plain CSS
- DB: SQLite by default; PostgreSQL via `DATABASE_URL`
- Serving: nginx + Docker Compose

## Commands (this machine)
setup: python3 -m venv backend/.venv && backend/.venv/bin/python -m pip install -r backend/requirements.txt && if [ -d frontend ]; then (cd frontend && npm install); fi
test: (cd backend && .venv/bin/python -m pytest -q; rc=$?; [ $rc -eq 5 ] || exit $rc) && if [ -d frontend ]; then (cd frontend && npm test -- --run); fi
build: if [ -d frontend ]; then (cd frontend && npm run build); fi

## Layout
- `backend/app/` routers (HTTP only) → `services/` (pure logic) → `models.py`. Settings from env in `config.py`.
- `backend/tests/` use in-memory SQLite; no server needed.
- `frontend/src/` pages call the backend only via `api.ts`; shared styling in `styles.css`.

## Conventions
- Every query is scoped by `user_id`; every data endpoint takes `fy` (financial year Apr–Mar, label `2026-27`).
- Money uses Decimal/Numeric, never float in the DB layer.
- Trades are unique per `(user_id, trade_id)`; duplicates are skipped, never updated.
- No secrets in the repo; read `JWT_SECRET`, `DATABASE_URL` from env.
- Keep code minimal; no new patterns/abstractions beyond atlas/architecture.md.
- Never skip or weaken tests to get green.

## Run on your machine
Install Docker, copy `.env.example` to `.env`, set `JWT_SECRET` to a long random value, then `docker compose up --build` and open http://localhost:8080. For PostgreSQL set `DATABASE_URL` in `.env` (and add `psycopg[binary]` to requirements).
