# ClearPath 需求文档 — Features, Criteria & Architecture

> Source: `(Final)ClearPathfaeturesandcriteria.docx` (2026-06-09 转录)

---

## Section 1: User Stories & Acceptance Criteria

所有 user story 遵循 Agile 格式: "As a [persona], I want to [action], so that [benefit]."
Acceptance Criteria 使用 BDD "Given-When-Then" 格式。

### 1.1 Find — Venue Discovery & Language Filter

| ID | Story |
|---|---|
| US-01 | Find a clinic in language of user |
| US-02 | Find a clinic in language of user |
| US-03 | See which facilities are wheelchair accessible (wheelmap.org dataset) |

### 1.2 Report — Waze-Style Community Reporting

| ID | Story |
|---|---|
| US-04 | Report a broken lift or facility issue |
| US-05 | Real-time map update and expiration for alerts |
| US-06 | Confirm or resolve an existing report |

### 1.3 Predict — ML Busyness Forecast

| ID | Story |
|---|---|
| US-07 | View clinic busyness levels and 12-hour forecasts |
| US-08 | Setup busyness alerts and venue coverage controls |
| US-09 | See the fastest way to get to a venue |

### 1.4 Assist — SOS, Chatbot & Show Staff

| ID | Story |
|---|---|
| US-10 | Trigger emergency SOS |
| US-11 | Use the AI chatbot in my language |
| US-12 | Accessibility and medical integration of the Show Staff card |
| US-13 | Save a medical profile - user profile |
| US-14 | Cross-Platform Medical Passport PDF Generation (Web Only) |

---

## Section 2: Feature Definitions

---

### F-01 Interactive Venue Map

- **Performance**: Map loads within 5 seconds on standard mobile connection
- **Gesture Controls**: Pinch-to-zoom and pan
- **Cross-Platform**: Mobile = venue detail bottom sheet; Web = left detail drawer
- **Quick Filter Chips**: Clinics, Pharmacy, AED, Toilets under search bar
- **Unified Four-Tier Color Legend**:
  - 🟢 Green (Quiet): < 30% capacity load
  - 🟡 Yellow (Moderate): 30%–70% capacity load
  - 🔴 Red (Busy): > 70% capacity load
  - 🔵 Blue (No Live Info): predictive mode or telemetry unavailable
- **Reporting Badges**: Warning badge overlay when active community report exists
- **Floating Navigation Buttons**: Mobile = red [SOS] + yellow [Reporting]; Web = blue [AI Assistant]
- **User Location**: Mobile = blue dot with GPS accuracy ring; Web = black position label "You"
- **Basemap**: Google Maps API with OpenStreetMap fallback

### F-02 Language Filter

- **Purpose**: Search/restrict visible map pins by venue's verified supported languages
- **Dual-Field Input**: Primary Language + Secondary Language (Optional)
- **Supported Languages**: ANY language at launch
- **Client-side Filtering**: For speed; data from database seed
- **Default Persistence**: Saved to user profile, auto-applied on launch

### F-03 Accessibility Filter

- **Toggle**: Single "Full Wheelchair Access" switch
- **No GPS Required**: Pure data-field filter on venue attributes
- **Live Report Cross-Reference**: Excludes venues with flagged broken lifts
- **UI Badge**: "Full Access" on matching venue list cards
- **Multi-Filter**: Combines simultaneously with Language Filter

### F-04 One-Tap Icon Reporting (Mobile Only)

- **GPS Gate**: Disabled GPS → mandatory alert modal with [Go to System Settings] / [Cancel]
- **Path A (Bind to Nearby Spot)**: Select venue within 30m radius; red-tinted Critical Alert Strip
- **Path B (Use My Current Location)**: Bind to GPS coordinates; standalone yellow triangle pin within 30s
- **8-Grid Icon Layout**: Structural barriers with icons, no text boxes; Path B = all 8 unlocked; Path A = context-filtered
- **Report Categories Pool**: Elevator Broken, Long Waiting Time, Ramp Blocked, Closed Early, etc.
- **Authentication Guard**: Guest can view reports, cannot submit without login
- **Automated Expiration**: Reports expire after 2 hours unless validated

