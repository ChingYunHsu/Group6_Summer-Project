# ClearPath — Environment Requirements

## 1. Infrastructure (Docker)

All core services are defined in `docker-compose.yml` and run inside Docker.

| Service | Image | Host Port |
|---|---|---|
| MySQL | `mysql:8.4` | `3306` |
| Redis | `redis:7-alpine` | `6379` |
| phpMyAdmin | `phpmyadmin:latest` | `8080` |
| Telemetry (opt-in) | custom build | — |

```bash
# Start core services
docker compose up -d

# Start with telemetry ingestion
docker compose --profile telemetry up -d
```

---

## 2. Backend (Flask / Poetry)

**Runtime:** Python `^3.11`

**Install:**
```bash
cd backend
cp .env.example .env   # fill in real keys
poetry install
poetry run flask run
```

### Python Dependencies

| Package | Version |
|---|---|
| flask | `^3.0.3` |
| pymysql | `^1.1.0` |
| pandas | `^2.2.0` |
| numpy | `^1.26.0` |
| requests | `^2.31.0` |
| pyproj | `^3.6.0` |
| redis | `^5.0.0` |
| celery | `^5.4.0` |
| pyjwt | `^2.9.0` |
| cryptography | `^43.0.0` |
| scikit-learn | `^1.4.0` |
| matplotlib | `^3.8.0` |
| python-dotenv | `^1.0.1` |
| dbutils | `^3.1.0` |

### Dev Dependencies

| Package | Version |
|---|---|
| pytest-timeout | `^2.2.0` |
| pytest-cov | `^5.0.0` |
| flake8 | `^7.1.0` |

### Required Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Description |
|---|---|
| `API_KEY` | General API key |
| `BESTTIME_API_KEY` | BestTime venue busyness API |
| `GOOGLE_MAPS_API_KEY` | Google Maps |
| `GEMINI_API_KEY` | Gemini AI |
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | `3306` |
| `DB_USER` | `clearpath_app` |
| `DB_PASSWORD` | `clearpath_app` |
| `DB_NAME` | `clearpath` |
| `JWT_SECRET` | 32-byte secret for JWT signing |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` |
| `MEDICAL_PROFILE_ENCRYPTION_KEY` | Fernet key for encrypted medical profiles |

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 3. Frontend Web (React)

**Install & run:**
```bash
cd frontend/web
npm install
npm run dev
```

### Key Dependencies

| Package | Purpose |
|---|---|
| react | UI framework |
| react-router-dom | Client-side routing |
| maplibre-gl | Map rendering |
| recharts | Charts / data visualization |

---

## 4. Frontend Mobile (React Native / Expo)

**Install & run:**
```bash
cd frontend/mobile
npm install
npx expo start
```

| Package | Version |
|---|---|
| react-native | `0.85.3` |
| expo | `~56.0.14` |

---

## 5. Data / ML Layer (Python + Jupyter)

**Telemetry service dependency** (`Data+ML/test/6.15-6.20/requirements-telemetry.txt`):

| Package | Version |
|---|---|
| PyMySQL | `1.1.1` |

**ETL notebook:** `Data+ML/test/6.2_DB/database_build.ipynb`

Execute cells in order: 12 → 14 → 16 → 22 → 19 → 24 → 27

---

## 6. Database Credentials (Local Dev)

| Key | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `3306` |
| Database | `clearpath` |
| User | `clearpath_app` |
| Password | `clearpath_app` |
| Root Password | `clearpath_root` |

Connect:
```bash
mysql -h 127.0.0.1 -P 3306 -u clearpath_app -pclearpath_app clearpath
# or via Docker
docker exec -it clearpath-mysql mysql -u clearpath_app -pclearpath_app clearpath
```
