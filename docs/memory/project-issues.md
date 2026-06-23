# ClearPath 问题追踪

> 最后更新: 2026-06-23
> 整理原则: 按 Sprint + 时间顺序，已解决项归档到底部

---

## Sprint 1 (Week 1-3) — 基础架构

> 无遗留问题，全部完成。

---

## Sprint 2 (Week 4-5) — 核心环境 + Auth + Zoning

### ✅ 已解决

| # | 问题 | 解决日期 | 说明 |
|---|------|:--------:|------|
| 1 | users 表缺失 | 2026-06-09 | Phase 2 创建，D1 邮箱+密码 |
| 2 | user_reports 缺 user_id | 2026-06-09 | Phase 3 ALTER TABLE + UNIQUE 约束 |
| 3 | busyness_forecasts 表缺失 | 2026-06-09 | Phase 4 创建 |
| 4 | venues 缺 district 列 | 2026-06-11 | Docker schema 已包含 + 手动 CREATE INDEX |
| 5 | MEDICAL_ID 幻影导入 | 2026-06-10 | mock_data.py 补充数据 |
| 6 | emergencyasset 命名漂移 | 2026-06-10 | 全链路统一为 `emergencyasset` |
| 7 | mock_data.py 两处缺口 | 2026-06-09 | Phase 6 修复 |
| 8 | 拥挤度命名 (D4) | 2026-06-09 | ALTER TABLE 执行 |
| 9 | 报告 issue_type (D5+D8) | 2026-06-09 | 建表 + ALTER |
| 10 | Docker/test schema 不同步 | 2026-06-09 | 已同步 |
| 11 | DQR O(N²) 效率问题 | 2026-06-11 | 网格预过滤 + 向量化 haversine |
| 12 | dqr_utils.py 代码重复 | 2026-06-11 | 移至 shared/ + 删除副本 |
| 13 | D2.7 单元测试缺失 | 2026-06-11 | 12 pytest cases |
| 14 | ERD 图表未导出 | 2026-06-11 | Mermaid → PNG/SVG |
| 15 | GPS 网格漏检高纬度 | 2026-06-11 | GRID_LNG 按 cos(40.88°) 缩放 |
| 16 | export 空结果不覆盖旧 CSV | 2026-06-11 | unlink() 删除过期文件 |
| 17 | Park toilet 零坐标 | 2026-06-11 | NYC Open Data 匹配 93 + 删 3 Bronx |

### ❌ 未解决

| # | 问题 | 严重度 | 说明 |
|---|------|:------:|------|
| 18 | D2.4 Mock 数据不完整 | 🟡 | 仅 3 个 venues，无 district 分组，需 20+ 覆盖 4 区域 |
| 19 | D2.5 ML 模型未实现 | 🔴 | ARIMA/LSTM 缺失，阻塞 Sprint 3 预测任务 |

### Sprint 2 数据任务审计

| 任务 | 状态 | 说明 |
|------|:----:|------|
| D2.1 ERD + Schema | ✅ | 19 tables, ERD 导出 |
| D2.2 MySQL 表实现 | ✅ | 20 FK, composite indexes |
| D2.3 数据摄取 | ✅ | 7 sources, ~30K rows |
| D2.4 Mock 数据 | ⚠️ | 仅 3 venues，缺区域分组 |
| D2.5 ML 模型 | ❌ | traffic_hourly.csv 已获取，模型未实现 |
| D2.6 数据去重 | ✅ | GPS grid+haversine |
| D2.7 单元测试 | ✅ | 12 pytest cases |

---

## Sprint 3 (Week 6-7) — Spatial Query + Reports + ML Production

### Phase 7: 用户医疗信息加密存储 (2026-06-23)

