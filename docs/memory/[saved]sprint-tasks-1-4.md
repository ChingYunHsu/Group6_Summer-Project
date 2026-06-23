# ClearPath Sprint 1-4 Task Summary

> Sources: Notion Sprint Backlog + Backend Lead Pipeline + Data Lead Pipeline + session-log.md
> Updated: 2026-06-23 | Progress audit from codebase + memory files + Sprint 3 fangxun.wu workstream
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

| # | Task | Week | Description | Actual Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| B2.1 | Core pyproject.toml, Poetry & Flask Blueprints Setup | Week 5 | Initialize Poetry, Flask Blueprints (Health, User, Venues, Reports) | ✅ 2026-06-08 | — |
| B2.2 | MySQL Table Activation & Connection Pooling | Week 4 | DDL execution + FK constraints + district index + SQLAlchemy pooling | ✅ 2026-06-09 | 5 |
| B2.3 | Authentication Handshakes & Global App State Gateway | Week 5 | Register, login, temporary credential API handlers | ❌ Not started | — |
| B2.4 | Standard User Profile & Notification Preferences Persistence | Week 4 | Account personalization GET/PUT endpoints | ❌ Not started | 6 |
| B2.5 | Backend Core Unit Testing (Auth & Profile Guard) | Week 5 | — | ❌ Not started | — |
| D2.4 | API & Map Mocking Data Arrays *(reassigned from Data)* | Week 4 | JSON mock data grouped by lowercase district tokens; expand `mock_data.py` with 20+ venues across 4 districts | ⚠️ 部分完成 | 6 |

### Data (fangxun.wu)

| # | Task | Week | Description | Actual Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| D2.1 | ERD Revision, Schema Updates & District Zoning Setup | Week 4 | ERD update + 4 district nodes | ✅ 2026-06-09 | 5 |
| D2.2 | MySQL Table Implementation & Index Tuning | Week 4 | DDL scripts + FK constraints + composite indexes | ✅ 2026-06-09 | 5 |
| D2.3 | Data Parsing & Ingestion | Week 5 | ETL: 349 restrooms, 900 healthcare, 431 NYS, 3,279 AEDs, 63 LASS | ✅ 2026-06-05 | 10 |
| D2.5 | Zoned Historical Ingestion & ML Model Init (Advance Start) | Week 5 | [High Priority] traffic_hourly.csv fetched; ARIMA/LSTM pending | ⚠️ 进行中 | 10 |
| D2.6 | Data Deduplication & Multi-Source Cleansing Preprocessing | Week 5 | GPS duplicate detection (grid+haversine, lat-scaled) | ✅ 2026-06-11 | 10 |
| D2.7 | Database Integrity, Privacy & Constraint Unit Testing | Week 5 | PyTest: 12 test cases (D2.7, GPS, export, immutability) | ✅ 2026-06-11 | — |

### Mobile (David Irving)

| # | Task | Week | Description | Actual Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| M2.1 | Mobile Infrastructure & Navigation Architecture | Week 5 | Repository framework + design tokens + tab/stack navigation | ✅ 2026-06-08 | 3 |
| M2.2 | Mobile Pages 1 & 3: Language & Location Permission Gateways | Week 4 | Language Selection (index.tsx) + Location Permission (location.tsx) | ✅ 2026-06-08 | 10 |
| M2.3 | Mobile Page 2: Legal & Compliance Interface | Week 4 | Terms of Service + Privacy Policy + HIPAA (legal.tsx) | ✅ 2026-06-08 | 10 |
| M2.4 | UI Component Binding with Mocks | Week 4 | Profile & Medical ID binding | ❌ Not started | 3 |
| M2.5 | Mobile Pages 4 & 5: Auth Switch & Registration Forms | Week 5 | Login/Register toggle (auth-gateway.tsx + login.tsx) | ✅ 2026-06-08 | 10 |
| M2.6 | Mobile Page 5: Post-Registration Intercept Gateway (PRD Fix) | Week 5 | [PRD] Bottom sheet: "Finish Medical Profile?" | ❌ Not started | 10 |
| M2.7 | Mobile Pages 9/9-A/9-B: Master Profile & Medical ID | Week 5 | Health dashboard, editable forms, allergens, contacts | ❌ Not started | 10 |
| M2.8 | Mobile UI & State Validation Unit Testing | Week 5 | — | ❌ Not started | — |

### Web (Casey)

| # | Task | Week | Description | Actual Status | Est. (h) |
|---|------|------|-------------|:-------------:|:--------:|
| W2.1 | Baseline Workspace Init, Global Navigation Bar & Routing | Week 4 | Root framework + nav bar + multi-page routing (1-8) | ✅ 2026-06-10 | 3 |
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