### F-05 Confirm / Resolve Chips

- **Path A (Bottom Sheet)**: Red card header + "Is this still an issue? (N users confirmed)" + [Confirm](Red) / [Resolve](Light Blue)
- **Path B (Map Pop-up)**: Callout box + timestamp + [Confirm](Blue) / [Resolve](White Outline)
- **Web Read-Only Mode**: No interactive buttons; static text/pill token summaries
- **Expiration Reset**: Confirm = +1 confirmation + fresh 2-hour countdown
- **Resolution**: Status resolved → remove badge/pin from map; log timestamp
- **3+ Confirmations**: Dynamic "N users confirmed" badge
- **Data Logging**: All verification events logged to backend for ML training pipeline
- **Authentication Guard**: Guest can view, cannot interact with verification

### F-06 Live Busyness Heatmap

- **Color Legend**: Same 4-tier as F-01 (Green/Yellow/Red/Blue)
- **Real-time Pin Updates**: From `busyness_scores` database table
- **Venue Detail Panel**: Current busyness level + estimated wait time + last updated timestamp
- **ML Model Features**: Google Maps live data, taxi trip density, weather, time of day (scikit-learn)
- **Client Caching**: 5 minutes before re-fetching
- **Fallback**: "Busyness data temporarily unavailable" + Blue pin

### F-07 12-Hour Forecast Bar Chart (Mobile + Web)

- **12 Vertical Bars**: Hourly color-coded (Green < 30%, Yellow 30–70%, Red > 70%)
- **Optimal Window**: Quietest hour gets green border + "Best time today" label
- **Interactive Tooltip**: Tap/hover → predicted busyness % + estimated wait time
- **Set Reminder**: Schedule push notification for when venue goes Green
- **Server Caching**: 1-hour cache for 12-hour prediction data
- **Mobile**: react-native-svg; Web: responsive SVG charting library

### F-08 AI-Driven Clinic Leaderboard & Insight Cards (Web Only)

- **District Filter**: Uptown, Midtown East, Downtown buttons → dynamic data update
- **Top Section Cards**:
  - Real-Time Density Card (occupancy + capacity status)
  - Quickest Triage Card (shortest wait clinic)
  - Best Travel Window Card (optimal time slot)
- **Middle Section Charts** (toggle):
  - 7-Day Crowding Trends (historical line/area chart)
  - 12-Hour Capacity Forecast (predictive bar chart, Green/Yellow/Red)
- **Bottom Section**: Top 3 Fastest Hubs
  - Sort: Current Location Distance + Live Wait Time
  - Display: name, density score progress bar, wait time, language badges

### F-09 SOS Emergency Button (Mobile Only)

- **Omnipresent**: Red SOS button on ALL mobile map/search screens
- **Full-Screen Overlay**: Crimson Emergency Alert Overlay page
- **5-Second Countdown**: "SOS ACTIVE 00:05" → auto-dial 112/999 + broadcast GPS
- **Accidental Activation Guard**: Hold 3s to cancel
- **Offline Operation**: Native dialler + on-screen medical profile text
- **Pre-translated Dispatches**: GPS in DMS format + Google Maps URL

### F-10 Multilingual AI Chatbot

- **Multilingual Mirroring**: Auto-detect input language → mirror in response
- **RAG Pipeline**: MySQL venue records + live busyness metrics via semantic embeddings
- **Gemini API**: Summary generation grounded in retrieved DB context
- **Suggested Prompts**: "Find an urgent care near me", "Which clinics are open now?", "I have no insurance — where can I go?"
- **Source Traceability**: Every recommendation shows venue name + distance
- **Anti-Hallucination Fallback**: Zero matches → "I couldn't find a match."
- **Privacy-First**: Chat history in client-side localStorage only
- **Latency Target**: < 3 seconds
- **Voice Input**: Blue mic dictation toggle for speech-to-text

### F-11 Show Staff Bilingual Card

- **Bilingual Display**: English + user's chosen language
- **Minimum Font Size**: 32px for desk readability
- **Screen Brightness**: Auto-maximize to 100% in card view; restore on exit
- **Input Options**:
  - Option A: Pre-made emergency/general templates
  - Option B: Custom free-text with live translation