| # | 任务 | 状态 | 说明 |
|---|------|:----:|------|
| 7.1 | 共享 DB helper | ✅ | src/db.py |
| 7.2 | MySQL Auth 改造 | ✅ | bcrypt + MySQL users 表 |
| 7.3 | Bearer JWT | ✅ | require_auth 装饰器 |
| 7.4 | Docker keyring | ✅ | keyring_file 插件 |
| 7.5 | user_medical_profiles 表 | ✅ | ENCRYPTION='Y' + CASCADE |
| 7.6 | Medical API | ✅ | GET/PUT/DELETE |
| 7.7 | OpenAPI 更新 | ✅ | v1.6.0 + 6 项缺口修复 |
| 7.8 | 后端测试 | ✅ | tests/test_medical.py |

### OpenAPI 缺口修复 (2026-06-23)

| # | 问题 | 修复 |
|---|------|------|
| 1 | MedicalProfile JSON 字段用 string[] | 改为 object[] (name+detail/name+dosage+frequency) |
| 2 | emergency_contacts 缺 primary | 添加 boolean 字段 |
| 3 | AuthLoginResponse 含 refresh_token | 移除 (D10: 只做 access token) |
| 4 | 5 个重复 schema | 删除冗余定义 |
| 5 | /medical-passport YAML 重复 key | 移除旧版块 |
| 6 | v1.4.1 changelog 矛盾 | 添加 "superseded" 注释 |

### Sprint 3 数据任务 (fangxun.wu)

| # | 任务 | 状态 | 说明 |
|---|------|:----:|------|
| S3.1 | MySQL Keyring + Encryption | ✅ | docker-compose + DDL |
| S3.2 | Encrypted Medical Profile DDL | ✅ | 002_medical_profile.sql |
| S3.3 | Seed Venues Ingestion | ✅ | busyness_ingestion.py + venue_coverage.py |
| S3.4 | Real-Time Telemetry Pipeline | ⚠️ | 历史数据管线存在，实时 telemetry 未实现 |
| S3.5 | 12-Hour Forecast Engine | ⚠️ | 统计聚合存在，ARIMA/LSTM 未实现 |
| S3.6 | Reports TTL Pipeline | ❌ | mock 数据，无 Redis/Celery |

### D10 医疗数据边界修订 (2026-06-15 → 2026-06-23)

| 版本 | 方案 | 日期 |
|------|------|:----:|
| v1 | 云端加密存储 (AES-256-GCM) | 2026-06-09 |
| v2 | 严格数据分层: Tier 1 云端 + Tier 2 本地 | 2026-06-15 |
| v3 | 服务器端加密存储 (InnoDB tablespace) | 2026-06-23 |

---

## Sprint 4 (Week 8-9) — 待开始

> 前置依赖: Sprint 3 完成

---

## 已解决问题归档 (按时间)

| 日期 | 问题 | 解决方式 |
|------|------|---------|
| 2026-06-06 | phone_number vs phone | mock_data.py 改为 phone |
| 2026-06-06 | forecast_4h/8h 残留 | DB 删除 + schema 同步 |
| 2026-06-06 | weather_risk 列 | DB 已存在 |
| 2026-06-06 | emergency_assets 重复写入 | 唯一约束 |
| 2026-06-09 | D1-D10 产品决策 | grill-with-docs 冻结 |
| 2026-06-09 | 19 tables schema | 6 phases 全部创建 |
| 2026-06-09 | Chatbot RAG 端点 | POST /chatbot |
| 2026-06-09 | Medical Passport | GET /medical-passport |
| 2026-06-09 | RouteOption per-mode | summary_by_mode |
| 2026-06-10 | forecast_1h INT→JSON | 计划内设计变更 |
| 2026-06-10 | emergencyasset 命名 | 全链路统一 |
| 2026-06-11 | DQR 拆分 | 6 modules + 218 行 notebook |
| 2026-06-11 | GPS 高纬度漏检 | cos(40.88°) 缩放 |
| 2026-06-11 | Park toilet 零坐标 | NYC Open Data 匹配 |
| 2026-06-23 | Phase 7 医疗加密存储 | 8 任务全部完成 |
| 2026-06-23 | OpenAPI 6 项缺口 | schema 对齐实现 |