| # | Task | Week | Description | Assignee | Actual Status |
|---|------|------|-------------|----------|:------------:|
| O2.1 | Sprint 3 Planning & backlog | Week 4 | Detail Sprint 3 tasks & estimations | H | ✅ Done |
| O2.2 | Presentation Preparation | Week 5 | — | — | ❌ Not started |
| O2.3 | Sprint Review & Retrospective | Week 5 | — | — | ❌ Not started |
| O2.4 | Tracking Table & Burn-Down Chart | Week 5 | — | — | ❌ Not started |
| O2.5 | Integration Test: Session Scaffolding & Profile Durability | Week 5 | — | QA | ❌ Not started |

---

### Sprint 2 进度总结 (2026-06-15)

**整体进度**: 约 45% 完成

| 模块 | 完成 | 进行中 | 未开始 | 进度 |
|------|------|--------|--------|------|
| Data (fangxun.wu) | 4/6 | 1/6 | 1/6 | 67% |
| Mobile (David Irving) | 4/8 | 0/8 | 4/8 | 50% |
| Web (Casey) | 1/7 | 0/7 | 6/7 | 14% |
| Backend (Emmett) | 2/6 | 1/6 | 3/6 | 38% |
| Design (Joanna) | 0/1 | 0/1 | 1/1 | 0% |
| 跨团队 | 1/5 | 0/5 | 4/5 | 20% |

**关键完成项**:
- ✅ D2.1-D2.3: ERD、Schema、ETL 数据摄取 (7 sources, ~30K rows)
- ✅ D2.6: GPS 重复检测 (grid+haversine, lat-scaled)
- ✅ D2.7: 12 pytest 用例 (D2.7, GPS, export, immutability)
- ✅ M2.1-M2.3, M2.5: Mobile 基础架构 + 4 个页面 (Language, Location, Legal, Auth)
- ✅ W2.1: Web 基础架构 (Vite + React + BusynessChart)
- ✅ B2.1-B2.2: Flask Blueprints + MySQL 表激活

**关键阻塞项**:
- ⚠️ D2.5: ARIMA/LSTM 模型实现 (阻塞 Sprint 3)
- ⚠️ D2.4: Mock 数据扩展 (部分完成)
- ❌ B2.3: JWT Auth 未实现 (阻塞用户功能)
- ❌ M2.4, M2.6-M2.7: Mobile 绑定与高级页面
- ❌ W2.2-W2.7: Web 页面实现

**下一步优先级**:
1. D2.5 ML 模型实现 (解除 Sprint 3 阻塞)
2. B2.3 JWT Auth (解除用户功能阻塞)
3. D2.4 Mock 数据扩展
4. M2.4 Mobile 组件绑定

---

## Sprint 3 — Spatial Query + Reports + ML Production

> **前置依赖**: D2.5 ML 模型实现 (ARIMA/LSTM) — 目前进行中
> **计划开始**: Week 6-7 (待 Sprint 2 完成)

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

#### fangxun.wu Sprint 3 Data Workstream

> **说明**: 以下任务全部归属 Sprint 3 的 `fangxun.wu` 交付范围，并遵守当前 DB 设计：静态 `venues` 保持不变，实时/预测写动态层，医疗资料写加密表，TTL 采用状态化过期。

| Task | Notes |
|------|------|
| MySQL Keyring Configuration & Tablespace Encryption Integration | 仅作为加密医疗表前置能力；失败只阻断需要 `ENCRYPTION='Y'` 的迁移 |
| Encrypted User Medical Profile Schema Migration Setup | `user_medical_profiles` DDL + `ENCRYPTION='Y'` + `ON DELETE CASCADE`，仅存 Tier 2 医疗字段 |
| Real-Time MySQL Seed Venues Ingestion & Verification | 静态 seed 初始化，补足基础 venues 数据，不替代 ETL 权威源 |
| Real-Time Zoned Telemetry Pipeline | Live capacity + wait-time 写入动态 telemetry 层，不回写静态 `venues` |
| 12-Hour Capacity Forecasting Production Engine | 产出 12h 预测结果到 forecast 层，保持与前端消费结构一致 |
| Polymorphic Crowdsourced Ingestion Engine & 2-Hour TTL Pipeline | `user_reports` / `report_confirmations` 路由 + Redis/Celery 过期状态化，TTL 不做硬删除 |

---

## Sprint 4 — Account Deletion + AI Integration + E2E Tests

> **前置依赖**: Sprint 3 完成 (Reports, ML, Real-time)
> **计划开始**: Week 8-9 (待 Sprint 3 完成)

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

> **Status**: All 10 decisions (D1-D10) have been frozen and implemented in the schema.
> **Impact**: These decisions guide the implementation of Sprint 2-4 tasks.