- **Medical Profile Integration**: Auto-append conditions, allergies, medications
- **Layout Variants**: General Visit (standard) vs Emergency (red high-contrast)
- **Landscape Mode**: Manual or sensor-driven rotation
- **Fallback Message**: "This visitor speaks [language]. They need medical assistance."

### F-12 Medical Profile & Saved Data

- **Data Tiering** (2026-06-15 需求变更):
  - **Tier 1 — Profile Group (Cloud MySQL)**: User ID [Read-Only], Email [Read-Only], Full Name [Read-Only], Phone [Editable & Synced], Languages [Editable & Synced], Nationality [Editable & Synced] → sync via `GET/PUT /api/v1/user/profile`, stored in MySQL `users` table
  - **Tier 2 — Medical ID Group (100% Mobile Local Storage)**: Date of Birth (DOB), Gender, Address, Emergency Contact, Blood Type, Allergies, Medical Conditions → editable via Mobile App ONLY, completely isolated from cloud MySQL tables, Web fields disabled/greyed out
- **Web Restriction**: Medical ID input fields on Web Page 5 are disabled/greyed out with a prompt directing users to edit exclusively via Mobile
- **Auto-Population**: Medical ID → SOS Alert (F-09) + Show Staff Card (F-11) — all from local storage, no cloud read
- **Delete All Data**: Settings button → complete local wipe (Tier 2) + server-side cascade purge (Tier 1, GDPR F-13)
- **Optional Photo**: Camera/gallery for profile photo (local-only)

### F-13 User Sign-Up & Authentication

- **Auth Method**: Email + full name + password (no Google OAuth)
- **Guest Mode**: Browse map, search clinics, read reports, use chatbot
- **Auth Required**: Submit report (F-04) / use verification chips (F-05)
- **Server Sync Scope** (2026-06-15 需求变更):
  - **Cloud Sync** (Tier 1 Profile Group): User ID [Read-Only], Email [Read-Only], Full Name [Read-Only], Phone [Editable], Languages [Editable], Nationality [Editable] → MySQL via `GET/PUT /api/v1/user/profile`
  - **Local-Only** (Tier 2 Medical ID): DOB, Gender, Address, Emergency Contact, Blood Type, Allergies, Medical Conditions → 100% local on Mobile, never synced to cloud
- **Medical Profile**: 100% local-only on Mobile; Web fields greyed out with "Edit via Mobile" prompt
- **Password Recovery**: Email tokenized verification links
- **GDPR Erasure**: Server-side cascade purge within 24h (Tier 1 data only)
- **JWT**: Flask-JWT-Extended for all authenticated API
- **Registration Intercept**: "Finish Profile & ID" / "Skip for Now" prompt

### F-14 Cross-Platform Medical Passport PDF (Web Only)

- **Entry**: [Print Medical Card] button in User Profile (Web)
- **Core Logic** (2026-06-15 需求变更): Implements strict data tiering. Medical ID data is 100% local-only on Mobile, never stored on cloud. Web client has no direct access to Medical ID records.
- **Print Execution Flow**:
  1. User clicks [Print Medical Card] on Web Page 5
  2. Web client fetches a short-lived **render_token** (JWT, 5-minute expiry) from backend
  3. Backend returns render_token → Web client displays it as a **dynamic QR Code**
  4. User scans the QR code using their **Mobile app camera**
  5. Mobile app triggers a **temporary frontend P2P encrypted channel** that pushes the local health JSON (Medical ID data) directly to the browser memory
  6. Web client renders the received data into an **A4 canvas** for immediate printing
  7. All data is **instantly purged** from browser memory upon tab closure
- **Bilingual A4**: "MEDICAL ALERT / ALERTA MÉDICA" dual-language layout
- **Fields**: Identity, blood type, allergies, conditions, contacts (all from local Mobile storage)
- **Output**: [Print My Medical Pass (PDF)] → native browser print/save
- **Privacy**: Zero Medical ID data stored in cloud; zero Medical ID data persisted in browser beyond tab lifetime
