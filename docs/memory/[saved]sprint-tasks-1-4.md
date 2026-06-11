# ClearPath Sprint 1-4 Task Summary

> Sources: Notion Sprint Backlog + Backend Lead Pipeline + Data Lead Pipeline
> Updated: 2026-06-10 | Synced from Notion
> Team: Hsu Ching Yun (H), fangxun.wu (F), David Irving (D), Joanna Saheed (J), Casey Liew (C), Emmett (E)

---

## Sprint 1 — Completed ✅

| Task | Week | Assignee | Status | Notion Est. (h) |
|------|------|----------|--------|:---------------:|
| Create Personas | Week 1 | All | ✅ | 1 |
| Interview | Week 1 | All | ✅ | 1 |
| Competitors Research | Week 1 | David, Joanna | ✅ | 1 |
| Project Planning & Backlog | Week 1 | Hsu Ching Yun | ✅ | — |
| Sprint 1 Planning & Backlog | Week 1 | Hsu Ching Yun | ✅ | — |
| Define Features | Week 2 | All | ✅ | — |
| System Architecture Diagram | Week 2 | Hsu Ching Yun | ✅ | — |
| Define User Stories | Week 2 | Hsu Ching Yun, Joanna | ✅ | — |
| Acceptance Criteria | Week 2 | Hsu Ching Yun, Joanna | ✅ | — |
| Create Git Repository & Branching | Week 2 | Hsu Ching Yun | ✅ | — |
| Dataset Source Exploration | Week 2 | fangxun.wu | ✅ | — |
| Raw Data Staging & Snapshot | Week 2 | fangxun.wu | ✅ | — |
| Secure API Handling | Week 2 | Emmett | ✅ | 1 |
| Create Mockups | Week 3 | Joanna, Hsu Ching Yun | ✅ | 10 |
| Supplemental Web Scraping Exploration | Week 3 | fangxun.wu | ✅ | 3 |
| API Endpoints Interfaces | Week 3 | Emmett, Casey, David, fangxun.wu | ✅ | 4 |
| Data Prototyping | Week 3 | Emmett | ✅ | — |
| API & Schema Alignment | Week 3 | fangxun.wu | ✅ | — |
| Database Initialization | Week 3 | fangxun.wu | ✅ | — |
| Sprint 2 Planning & backlog | Week 3 | Hsu Ching Yun | ✅ | — |
| Sprint Review & Retrospective | Week 3 | Hsu Ching Yun | ✅ | — |
| Tracking Table & Burn-Down Chart | Week 3 | Hsu Ching Yun | ✅ | — |
| API Contract Revision & Schema Alignment | Week 3 | Emmett | ✅ | — |

---

## Sprint 2 — Core Environment + Auth + Zoning (Week 4-5)

### 总工时: Est. 219h / Actual 8h

### Backend (Emmett)

| # | Task | Week | Description | Notion Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| B2.1 | Core pyproject.toml, Poetry & Flask Blueprints Setup | Week 5 | Initialize Poetry, Flask Blueprints (Health, User, Venues, Reports) | ❌ Not started | — |
| B2.2 | MySQL Table Activation & Connection Pooling | Week 4 | DDL execution + FK constraints + district index + SQLAlchemy pooling | ❌ Not started | 5 |
| B2.3 | Authentication Handshakes & Global App State Gateway | Week 5 | Register, login, temporary credential API handlers | ❌ Not started | — |
| B2.4 | Standard User Profile & Notification Preferences Persistence | Week 4 | Account personalization GET/PUT endpoints | ❌ Not started | 6 |
| B2.5 | Backend Core Unit Testing (Auth & Profile Guard) | Week 5 | — | ❌ Not started | — |

### Data (fangxun.wu)

| # | Task | Week | Description | Notion Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| D2.1 | ERD Revision, Schema Updates & District Zoning Setup | Week 4 | ERD update + 4 district nodes | 🔄 **In progress** | 5 |
| D2.2 | MySQL Table Implementation & Index Tuning | Week 4 | DDL scripts + FK constraints + composite indexes | ❌ Not started | 5 |
| D2.3 | Data Parsing & Ingestion | Week 5 | ETL: 349 restrooms, 900 healthcare, 431 NYS, 3,279 AEDs, 63 LASS | ❌ Not started | 10 |
| D2.4 | API & Map Mocking Data Arrays | Week 4 | JSON mock data grouped by lowercase district tokens | ❌ Not started | 6 |
| D2.5 | Zoned Historical Ingestion & ML Model Init (Advance Start) | Week 5 | [High Priority] Parse historical data, init ARIMA/LSTM | ❌ Not started | 10 |
| D2.6 | Data Deduplication & Multi-Source Cleansing Preprocessing | Week 5 | Python/Pandas spatial overlap resolution | ❌ Not started | 10 |
| D2.7 | Database Integrity, Privacy & Constraint Unit Testing | Week 5 | PyTest: 100% venues non-Null district classification | ❌ Not started | — |

