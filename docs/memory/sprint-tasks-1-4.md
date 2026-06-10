# ClearPath Sprint 1-4 Task Summary

> Sources: Notion Sprint Backlog + Backend Lead Pipeline + Data Lead Pipeline
> Updated: 2026-06-09 | Synced from Notion
> Team: Hsu Ching Yun (H), fangxun.wu (F), David Irving (D), Joanna Saheed (J), Emmett (E)

---

## Sprint 1 — Completed ✅

| Task | Week | Assignee | Status |
|------|------|----------|--------|
| Create Personas | Week 1 | All | ✅ |
| Interview | Week 1 | All | ✅ |
| Competitors Research | Week 1 | David, Joanna | ✅ |
| Create Git Repository & Branching | Week 2 | Hsu Ching Yun | ✅ |
| Create Mockups | Week 3 | Joanna, Hsu Ching Yun | ✅ |
| Supplemental Web Scraping Exploration | Week 3 | fangxun.wu | ✅ |
| API Endpoints Interfaces | Week 3 | Emmett, David, fangxun.wu | ✅ |
| Data Prototyping | Week 3 | Emmett | ✅ |
| API & Schema Alignment | Week 3 | fangxun.wu | ✅ |
| Database Initialization | Week 3 | fangxun.wu | ✅ |
| Sprint 2 Planning & backlog | Week 3 | Hsu Ching Yun | ✅ |
| Sprint Review & Retrospective | Week 3 | Hsu Ching Yun | ✅ |
| Tracking Table & Burn-Down Chart | Week 3 | Hsu Ching Yun | ✅ |
| API Contract Revision & Schema Alignment | Week 3 | Emmett | ✅ |

---

## Sprint 2 — Core Environment + Auth + Zoning (Week 4-5)

### Backend (Emmett)

| # | Task | Week | Description | Status |
|---|------|------|-------------|--------|
| B2.1 | Core App Entry, Poetry & Flask Blueprints Setup | Week 4 | `pyproject.toml` + Blueprints (`/auth`, `/profile`, `/map`) | ❌ |
| B2.2 | MySQL Table Implementation & Connection Pooling | Week 4 | DDL execution + FK constraints + district index + Flask-SQLAlchemy pooling | ✅ DDL done |
| B2.3 | Authentication Gateway & JWT Session API | Week 4 | `/auth/register`, `/auth/login`, `/auth/guest` + JWT | ❌ users table ready |
| B2.4 | Personal Profile & Medical ID CRUD Endpoints | Week 4 | `GET/PUT /api/v1/profile` | ❌ D10: medical data device-local only |

### Data (fangxun.wu)

| # | Task | Week | Description | Status |
|---|------|------|-------------|--------|
| D2.1 | ERD Revision, Schema Updates & District Zoning Setup | Week 4 | ERD update + 4 district nodes (Uptown, Midtown East, Midtown West, Downtown) | ✅ |
| D2.2 | MySQL Table Implementation | Week 4 | DDL scripts + FK constraints + district index | ✅ 19 tables done |
| D2.3 | Data Parsing & Ingestion | Week 4 | ETL pipeline: NYC Open Data → MySQL | ✅ |
| D2.4 | API & Map Mocking Data Arrays | Week 4 | JSON mock data grouped by district | ✅ |

### Mobile (David Irving)

| # | Task | Week | Description | Status |
|---|------|------|-------------|--------|
| M2.1 | Mobile Infrastructure & Navigation Architecture | Week 4 | Repository framework + design tokens + tab/stack navigation | ❌ |
| M2.2 | Mobile Pages 1 & 3: Language & Location Permission Gateways | Week 4 | Language Selection + Location Permission | ❌ |
| M2.3 | Mobile Page 2: Legal & Compliance Interface | Week 4 | Terms of Service + Privacy Policy | ❌ |
| M2.4 | UI Component Binding with Mocks | Week 4 | Profile & Medical ID binding | ❌ |

### Web (Casey)

| # | Task | Week | Description | Status |
|---|------|------|-------------|--------|
| W2.1 | Baseline Workspace Init, Global Navigation Bar & Routing Frame | Week 4 | Root framework + nav bar + routing | ❌ |
| W2.2 | UI Component Binding with Mocks | Week 4 | User Profile + Auth component binding | ❌ |
| W2.3 | Web Page 1: Sign-In Gateway & Location Modal Trigger | Week 4 | Login page + location permission | ❌ |
| W2.4 | Web Pages 6 & 7: User Profile View & Editable ID Workspaces | Week 4 | Health dossier layout | ❌ |
| W2.5 | Web Page 8: Medical Preview & PDF Document Generation | Week 5 | A4 medical form + PDF export | ❌ |

### Design (Joanna Saheed)

| # | Task | Week | Description | Status |
|---|------|------|-------------|--------|
| J2.1 | User Testing to Finalize UI | Week 4 | 3-5 target users testing Figma prototypes | ❌ |

---

## Sprint 3 — Spatial Query + Reports + ML Production

### Backend

