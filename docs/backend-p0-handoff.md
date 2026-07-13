# Sprint 3–4 Backend P0 Handoff

Data/Ops has frozen the data contracts and intentionally does not modify `backend/**` or OpenAPI. The following items require Backend ownership before cross-service P0 can be declared closed.

## Medical profile (O8)

- Keep `medical_profiles` as the sole canonical table. Its DDL is column-based and has no `encrypted_payload` column.
- Remove or migrate the duplicate `GET/PUT/DELETE /api/v1/user/medical-profile` implementation that reads `encrypted_payload`; leave exactly one route matching the DDL, OpenAPI, fixtures, and cascade-delete behavior.
- Add contract tests that prove only one route is registered and the returned/persisted fields match the table.

## Chatbot privacy (O6/O7)

- Preserve the current venue-embeddings-only retrieval boundary; no medical profile table, module, or source may enter retrieval or prompt assembly.
- Add route-level coverage for Gemini timeout/retry, explicit fallback behavior, medical-advice refusal, and requested-language preservation.
- Retain a test that demonstrates the actual retrieval query excludes medical data, not only that the final response is safe.

## Fallback contracts (O4)

- Development may use mocks only when DB access is unavailable. Production and demo must return explicit degraded/no-data behavior, never silent mock success.
- Freeze one response schema across DB, fallback, and empty-data cases; `data_mode` is required and `fallback_reason` must accompany degraded responses. Agree any `formula_version` requirement with Frontend before release.
- Align reports and insights tests with this matrix, then run Frontend schema smoke tests against the frozen contract.
