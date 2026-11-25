# Constraints – quality bar

- Tests must not be skipped, deleted, or weakened (no `skip`/`xfail` additions, no new lint-suppression comments, no shrinking assertions) just to get a passing build. Fix the code instead.
- Coverage: backend ≥ 80% line coverage on `app/services` and `app/fy.py` (the business rules: import dedupe, FY, P&L, targets); routers have tests for auth, user isolation, and upload. Frontend: tests for API wrapper and at least login and table pagination; no numeric target.
- Tests need no running server, Docker or network; use in-memory SQLite.
- Security: no secrets committed; all queries parameterised and user-scoped; passwords bcrypt-hashed; all inputs validated at the boundary.
- Backend type hints on public functions; TypeScript `strict` on; no `any` without reason.
- UI: every page has loading, empty and error states; works at 375px width.
