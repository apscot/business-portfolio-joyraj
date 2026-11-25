# Vision: F&O Business Portfolio Tracker

## Problem
An Indian F&O trader keeps trades in broker CSV exports and holdings (G-Secs, mutual funds, interest, invested capital) in scattered places. There is no single view of the business: how much capital is deployed, how it grows, what each NIFTY/SENSEX expiry earned, and whether the 10% yearly return goal is on track. Financial-year records are also hard to separate for tax and review.

## Value proposition
One clean, secure web app that treats trading as a business: import tradebook CSVs repeatedly without duplicates, see realized P&L per expiry, track capital and interest growth, and see at a glance whether yearly/quarterly/monthly/weekly targets are met. Everything is organised by Indian financial year (1 Apr–31 Mar), so past years are an automatic archive.

## Target user
Individual F&O traders in India (initially the owner), running the app themselves via Docker. It is multi-user: each user sees only their own data.

## Capabilities for this build
1. **Authentication and multi-user isolation**: login form, per-user data. Registration, or a seed user, is an assumption (the request only specifies login). We will provide simple sign-up plus login.
2. **Home / portfolio**: manually add holdings (G-Sec, mutual funds, other), dated interest-accrued entries, and dated invested-value entries. A financial-year dropdown drives a growth chart (cumulative invested plus interest over time).
3. **TradeBook**: upload a CSV (header columns as in the sample; trim whitespace in headers). Duplicate trades are skipped and never updated. The upload reports inserted vs. skipped counts. A table shows all fields, 15 rows per page, filtered by the selected FY.
4. **P&L**: realized gross P&L grouped by expiry date for NIFTY or SENSEX (with an All filter). Unclosed positions are flagged, not guessed. Charges are not included.
5. **Targets**: four cards (Yearly, Quarterly, Monthly, Weekly). Yearly target = 10% of the FY's total invested value. The others are pro-rata (yearly/4, /12, /52). Each card compares realized P&L for the current period with its target and shows a met / not-met indicator.
6. **FY archive**: a global financial-year selector. Choosing a past FY shows that year's data on every page. FY is derived from dates, so no data is moved.

## Quality bar
- Enterprise-style light-theme UI with strong UX: clear navigation, validation messages, empty states, loading states, and responsive layout.
- Frontend, backend API and database are separate and loosely coupled through a documented REST contract.
- Run everything with a single Docker Compose command.
- Minimal code, with secure basics: hashed passwords, secrets from environment variables.

## Assumptions
- Dedupe key is per user: exchange + segment + trade_id + trade_date.
- Target baseline = total invested value entered for the selected FY. A carry-forward from prior years is not included in this first build.
- Weekly period = Monday–Sunday. The "current" period for a past FY is its last period.
- P&L counts only closed (net-zero) quantity per contract, gross of charges.

## Out of scope
- Live market data, broker API integration, or automatic trade sync.
- Brokerage, STT, tax calculation or ITR reports.
- Mark-to-market for open positions, Greeks, strategy analytics.
- Editing or deleting individual trades (re-import only); admin or role management; password reset by email; social login.
- Mobile native apps, notifications, and multi-currency.
