# Project Summary – F&O Portfolio Tracker

## What was built
Multi-user web app for tracking F&O trading as a business portfolio.
- Backend: FastAPI, SQLAlchemy 2, Pydantic 2, JWT auth, bcrypt. SQLite by default, PostgreSQL via `DATABASE_URL`.
- Frontend: React 18 + TypeScript + Vite, light enterprise theme, Recharts.
- Pages: Login, Home (manual holdings such as gsec and mutual funds, interest with date, invested value with date, FY dropdown, growth chart), TradeBook (CSV upload, duplicates by `(user_id, trade_id)` skipped, 15 rows per page), P&L (by NIFTY/SENSEX expiry), Target (yearly, quarterly, monthly and weekly cards with a met/not-met indicator; target is 10% of investment per year).
- Every data endpoint takes a financial-year parameter (Apr–Mar), and every query is scoped by user.
- Docker Compose runs nginx serving the frontend and the backend.

## Commands
- Setup: `python3 -m venv backend/.venv && backend/.venv/bin/python -m pip install -r backend/requirements.txt && (cd frontend && npm install)`
- Test: `(cd backend && .venv/bin/python -m pytest -q)` and `(cd frontend && npm test -- --run)`
- Build: `(cd frontend && npm run build)`
- Run: copy `.env.example` to `.env`, set `JWT_SECRET`, then `docker compose up --build` and open http://localhost:8080.

## Verified in this stage
- Backend tests: 83 passed.
- Frontend tests: 7 passed.
- Frontend build: succeeded.
- I did not run Docker Compose or start the app, so the containers are unverified.

## Known limitations
- PostgreSQL needs `psycopg[binary]` added to requirements.
- The backend tests emit some warnings, about 40.
- No backlog tasks are marked failed.
