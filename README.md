# F&O Portfolio Tracker

A multi-user web app for tracking Futures & Options trades. Upload a broker tradebook CSV and see your trades, realised P&L per expiry, a portfolio summary, and profit targets, all by financial year.

Stack: FastAPI + SQLAlchemy (Python 3.12) backend, React + TypeScript + Vite frontend, SQLite (default) or PostgreSQL, served by nginx via Docker Compose.

## Features
- Register / log in (JWT, bcrypt-hashed passwords). Every query is scoped to the logged-in user.
- Tradebook CSV upload with per-row validation and duplicate skipping.
- Paginated trade book.
- Realised P&L grouped by expiry date and underlying (optional NIFTY / SENSEX filter).
- Profit targets (yearly, quarterly, monthly, weekly) with status and progress.
- Manual entry of investments, interest and holdings; summary with a growth series.
- Financial-year selector on all data views.

## Assumptions
- **Financial year (FY):** 1 Apr – 31 Mar, labelled like `2026-27`. Every data endpoint takes an optional `fy` query parameter. The FY list contains the FYs of your data plus the current one.
- **P&L:** per (underlying, expiry date): `sum(sell qty × price) − sum(buy qty × price)`. Trades are assigned to an FY by their **expiry date**; trades with no expiry date are ignored. A row is flagged `open` when any symbol's net quantity is non-zero (P&L is then partial).
- **Underlying:** derived from the symbol prefix (`MIDCPNIFTY`, `BANKNIFTY`, `FINNIFTY`, `SENSEX`, `BANKEX`, `NIFTY`), otherwise `OTHER`.
- **Targets:** yearly target = 10% of the amount invested (Investments entries dated inside the FY). Quarterly = yearly/4, monthly = yearly/12, weekly = yearly/52. The "current" period is today clamped into the chosen FY (a past FY shows its last period). Achieved = realised P&L of expiries inside the period. Status: `Met` (achieved > 0 and ≥ target), `In progress` (achieved > 0), else `Behind`. Progress is clamped to 0–100%.
- **Dedupe:** trades are unique per `(user, trade_id)`. Rows whose `trade_id` already exists for you (or repeats within the file) are skipped and counted as duplicates; existing trades are never updated.
- Money uses `Decimal`/`Numeric`, never float.

## Run
Install Docker, then:

```
cp .env.example .env     # set JWT_SECRET to a long random value, e.g. openssl rand -hex 32
docker compose up --build
```

Open http://localhost:8080.

Optional PostgreSQL: set `DATABASE_URL` in `.env` (e.g. `postgresql+psycopg://user:password@host:5432/dbname`) and add `psycopg[binary]` to `backend/requirements.txt`. Default is SQLite.

### Development
```
python3 -m venv backend/.venv && backend/.venv/bin/python -m pip install -r backend/requirements.txt
(cd frontend && npm install)
(cd backend && .venv/bin/python -m pytest -q)     # backend tests, in-memory SQLite
(cd frontend && npm test -- --run)                # frontend tests
(cd frontend && npm run build)                    # production build
```

## CSV format
UTF-8 (BOM allowed), max 5 MB, first row is the header. Headers are case-insensitive and whitespace-trimmed, in any order, but must be **exactly** these 14 columns (missing, unexpected or duplicate columns reject the file):

`symbol, isin, trade_date, exchange, segment, series, trade_type, auction, quantity, price, trade_id, order_id, order_execution_time, expiry_date`

| Column | Rule |
|---|---|
| `symbol`, `exchange`, `segment`, `trade_type`, `trade_id` | required |
| `trade_type` | `buy` or `sell` (case-insensitive) |
| `trade_date`, `expiry_date` | `YYYY-MM-DD`; `expiry_date` may be empty |
| `order_execution_time` | ISO date-time |
| `quantity` | number > 0 |
| `price` | number ≥ 0 |
| `auction` | `true/yes/y/1` or `false/no/n/0` or empty |
| `isin`, `series`, `order_id` | optional text |

Max lengths: symbol 100, isin/exchange/segment/series 20, trade_id/order_id 50. Invalid rows are not imported; the response lists them with their 1-based line number (header = row 1) and a reason, while valid rows are still saved.

## API overview
All endpoints except register/login need `Authorization: Bearer <token>`. Data endpoints accept `fy` (e.g. `2026-27`).

| Method & path | Purpose |
|---|---|
| `POST /api/auth/register`, `POST /api/auth/login` | Create account / get token |
| `GET /api/auth/me` | Current user |
| `POST /api/trades/upload` | Multipart `file` field; returns `{inserted, duplicates, invalid[]}` |
| `GET /api/trades` | Paginated trades: `fy`, `page`, `page_size` (default 15, max 100) |
| `GET /api/pnl` | P&L rows and total; optional `underlying=NIFTY\|SENSEX` |
| `GET /api/targets` | Four target cards for the FY |
| `GET /api/fy` | Available FY labels |
| `GET /api/summary` | Invested, interest, total and growth series |
| `GET/POST /api/investments`, `DELETE /api/investments/{id}` | Investment entries |
| `GET/POST /api/interest`, `DELETE /api/interest/{id}` | Interest entries |
| `GET/POST /api/holdings`, `DELETE /api/holdings/{id}` | Holdings |

`GET /api/health` returns `{"status": "ok"}`. nginx proxies only `/api/` to the backend.

## Layout
- `backend/app/`: `routers/` (HTTP only) → `services/` (pure logic) → `models.py`; settings in `config.py`.
- `backend/tests/`: pytest, in-memory SQLite.
- `frontend/src/`: pages call the backend only through `api.ts`.
