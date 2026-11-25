# Backlog

1. Backend scaffold
2. Models, FY helpers, schemas
3. Auth API
4. Holdings, interest, investments and summary API
5. Trade CSV import and list API
6. P&L and targets API
7. Backend Dockerfile
8. Frontend scaffold, theme and API client
9. Layout, routing, shared components and Login page
10. Home page
11. TradeBook page
12. P&L and Target pages
13. Frontend Docker, nginx and Compose
14. README (docs)

# Plan

**Ships first:** the backend, one vertical at a time (auth, then data, then trades, then P&L and targets). Each piece is tested through the API before any UI depends on it. The frontend scaffold (8) only needs task 1, so it can be built in parallel with the backend work.

**Dependencies to respect:**
- Everything per-user is scoped by `user_id` from the auth dependency (task 3).
- P&L and targets (6) use trades (5) and investments (4).
- Frontend pages (10–12) need the shared layout and FY context (9) and their matching API.
- Compose (13) needs both Dockerfiles and a buildable frontend.

**Main risks:**
- 1 (scaffold): the test DB must share one connection for in-memory SQLite (StaticPool).
- 2 (models): FY boundaries (31 Mar and 1 Apr) and Decimal handling.
- 3 (auth): bcrypt and JWT pins. Keep the 72-byte password limit in mind.
- 4 (summary): the growth series must be cumulative and ordered, with correct FY filtering.
- 5 (import): strict header check, whitespace in headers, quantities like `520.000000`, and idempotent re-upload.
- 6 (P&L, targets): open-position flag and the current-period logic for past FYs.
- 9 (frontend shell): token expiry and redirect handling.
- 13 (compose): nginx proxy to the backend, and SQLite volume permissions.
