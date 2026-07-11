# Sprint 3–4 Data — Canonical Contract & Frozen Baseline (Stage 0)

> SOP Stage 0 exit artifact. This file is the single source of truth for the canonical
> contracts (medical table, report categories, venue types, fallback markers) and records
> the new/old volume smoke-check evidence. Do not proceed to Stage 1 cross-layer edits
> against any contract still marked **UNDECIDED**.

## 0.1 Frozen baseline

| Item | Value |
|------|-------|
| Base branch | `main` |
| Base commit SHA | `305f989e2bd8eb6326937140fed3f9c985baad37` |
| Execution branch | `data/sprint3-4-contract-convergence` |
| Compose | `docker-compose.yml` — mysql `mysql:8.4`, redis `7-alpine`, phpmyadmin |
| Live DB volume | `group6_summer-project_clearpath_mysql_data` — **EXISTING / pre-populated** (4843 venues) |
| Init scripts | `docker/mysql/init/001…007` (7 files) |
| Date | 2026-07-10 |

Constraint for this workstream: **do not modify backend files** (`backend/src/**`, `openapi.yaml`).
Backend/contract mismatches are logged in the register below with owner = Backend and must be
fixed by that owner; Data-owned changes are limited to `docker/mysql/**`, seeds, DDL, and frontend.

---

## 0.2 Canonical contract list

### C1 — Medical profile table (DECIDED)
- **Canonical table name:** `medical_profiles` (consistent across DDL, backend `user.py`, chatbot forbidden list).
- **Canonical storage shape:** single encrypted column **`encrypted_payload`** (backend `user.py` reads/writes
  `SELECT/INSERT ... encrypted_payload`; `medical_crypto.py` docstring documents the same).
- **CONFLICT (P0):** DDL `004_medical_profiles.sql` defines *plaintext* columns
  (`date_of_birth, gender, address, blood_type, allergies, conditions, medications, emergency_contacts`)
  and **no `encrypted_payload` column**. Confirmed on both old and new volumes → every deploy ships a
  `medical_profiles` table that backend GET/PUT/DELETE cannot use. **Data-owned fix** (Stage 1): rewrite
  `004` to the encrypted-payload shape (`user_id PK`, `encrypted_payload`, `created_at`, `updated_at`,
  FK CASCADE) to match backend. No naming conflict — column-shape only.

### C2 — Report categories (DECIDED: 9)
- **Canonical set (9), source of truth = `openapi.yaml` ReportSubmission enum + DB FK dictionary:**
  `elevator_broken, wheelchair_lift_broken, toilet_out_of_order, large_crowd, long_waiting_time,
  protest_or_blockage, entrance_closed, ramp_blocked, closed_early`
- **Aligned:** DDL FK `fk_report_category` → `report_categories`; seed `006` (9 rows); OpenAPI enum (9);
  live + fresh DB both hold 9 rows. ✓
- **CONFLICT (P1, Backend-owned):** `backend/src/api/reports.py ALLOWED_REPORT_TYPES` has only **6**
  (missing `long_waiting_time, ramp_blocked, closed_early`) → those 3 valid categories are rejected at
  submit. Also `ISSUE_TYPE_LABELS` text diverges from seed/OpenAPI labels
  (e.g. "Toilet Out of Order" vs "Toilet out of service", "Large Crowd" vs "Too Crowded",
  "Entrance Closed" vs "Entrance Blocked"). **RECORD — Backend must expand to 9 + align labels.**
- **CONFLICT (P2, Contract-owned):** OpenAPI prose says "all **8** labels/entries" while its own enum lists **9**.
  Stale doc text. **RECORD — Backend/OpenAPI owner fixes wording to 9.**

### C3 — Venue types (DECIDED: data/OpenAPI set)
- **Canonical enum = the set present in production data + OpenAPI:**
  `restroom, healthcare, emergencyasset, clinic, pharmacy, hospital` (OpenAPI additionally reserves
  `dentist, laboratory` — permitted, currently unused in data).