| # | Task | Priority | Description |
|---|------|----------|-------------|
| B3.1 | Map Query Engine | P0 | `/api/v1/map/venues` supports district/language/wheelchair filters |
| B3.2 | 5-Minute Cache Window | P0 | Server-side busyness query cache |
| B3.3 | Report Engine Path A (venue-bound) | P0 | `POST/PATCH /reports` |
| B3.4 | Report Engine Path B (GPS-only) | P1 | Standalone `standalone_incidents` table |
| B3.5 | **2-Hour TTL** | P0 | Celery/Redis background cleanup of expired reports |
| B3.6 | Push Notifications (report resolved) | P1 | `PATCH /reports` triggers push |
| B3.7 | SOS Webhook | P0 | `/api/v1/emergency/sos` 5s long-press signal |
| B3.8 | Report + API Performance Unit Tests | P0 | Concurrent writes, TTL precision, district isolation |

### Data

| # | Task | Priority | Description |
|---|------|----------|-------------|
| D3.1 | **Real-Time Telemetry Pipeline** | **P0** | External data sources → real-time wait time/load |
| D3.2 | **ML Model: 12-Hour Forecast** | **P0** | ARIMA/LSTM per-facility time-series prediction |
| D3.3 | Report Path A Data Routing | P0 | Venue active alert field |
| D3.4 | Report Path B Data Routing | P1 | `standalone_incidents` table |
| D3.5 | **Regional Aggregation Formula** | **P0** | Real-Time Density, Best Travel Window, Fastest Hubs |
| D3.6 | 2-Hour TTL (with Backend) | P0 | Auto-delete expired reports |
| D3.7 | ML + Aggregation Unit Tests | P0 | PyTest: regional logic, ranking functions, 95% coverage |

---

## Sprint 4 — Account Deletion + AI Integration + E2E Tests

### Backend

| # | Task | Priority | Description |
|---|------|----------|-------------|
| B4.1 | Cascade Delete API | P0 | `DELETE /api/v1/account` purges all associated data |
| B4.2 | JWT Invalidation + Frontend Cleanup | P0 | Force-clear localStorage/AsyncStorage |
| B4.3 | Gemini RAG Integration | P1 | AI chatbot Flask routes |
| B4.4 | Rate-limiting + API Docs | P0 | Throttling + Swagger/Postman |
| B4.5 | Cascade Delete + Security Unit Tests | P0 | Complete data purge verification |

### Data

| # | Task | Priority | Description |
|---|------|----------|-------------|
| D4.1 | **Multilingual RAG Pipeline** | **P1** | Vector embeddings + Gemini API |
| D4.2 | Cross-Language Intent Recognition Test | P1 | Chinese/French query validation |
| D4.3 | E2E Integration + Documentation | P0 | Code Freeze, full-chain verification |

---

## Product Decisions Reference (Frozen 2026-06-09)

| Decision | Conclusion | Sprint Impact |
|----------|-----------|---------------|
| D1 | Email + password (bcrypt) | S2: B2.3 |
| D2 | No token = Guest | S2: B2.3 |
| D3 | Anonymize after submission, keep `anonymous` | S3: B3.3 |
| D4 | Three levels `quiet/moderate/busy`, NULL = no data | S3: D3.2 |
| D5 | OpenAPI 8 issue_type values | S3: B3.3 |
| D6 | Confirmation overwrite, `UNIQUE (report_id, user_id)` | S3: B3.3 |
| D7 | No `auth_subject` needed | S2: B2.3 |
| D8 | Dictionary table `report_categories` (filter by venue type) | S3: B3.3 |
| D9 | MySQL JSON/BLOB for RAG embeddings | S4: D4.1 |
| D10 | Strict local storage, no cloud sync | S2: B2.4 |

---

## Database Table Dependencies

```
Phase 1: venues (exists) + venue_source_links (exists)
    ↓
Phase 2: users (new) → user_favorite_venues (new) + notification_preferences (new)
    ↓
Phase 3: user_reports (+user_id FK) + report_confirmations (+user_id FK) + report_categories (new)
    ↓
Phase 4: busyness_forecasts (new, separate from busyness_scores)
    ↓
Phase 5: RAG index + vector storage
    ↓
Phase 6: Verification + cleanup
```

## New Tables Checklist

| Table | Sprint | Priority | DDL Location | Status |
|-------|--------|----------|--------------|--------|
| `users` | S2 | P0 | execution-plan.md Phase 2 | ✅ 2026-06-09 |
| `user_favorite_venues` | S2 | P1 | execution-plan.md Phase 2 | ✅ 2026-06-09 |
| `notification_preferences` | S2 | P1 | execution-plan.md Phase 2 | ✅ 2026-06-09 |
| `report_categories` | S3 | P2 | execution-plan.md Phase 3 | ✅ 2026-06-09 |
| `busyness_forecasts` | S3 | P1 | execution-plan.md Phase 4 | ✅ 2026-06-09 |
| `venue_embeddings` | S4 | P1 | execution-plan.md Phase 5 | ✅ 2026-06-09 |

## Current Blockers

| Blocker | Impact | Resolution | Status |
|---------|--------|------------|--------|
| ~~No `users` table~~ | All S2/S3 user features | Phase 2: Create users table | ✅ 2026-06-09 |
| ~~`user_reports` missing `user_id`~~ | Reports can't bind to users | Phase 3: ALTER TABLE | ✅ 2026-06-09 |
| ~~`busyness_forecasts` not created~~ | 12h forecast has no storage | Phase 4: Create new table | ✅ 2026-06-09 |
| ~~Docker schema not synced~~ | Deployment structure mismatch | Manual copy test schema → docker | ✅ 2026-06-09 |
