# Summary – F&O Portfolio Tracker

## Built
Multi-user app: FastAPI + SQLAlchemy backend (JWT/bcrypt auth, all data user- and FY-scoped), React/TypeScript/Vite frontend (light theme). Pages: Login, Home (holdings, interest, investments, FY selector, growth chart), TradeBook (CSV upload, deduped by trade_id, 15 rows/page), P&L (by expiry, NIFTY/SENSEX), Target (yearly/quarterly/monthly/weekly, 10% of investment, met indicators). Docker Compose with nginx.

## Commands
- Setup: `python3 -m venv backend/.venv && backend/.venv/bin/python -m pip install -r backend/requirements.txt && (cd frontend && npm install)`
- Test: `(cd backend && .venv/bin/python -m pytest -q)` and `(cd frontend && npm test -- --run)`
- Build: `(cd frontend && npm run build)`
- Run: copy `.env.example` to `.env`, set `JWT_SECRET`, `docker compose up --build`, open http://localhost:8080

## Verified this stage
Backend 83 tests passed; frontend 7 tests passed; frontend build succeeded. Docker Compose and the running app were NOT run/verified. Coverage percentage not measured.

## Limitations
- PostgreSQL needs `psycopg[binary]` added manually.
- Backend tests emit deprecation warnings.
- No failed backlog tasks.