| Decision | Conclusion | Sprint Impact | Implementation Status |
|----------|-----------|---------------|----------------------|
| D1 | Email + password (bcrypt) | S2: B2.3 | ❌ Not started |
| D2 | No token = Guest | S2: B2.3 | ❌ Not started |
| D3 | Anonymize after submission, keep `anonymous` | S3: B3.3 | ❌ Not started |
| D4 | **Four levels** `quiet/moderate/busy/no_data` (F-06 color alignment) | S3: D3.2 | ✅ Schema ready |
| D5 | OpenAPI 8 issue_type values | S3: B3.3 | ✅ Schema ready |
| D6 | Confirmation overwrite, `UNIQUE (report_id, user_id)` | S3: B3.3 | ✅ Schema ready |
| D7 | No `auth_subject` needed | S2: B2.3 | ✅ Schema ready |
| D8 | Dictionary table `report_categories` (filter by venue type) | S3: B3.3 | ✅ Table created |
| D9 | MySQL JSON/BLOB for RAG embeddings | S4: D4.1 | ✅ Table created |
| D10 | Cloud encrypted storage (AES-256-GCM), no local copy | S2: B2.4 | ❌ Not started |

---

## Database Table Dependencies

```
Phase 1: venues (exists) + venue_source_links (exists) ✅
    ↓
Phase 2: users (new) → user_favorite_venues (new) + notification_preferences (new) ✅
    ↓
Phase 3: user_reports (+user_id FK) + report_confirmations (+user_id FK) + report_categories (new) ✅
    ↓
Phase 4: busyness_forecasts (new, separate from busyness_scores) ✅
    ↓
Phase 5: RAG index + vector storage ✅
    ↓
Phase 6: Verification + cleanup ✅
```

> **Status**: All 6 phases have been completed as of 2026-06-09. Database schema is ready for Sprint 3-4 implementation.

## New Tables Checklist

| Table | Sprint | Priority | DDL Location | Status |
|-------|--------|----------|--------------|--------|
| `users` | S2 | P0 | execution-plan.md Phase 2 | ✅ 2026-06-09 |
| `user_favorite_venues` | S2 | P1 | execution-plan.md Phase 2 | ✅ 2026-06-09 |
| `notification_preferences` | S2 | P1 | execution-plan.md Phase 2 | ✅ 2026-06-09 |
| `report_categories` | S3 | P2 | execution-plan.md Phase 3 | ✅ 2026-06-09 |
| `busyness_forecasts` | S3 | P1 | execution-plan.md Phase 4 | ✅ 2026-06-09 |
| `venue_embeddings` | S4 | P1 | execution-plan.md Phase 5 | ✅ 2026-06-09 |

> **Note**: All 6 new tables have been created as of 2026-06-09. Schema is ready for Sprint 3-4 implementation.

## Current Blockers

| Blocker | Impact | Resolution | Status |
|---------|--------|------------|--------|
| ~~No `users` table~~ | All S2/S3 user features | Phase 2: Create users table | ✅ 2026-06-09 |
| ~~`user_reports` missing `user_id`~~ | Reports can't bind to users | Phase 3: ALTER TABLE | ✅ 2026-06-09 |
| ~~`busyness_forecasts` not created~~ | 12h forecast has no storage | Phase 4: Create new table | ✅ 2026-06-09 |
| ~~Docker schema not synced~~ | Deployment structure mismatch | Manual copy test schema → docker | ✅ 2026-06-09 |
| D2.5 ARIMA/LSTM 模型未实现 | 阻塞 Sprint 3 ML 预测 | fangxun.wu 实现中 | ⚠️ 进行中 |
| D2.4 Mock 数据不完整 | 部分 API 端点无测试数据 | 扩展 mock_data.py | ⚠️ 部分完成 |
| B2.3 JWT Auth 未实现 | 用户功能无法使用 | Emmett 实现 | ❌ 未开始 |

---

## 整体项目进度 (2026-06-15)

### Sprint 完成度

| Sprint | 进度 | 状态 |
|--------|------|------|
| Sprint 1 | 100% | ✅ 完成 |
| Sprint 2 | 45% | 🔄 进行中 |
| Sprint 3 | 0% | ⏳ 待开始 |
| Sprint 4 | 0% | ⏳ 待开始 |

### 关键里程碑

- ✅ **2026-06-09**: 10 项产品决策冻结 (D1-D10)
- ✅ **2026-06-09**: 数据库 Schema 完成 (19 tables)
- ✅ **2026-06-05**: ETL 数据摄取完成 (7 sources, ~30K rows)
- ✅ **2026-06-08**: Mobile 基础架构完成 (Expo Router, 4 pages)
- ✅ **2026-06-10**: Web 基础架构完成 (Vite + React)
- ✅ **2026-06-11**: DQR Pipeline 完成 (6 shared modules, 12 tests)
- ⏳ **待定**: Sprint 2 完成 → Sprint 3 开始

### 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| D2.5 ML 模型延迟 | Sprint 3 无法开始 | 优先实现 ARIMA/LSTM |
| JWT Auth 未实现 | 用户功能阻塞 | 分配资源实现 B2.3 |
| Mock 数据不完整 | API 测试受限 | 扩展 mock_data.py |

### 下一步行动

1. **立即**: 完成 D2.5 ARIMA/LSTM 模型实现
2. **本周**: 实现 B2.3 JWT Auth
3. **下周**: 扩展 D2.4 Mock 数据
4. **两周后**: 开始 Sprint 3 (Spatial Query + Reports)
