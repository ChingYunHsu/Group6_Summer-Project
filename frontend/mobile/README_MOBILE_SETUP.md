# ClearPath Mobile Setup Guide

This covers everything needed to get the mobile app (`frontend/mobile`) running on a fresh machine, for iOS Simulator, Android Emulator, and real physical devices, plus running the test suites.

---

## 1. Prerequisites: install these first

| Tool | Why | Notes |
| --- | --- | --- |
| **Node.js** (LTS) | Runs the JS toolchain | Check with `node -v` |
| **npm** | Package manager | Comes with Node |
| **Xcode** (Mac only) | iOS Simulator | Install from the App Store. Also installs the iOS Simulator and command line tools. |
| **Android Studio** | Android Emulator + SDK | developer.android.com/studio |
| **JDK 17** | Required for Android native builds | **Must be JDK 17 specifically**, newer JDKs (21+) break the native build with a `JvmVendorSpec` error. Install via `brew install --cask zulu17` if on macOS. |
| **Maestro** | End-to-end test runner | `curl -Ls "https://get.maestro.mobile.dev" \| bash` |

### Environment variables (add to your shell profile, e.g. `~/.zshrc`)

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v17)
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH="$PATH:$ANDROID_HOME/platform-tools"
export PATH="$PATH:$HOME/.maestro/bin"
```

Reload your shell (`source ~/.zshrc`) or open a new terminal after adding these.

---

## 2. Install project dependencies

```bash
cd frontend/mobile
npm install
```

---

## 3. Required config files (not committed to git, you need to create these yourself)

### `frontend/mobile/.env`

```bash
touch .env
```

```
EXPO_PUBLIC_API_KEY=development
EXPO_PUBLIC_API_HOST=<only needed for testing on a real physical device (see Section 7)>
```

`EXPO_PUBLIC_API_KEY` is read by `src/services/api.ts` and sent as the `X-API-Key` header on every request, locally this is just the fixed value `"development"`.

### `backend/.env`

Copy `backend/.env.example` and fill in:

| Key | Required for | If missing |
| --- | --- | --- |
| `API_KEY` | Every single API request | Every request from the app returns `401`. Use `"development"` locally. |
| `JWT_SECRET` | Login, registration, session tokens | **Not required locally** `backend/src/settings.py` falls back to a hardcoded `"dev-insecure-jwt-secret"` value if unset, so auth still works fine. Worth setting a real value anyway, since that fallback is public/insecure and shouldn't be relied on beyond casual local testing (e.g. never for a real deployment). |
| `MEDICAL_PROFILE_ENCRYPTION_KEY` | Saving/loading Medical ID | Medical ID save/load fails; rest of the app is unaffected. Generation steps for this value are documented directly in `backend/.env.example`. |
| `GEMINI_API_KEY` | The Assistant chatbot | Chatbot responds with a generic error; rest of the app is unaffected |
| `GOOGLE_MAPS_API_KEY` | `/routes` endpoints (Directions) | Getting directions to a venue fails; the map itself still renders fine |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` | Everything backed by the database | Match the defaults already set in `docker-compose.yml` |

### Google Maps API key (Android only)

Android needs its own Maps SDK key, separate from any iOS key, added to `app.json`:

```json
{
  "expo": {
    "android": {
      "config": {
        "googleMaps": {
          "apiKey": "YOUR_ANDROID_MAPS_KEY_HERE"
        }
      }
    }
  }
}
```

Get a key from Google Cloud Console → APIs & Services → Credentials, restricted to "Android apps" with the "Maps SDK for Android" API enabled. Without this, the map screen will fail to render on Android with no clear error message.

**Note:** this key is currently committed in plain text in `app.json` for convenience. Longer term, this should move to `app.config.js` reading from a gitignored `.env` value instead, since Maps keys shouldn't sit in a public repo history even though they're client-restricted.

### Chatbot venue citations (`venue_embeddings`)

The Assistant's citation system (linking a chatbot response to real venues) depends on a populated `venue_embeddings` table. If this is empty or stale, the chatbot may still respond to questions but without real venue citations attached. Check coverage with:

```sql
SELECT COUNT(*) FROM venue_embeddings;
```

Regenerate it with:
```bash
poetry run python scripts/backfill_venue_embeddings.py
```

---

## 4. Running the backend (required, the app does nothing useful without it)