### Mobile (David Irving)

| # | Task | Week | Description | Notion Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| M2.1 | Mobile Infrastructure & Navigation Architecture | Week 5 | Repository framework + design tokens + tab/stack navigation | ❌ Not started | 3 |
| M2.2 | Mobile Pages 1 & 3: Language & Location Permission Gateways | Week 4 | Language Selection + Location Permission | ❌ Not started | 10 |
| M2.3 | Mobile Page 2: Legal & Compliance Interface | Week 4 | Terms of Service + Privacy Policy + HIPAA | ❌ Not started | 10 |
| M2.4 | UI Component Binding with Mocks | Week 4 | Profile & Medical ID binding | ❌ Not started | 3 |
| M2.5 | Mobile Pages 4 & 5: Auth Switch & Registration Forms | Week 5 | Login/Register toggle, "Continue as Guest" | ❌ Not started | 10 |
| M2.6 | Mobile Page 5: Post-Registration Intercept Gateway (PRD Fix) | Week 5 | [PRD] Bottom sheet: "Finish Medical Profile?" | ❌ Not started | 10 |
| M2.7 | Mobile Pages 9/9-A/9-B: Master Profile & Medical ID | Week 5 | Health dashboard, editable forms, allergens, contacts | ❌ Not started | 10 |
| M2.8 | Mobile UI & State Validation Unit Testing | Week 5 | — | ❌ Not started | — |

### Web (Casey)

| # | Task | Week | Description | Notion Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| W2.1 | Baseline Workspace Init, Global Navigation Bar & Routing | Week 4 | Root framework + nav bar + multi-page routing (1-8) | ❌ Not started | 3 |
| W2.2 | UI Component Binding with Mocks | Week 4 | User Profile + Auth component binding | ❌ Not started | 3 |
| W2.3 | Web Page 1: Sign-In Gateway & Location Modal Trigger | Week 4 | Split-screen portal + dark mask + Geolocation API | ❌ Not started | 10 |
| W2.4 | Web Page 6: User Profile View & Editable Form Setup | Week 4 | Health dossier + languages + blood type + allergens + Print Medical Card | ❌ Not started | 10 |
| W2.5 | Web Page 7: Medical Passport & PDF Document Generation | Week 5 | Bilingual A4 medical alert + [Print My Medical Pass (PDF)] | ❌ Not started | — |
| W2.6 | Web Page 8 (Phase 1): Account Settings & Notification Prefs | Week 5 | — | ❌ Not started | — |
| W2.7 | Web UI & State Validation Unit Testing | Week 5 | — | ❌ Not started | — |

### Design (Joanna Saheed)

| # | Task | Week | Description | Notion Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| J2.1 | User Testing to Finalize UI | Week 4 | 3-5 target users testing Figma prototypes | ❌ Not started | 5 |

### 跨团队/其他任务

| # | Task | Week | Description | Assignee | Notion Status |
|---|------|------|-------------|----------|:------------:|
| O2.1 | Sprint 3 Planning & backlog | Week 4 | Detail Sprint 3 tasks & estimations | H | ✅ Done |
| O2.2 | Presentation Preparation | Week 5 | — | — | ❌ Not started |
| O2.3 | Sprint Review & Retrospective | Week 5 | — | — | ❌ Not started |
| O2.4 | Tracking Table & Burn-Down Chart | Week 5 | — | — | ❌ Not started |
| O2.5 | Integration Test: Session Scaffolding & Profile Durability | Week 5 | — | QA | ❌ Not started |

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
| D4 | **Four levels** `quiet/moderate/busy/no_data` (F-06 color alignment) | S3: D3.2 |
| D5 | OpenAPI 8 issue_type values | S3: B3.3 |
| D6 | Confirmation overwrite, `UNIQUE (report_id, user_id)` | S3: B3.3 |
| D7 | No `auth_subject` needed | S2: B2.3 |
| D8 | Dictionary table `report_categories` (filter by venue type) | S3: B3.3 |
| D9 | MySQL JSON/BLOB for RAG embeddings | S4: D4.1 |
| D10 | Cloud encrypted storage (AES-256-GCM), no local copy | S2: B2.4 |

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
