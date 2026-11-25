# Research: F&O Trading Portfolio Tracker

Note: web search returned no results; everything below is from background knowledge and is **unverified** against live sources.

## Domain facts
- **Indian financial year (FY)** runs 1 Apr – 31 Mar. Quarters: Q1 Apr–Jun, Q2 Jul–Sep, Q3 Oct–Dec, Q4 Jan–Mar. FY labels like "2025-26".
- **F&O income** is treated as non-speculative business income in India; traders want per-FY archives (for ITR-3 / audit turnover). Turnover for F&O tax purposes is the sum of absolute settled P&L, not gross trade value (unverified detail; the app need only show P&L).
- **Symbol format**: the sample symbols (`NIFTY26OCT23500CE`) are monthly-style: underlying + YY + MON + strike + CE/PE. Weekly options usually embed a month code/day (e.g. `NIFTY2610723500CE`). The parser must therefore be tolerant. The underlying can be derived by prefix (NIFTY, SENSEX, BANKNIFTY, FINNIFTY...). The sample's `26OCT` looks like year 26, but dates are also 2026, so the format is consistent. Don't depend on the symbol for expiry; the CSV has `expiry_date`.
- **CSV looks like a Zerodha tradebook export** (symbol, isin, trade_date, exchange, segment, series, trade_type, auction, quantity, price, trade_id, order_id, order_execution_time). `expiry_date` is an added column. Note the pasted header has a stray tab after `auction`; strip whitespace from headers.
- **Uniqueness**: `trade_id` is unique per exchange/segment per day in broker data, and is not guaranteed globally unique. A safe dedupe key is (user, exchange, segment, trade_id, trade_date), or add order_id. Duplicate rows should be skipped, not updated, and the upload summary should report inserted vs. skipped counts.
- **P&L by expiry**: group trades by (underlying, expiry_date). Within each contract (symbol), realized P&L = Σ(sell qty×price) − Σ(buy qty×price) for closed quantity. Matching on net-zero positions is simple; open or expired-unsquared positions need a flag. Charges (brokerage, STT, etc.) are not in the CSV, so P&L is gross. Quantity is in units (contracts × lot size), so no lot-size multiplication is needed. Sample quantities such as 520 and 455 are consistent with that.
  - Positions that are still open (net quantity ≠ 0) are best shown as "open" and excluded from realized P&L. Options expiring worthless/exercised do not generate a closing trade in the tradebook, so there may be a residual. Flag it and don't invent a value.
  - Only NIFTY and SENSEX were requested. Filter on the underlying and allow an "All" filter.
- **Targets**: yearly = 10% of total invested capital for the FY. Derived: quarterly = yearly/4, monthly = yearly/12, weekly = yearly/52. Compare against realized P&L within the current period. "Invested value" is the sum of the dated entries for the FY (a design decision to confirm: invested capital in the FY, plus the carried-forward value?).
- **Home portfolio**: manual holdings (G-Sec, mutual funds, etc.), dated interest accrued entries, dated invested-value entries. The growth graph = cumulative invested + cumulative interest (+ realized F&O P&L, optional) over time in the FY.

## Common product patterns (Tradervue, Edgewonk, Zerodha Console, Sensibull-style P&L)
- CSV import with preview and a duplicate/skipped summary.
- Paginated, sortable tables; filter by date/symbol.
- Summary cards with green/red status indicators, and an equity curve chart.
- A global FY selector in the header, which drives all pages (matches the "archive" requirement).

## Multi-user and security implications
- All tables carry `user_id`; every query is scoped by it. Dedupe uniqueness is per user.
- Password hashing (argon2/bcrypt), short-lived JWT or secure cookie sessions, rate-limit login, and CORS limited to the frontend origin. Secrets come from env vars, not the repo.
- No self-signup was specified. Assumption: provide registration or a seed admin user; this is an open question.

## Implications / assumptions for later stages
1. FY is derived from the date (not stored per row), so the archive is just a filter. No data moves.
2. Money: use decimals (not floats) for price × quantity.
3. Decouple: separate frontend and API containers and a database container, with an API contract (REST/OpenAPI) between them; Docker Compose to run all of them.
4. 15 rows/page implies server-side pagination.
5. Unverified/open: exact dedupe key, handling of unsquared expiries, whether the target baseline is "invested in FY" or total cumulative investment, charges/taxes exclusion, and the weekly definition (ISO week vs Mon–Fri).
