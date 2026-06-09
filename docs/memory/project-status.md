# ClearPath 当前项目状态

> 更新日期：2026-06-09 | openapi.yaml v1.4.0

---

## 项目概览

- **项目名称**: ClearPath — 曼哈顿无障碍设施导航
- **技术栈**: Flask + MySQL + React Native
- **分支**: `main` (主分支), `alex` (开发分支)
- **DB**: MySQL `clearpath` schema, 13 张表

## 数据库连接

| 参数 | 值 |
|------|-----|
| Host | 127.0.0.1:3306 |
| User | clearpath_app |
| Password | clearpath_app |
| Database | clearpath |

---

## 数据库 Schema 状态 (13 张表)

### 已完成的表

| 表名 | 行数 | 用途 |
|------|------|------|
| `venues` | ~3,479 | 统一 POI 表 (含 district、语言、无障碍、警告、weather_risk) |
| `venue_source_links` | ~3,479 | 数据源追踪 (1:1 with venues) |
| `restroom_profiles` | 476 | 卫生间详情 |
| `healthcare_profiles` | 1,228 | 医疗机构详情 |
| `emergency_assets` | ~3,279 | AED 设备 (含唯一约束) |
| `pedestrian_ramps` | 23,625 | 无障碍坡道 (含 district) |
| `venue_accessibility` | 0 | 场馆无障碍详情 (待填充) |
| `venue_language` | 63 | 场馆多语言支持 |
| `venue_warnings` | 0 | 场馆警告 (待填充) |
| `external_context_cache` | 1 | 天气 API 缓存 |

### 需改造的表

| 表名 | 行数 | 问题 |
|------|------|------|
| `user_reports` | 0 | 缺 `user_id` FK, 需移除 `anonymous`/`reported_by` |
| `report_confirmations` | 0 | 缺 `user_id` + 唯一约束 `(report_id, user_id)` |
| `busyness_scores` | 0 | 仅有 `forecast_1h`; 缺 `busyness_forecasts` 时序表 |

### 缺失的关键表

| 表名 | 用途 | 优先级 |
|------|------|--------|
| `users` | 账户系统基础 | P0 |
| `user_favorite_venues` | 跨设备收藏同步 | P1 |
| `notification_preferences` | 安静时段 + Push 订阅 | P1 |
| `busyness_forecasts` | 12 小时时序预测 | P1 |
| `report_categories` | 报告类别字典 | P2 |

---

## venues 表列数：24

```
venue_id, venue_type, name, latitude, longitude, borough, district,
language_tags, primary_language, secondary_language, accessible_status,
accessibility_features, active_warning, open_now, address, phone, website,
opening_hours, photos, rating, weather_risk, source_confidence,
created_at, updated_at
```

---

## ETL Pipeline 状态

- **Notebook**: `Data+ML/test/6.2-6.5_DB/database_build.ipynb` (49 cells, 24 code cells)
- **Schema**: `Data+ML/test/6.2-6.5_DB/001_clearpath_schema.sql`
- **数据源**: `data_source/` (仓库外部), 由 `clearpath_sources.json` 管理
- **MySQL Docker**: `docker-compose.yml` at repo root, init: `docker/mysql/init/001_clearpath_schema.sql`
- **District Zoning**: ✅ 已实现 (venues + pedestrian_ramps)
- **Weather API**: ✅ NWS 集成, 1 条缓存
- **Venue Language**: ✅ LASS 数据, 63 条匹配

### ETL 后行数 (2026-06-05)

| 数据源 | Manhattan | ETL 后 |
|--------|-----------|--------|
| NYC Public Restrooms | 358 | 349 导入 |
| Parks Toilets | 129 | 127 导入 |
| OSM Healthcare | 900 | 900 导入 |
| NYS Health | 454 | 431 导入 |
| AED Inventory | 3,393 | 3,279 导入 (dedup) |
| Pedestrian Ramps | 23,625 | 23,625 导入 |
| Weather (NWS API) | — | 1 cached |
| Venue Language (LASS) | 442 | 63 matched |

---

## OpenAPI 状态 (v1.4.0)

- **端点数**: 20+
- **新标签**: Busyness, Insights, Chatbot
- **覆盖率**: ~90%
- **组内审核**: `docs/memory/openapi_gap_finalacceptcriteria.md`

### 已实现的端点

| 模块 | 端点 | 状态 |
|------|------|------|
| Venues | `GET /venues`, `GET /venues/{id}` | ✅ |
| Busyness | `GET /venues/{id}/busyness`, `GET /venues/{id}/busyness/forecast` | ✅ |
| Reports | `GET/POST /reports`, `POST /reports/{id}/confirmations` | ✅ |
| Insights | `GET /insights` | ✅ |
| Chatbot | `POST /chatbot` | ✅ |
| User | profile, settings, languages, favourites (CRUD), SOS, notification-prefs, account delete, medical-passport | ✅ |
| Routes | options, detail | ✅ |
| Realtime | SSE map-updates | ✅ |

---

## Sprint Pipeline 状态

| 已完成 | 待实现 |
|--------|--------|
| ✅ 13 张表 Schema | ❌ JWT 认证 |
| ✅ ETL 数据导入 | ❌ Profile CRUD |
| ✅ Mock 数据 (v1.4.0) | ❌ 实时遥测管道 |
| ✅ Weather API 集成 | ❌ 12 小时 ML 预测 |
| ✅ Venue Language ETL | ❌ 报告 TTL (2h) |
| ✅ Schema 同步机制 | ❌ 级联删除 API |
| ✅ District Zoning (venues + ramps) | ❌ Gemini RAG |
| ✅ emergency_assets 唯一约束 | ❌ 用户认证系统 |
| ✅ OpenAPI v1.4.0 (20+ 端点) | |

---

## 文件结构

```
docs/memory/
├── project-status.md          ← 本文件
├── project-issues.md          ← 现有问题
├── execution-plan.md          ← 执行计划 (DB schema 重点)
├── openapi_gap_finalacceptcriteria.md  ← 组内审核用
└── MEMORY.md                  ← 索引

src/
├── app.py              # Flask 应用入口
├── mock_data.py        # 模拟数据 (v1.4.0)
└── api/                # API 路由

Data+ML/test/6.2-6.5_DB/
├── database_build.ipynb      # ETL 流程
├── 001_clearpath_schema.sql  # 数据库 Schema
├── README.md                 # 操作文档
└── clearpath_sources.json    # 数据源清单
```