The mobile app expects the backend running locally at `127.0.0.1:5000` (iOS Simulator) or `10.0.2.2:5000` (Android Emulator: this is Android's special alias for "the host machine," already handled automatically in `api.ts`). See `backend/README.md` for full backend setup. **Start the backend before launching the app.**

For Android Emulator or a real physical device, bind Flask to all interfaces, not just localhost:
```bash
poetry run python src/app.py --host=0.0.0.0
```

---

## 5. Running on iOS Simulator

```bash
cd frontend/mobile
npx expo run:ios
```

This builds a real native app and installs it on the Simulator. **You only need this full command once**, or again later if you add/change a native module, or change native config like `app.json`'s Maps key. This project can't use the generic **Expo Go** app from the App Store, because the SDK version bundled in the public App Store release of Expo Go is behind this project's own Expo SDK version, not because of any specific native module. Day-to-day, once the native build is installed, the normal Expo workflow applies:

```bash
npx expo start
```

Press `i` to reopen the already installed build, or just tap the app icon directly on the Simulator (either reconnects to Metro without rebuilding).

If you need to test on a specific simulator (e.g. a smaller screen):
```bash
xcrun simctl create "iPhone SE Test" "iPhone SE (3rd generation)"
xcrun simctl boot "iPhone SE Test"
npx expo run:ios --device "iPhone SE Test"
```

---

## 6. Running on Android Emulator

Boot an emulator first via Android Studio's Device Manager, then:

```bash
cd frontend/mobile
npx expo run:android
```

### Known Android emulator limitations (not app bugs)

- **Location services** don't work out of the box on emulators (no real GPS). Manually set a mock location via the emulator's Extended Controls → Location panel, and enable Location Services in the emulator's Settings app, before any location-dependent screen (onboarding, SOS, map) works correctly.
- **`getCurrentLocation()`** in `services/location.ts` deliberately uses `Location.Accuracy.Balanced` rather than `High`/`Highest`, requesting high accuracy on an emulator can fail entirely with `ERR_CURRENT_LOCATION_IS_UNAVAILABLE`, since emulators don't simulate a real satellite fix. This is a permanent fix, not a workaround to remove later.
- Emulators are noticeably slower than real devices or the iOS Simulator, especially on first cold start expect map load times to be several times slower than iOS. This is a documented environment limitation, not a performance regression in the app itself (see `Mobile Accessibility & Performance Review.pdf` in this folder).

---

## 7. Running on a real physical device (iPhone)

Genuinely achievable with just a free Apple ID, no paid Developer Program needed.

1. **Enable Developer Mode** on the iPhone: Settings → Privacy & Security → Developer Mode → on (requires a restart + confirmation).
2. Connect the iPhone via USB, tap **Trust** when prompted.
3. Open the Xcode workspace: `open ios/*.xcworkspace`
4. In Xcode: **Settings → Accounts** → sign in with your Apple ID if not already.
5. Select the project in the sidebar → your app's **target** (under TARGETS, not PROJECT) → **Signing & Capabilities** → set **Team** to your Apple ID → ensure **Bundle Identifier** is unique to you (free accounts can't share a bundle ID across different people's teams, append your name if you hit a "not available" registration error, e.g. `com.yourname.clearpath.mobile`).
6. Build and install:
   ```bash
   npx expo run:ios --device
   ```

**Known limitation:** with a free (non-paid) Apple ID, the app's signing certificate expires after **7 days**, after which it stops launching until reinstalled via the same `npx expo run:ios --device` command. This is a genuine Apple platform constraint, not something fixable in this project's scope.

**If the app crashes on launch with "No script URL provided":** the installed build has lost track of where Metro is, relaunch via `npx expo run:ios --device` again (not by tapping the home screen icon) to hand it the current bundler address.

### Running the Simulator and a real device at the same time

Both can share one Metro instance and one backend, no need to run anything twice. Once one is running via the CLI, press `i` in the same Metro terminal to also launch the Simulator alongside it.

---

## 8. Networking: real devices need your Mac's real IP address

A real physical device can't use `127.0.0.1` (that means "the device itself" to it, not your Mac) or Android's `10.0.2.2` alias (it needs your Mac's actual local network IP).

### Checklist: every time you switch WiFi networks (including switching to/from a phone hotspot)

1. **Get your Mac's current IP:**
   ```bash
   ipconfig getifaddr en0
   ```
2. **Update `frontend/mobile/.env`:**
   ```
   EXPO_PUBLIC_API_HOST=<the IP from step 1>
   ```
3. **Restart the backend** (`Ctrl+C`, then re-run with `--host=0.0.0.0`), confirm the IP it prints matches step 1.
4. **Restart Metro with cache clear:**
   ```bash
   npx expo start -c
   ```
5. **Relaunch on the device via CLI**, not by tapping the icon:
   ```bash
   npx expo run:ios --device
   ```

If anything seems broken on a real device (login failing, requests timing out, chatbot not responding) and you've switched networks recently, **check this mismatch first**, it's the most common root cause by far.

This override doesn't affect the iOS Simulator or Android Emulator, which continue to work normally without it, `EXPO_PUBLIC_API_HOST` only needs to be set/updated when testing on a real device.

---

## 9. Local test data

**`Data+ML/test/7.13-7.18/run_v2_forecast.sh`** publishes real busyness forecast predictions. This data goes stale roughly every 11–12 hours so re-run this script if venue busyness charts stop appearing (`data_mode: "unavailable"` in the API response is the tell). See its own header comment for scheduling options (cron).

---

## 10. Running tests

Jest and Maestro test different things. Jest runs entirely in code with no real app/simulator/backend involved, calling functions and components directly with mocked data; fast, and isolates one specific piece of logic. Maestro drives a real, running app on a real simulator/device, tapping and typing exactly like a person would, against a real backend; slower, and closer to "does the whole flow actually work," but a failure doesn't point at one specific function the way a Jest failure does.

### Unit tests (Jest)

```bash
cd frontend/mobile
npm test
```

### End-to-end tests (Maestro)

Requires a running simulator with the app already installed (see Section 5).

```bash
maestro test maestro/login.yaml
```

Or run the whole suite:
```bash
./maestro/run-all.sh <simulator-udid>
```
Get the UDID via `xcrun simctl list devices | grep Booted`.

### Linting

```bash
npm run lint
```