- **`restroom` and AED口径 (DECIDED):**
  - `restroom` is a **venue_type** (474 live rows; has `restroom_profiles` attribute table).
  - AED is venue_type **`emergencyasset`** (3280 live rows) **plus** the `emergency_assets` attribute table
    (`asset_type ENUM('aed')`). AED is NOT its own venue_type — it is `emergencyasset` + attribute rows.
- **CONFLICT (P0, Backend-owned):** `backend/src/api/venues.py VALID_VENUE_TYPES =
  {hospital, clinic, pharmacy, urgent_care, mental_health, shelter}` — matches **0.06%** of live venues
  and rejects `restroom/healthcare/emergencyasset` (99.9% of data) as "Unknown venue type".
  **RECORD — Backend must replace VALID_VENUE_TYPES with the canonical set.**
- Data-owned follow-up (Stage 1): venue seed `005` lacks a `healthcare`-type row though it is the 2nd-largest
  live type; consider adding for representative filter coverage.

### C4 — Insights / reports fallback markers (PARTIALLY DECIDED)
- **Observed markers today:**
  - `venues.py`: `data_mode ∈ {live, predicted, forecast, mock}`, plus `forecast_source ∈
    {busyness_forecasts, busyness_scores.forecast_1h, mock_data}`, `no_data` colour path.
  - `insights.py`: `data_mode ∈ {db, mock}`; falls back to `mock_data.INSIGHTS_DASHBOARD` when DB unavailable.
- **UNDECIDED (Stage 2 gate):** (a) whether `INSIGHTS_DASHBOARD` mock is dev-only or fully banned;
  (b) unified `no_data` / partial-payload shape when DB reachable but empty; (c) whether `formula_version`
  / `fallback_reason` are required fields. These are frozen in Stage 2 before any fallback-related edits.
  Contract-schema decisions here need Backend + Frontend sign-off (recorded, not edited under this workstream).

---

## 0.3 Volume smoke-check evidence

### Old volume (live `clearpath-mysql`, existing data) — read-only
| Check | Result |
|-------|--------|
| Tables | 23 |
| `report_categories` | 9 (all canonical ids) ✓ |
| `medical_profiles` columns | plaintext set, **no `encrypted_payload`** ✗ (C1 P0) |
| `venues` | 4843 — emergencyasset 3280, healthcare 1086, restroom 474, clinic/pharmacy/hospital 1 each |
| `telemetry_audit_log` | present ✓ |

### New volume (throwaway `mysql:8.4`, fresh volume, init 001–007) — non-destructive
| Check | Result |
|-------|--------|
| Init applied | clean, all 7 scripts ✓ |
| Tables | 21 |
| `report_categories` | 9 ✓ (seed repeatable on fresh volume) |
| `medical_profiles` columns | plaintext, **no `encrypted_payload`** ✗ (C1 reproducible on every deploy) |
| `venues` seed | 5 rows — restroom, emergencyasset, clinic, pharmacy, hospital (no `healthcare` row) |

### Schema drift (old vs new)
- Live has **23** tables; fresh init produces **21**. The 2 tables present in live but **not created by any
  `docker/mysql/init/` script**: `healthcare_prediction_groups`, `healthcare_prediction_group_members`.
  → Reproducibility gap: a clean deploy will not have them. Stage 1 must locate their DDL source
  (ML pipeline / out-of-band migration) and either add to `init/` or document as pipeline-created.

---

## 0.4 Stage 0 exit gate

| Gate | Status |
|------|--------|
| Fixed contract list exists | ✅ (C1–C3 decided, C4 partially — C4 finalised in Stage 2) |
| Old + new volume baseline captured | ✅ |
| "Write-fail silently returns mock success" path forbidden | ⏳ verify in Stage 2 (venues.py `pass  # Fallback to mock` paths flagged) |

**Cleared to enter Stage 1** for the P0 Data-owned items (C1 DDL rewrite, C3 seed coverage, drift tables).
Backend-owned P0/P1 items (C2 ALLOWED_REPORT_TYPES, C3 VALID_VENUE_TYPES, labels, OpenAPI "8"→"9")
are **recorded here for the Backend owner** and are out of scope for this no-backend-edit workstream.
