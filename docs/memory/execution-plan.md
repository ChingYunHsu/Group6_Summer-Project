# ClearPath 执行计划 (DB Schema 重点)

> 更新日期：2026-06-23 | 审计: 与 openapi_gap_finalacceptcriteria.md 对齐 + Sprint 3 数据任务归属整理
> 决策冻结: 2026-06-09 grill-with-docs 会话 (10 项)

---

## 已冻结决策 (D1-D10)

详见 `context-terms.md` — 以下为摘要：

| # | 决策项 | 结论 |
|---|-------|------|
| D1 | 认证方式 | 邮箱+密码（bcrypt），No OAuth |
| D2 | Guest 模式 | 无 token = Guest，被动访问 |
| D3 | 匿名报告 | 提交后匿名化，保留 `anonymous` 字段 |
| D4 | 拥挤度等级 | 三级 `quiet/moderate/busy`，NULL = 无数据 |
| D5 | 报告类别 | OpenAPI 8 个 issue_type 值 |
| D6 | 确认操作 | 覆盖旧 action，`UNIQUE (report_id, user_id)` |
| D7 | `auth_subject` | 不需要，邮箱即认证标识 |
| D8 | 报告类别存储 | 字典表 `report_categories`（按场馆类型过滤） |
| D9 | RAG embedding | MySQL JSON/BLOB（~3500 条数据量足够） |
| D10 | 医疗数据边界 | **严格数据分层**: Tier 1 Profile Group 云端同步(Read-Only/Editable); Tier 2 Medical ID 100%本地 Mobile Only; F-14 QR-P2P打印 (2026-06-15 修订) |

---

## 已完成项

- [x] emergency_assets 唯一约束 `(venue_id, floor, location_type)` — session 2026-06-06
- [x] District Zoning: venues.district + pedestrian_ramps.district — session 2026-06-09
- [x] forecast_4h/8h 从 busyness_scores 删除 — session 2026-06-06
- [x] forecast_1h 改为 JSON 类型 — session 2026-06-06
- [x] Schema 文件同步 (test → 001_clearpath_schema.sql) — session 2026-06-06
- [x] D1-D10 产品决策冻结 — session 2026-06-09 (grill-with-docs)
- [x] busyness_scores ENUM 改为 `quiet/moderate/busy` + 删除 forecast_4h/8h — session 2026-06-09

---

## Phase 1: 基础同步与决策冻结

**目标**: 统一 Schema 文件, 冻结产品决策

- [x] 同步两份 `001_clearpath_schema.sql` (docker/mysql/init/ ↔ Data+ML/test/6.2-6.5_DB/)
- [x] 冻结 10 项产品决策 — 已完成，见 `context-terms.md`

---

## Phase 2: 用户与账户表

**目标**: 建立认证基础 (D1 邮箱+密码, D2 Guest 无 token)

- [x] 新建 `users` 表 — 2026-06-09
- [x] 新建 `user_favorite_venues` 表 — 2026-06-09
- [x] 新建 `notification_preferences` 表 — 2026-06-09

---

## Phase 3: 报告系统改造

**目标**: 绑定认证用户, 防重复投票, 按场馆类型过滤类别

- [x] 改造 `user_reports` — 2026-06-09
- [x] 改造 `report_confirmations` — 2026-06-09
- [x] 新建 `report_categories` 字典表 (D8: 按场馆类型过滤) — 2026-06-09

---

## Phase 4: 拥挤度预测

**目标**: 支持 12 小时预测图表

- [x] 新建 `busyness_forecasts` 表 (D4 + D9) — 2026-06-09

---

## Phase 5: RAG 数据层

**目标**: 支持 Gemini RAG 查询

- [x] 为 `venues(latitude, longitude)`、`venue_type`、`district` 建立索引 — 2026-06-09
- [ ] 生成可检索的场馆文档投影 (含语言、无障碍、营业、警告、实时拥挤度) — 待后端实现
- [x] embedding 存储方案确定: MySQL JSON/BLOB (D9) — ~3500 条数据量足够
- [x] 创建 `venue_embeddings` 表 — 2026-06-09
- [x] 确认不创建服务端 `chat_history` 表 (Final 要求聊天历史仅客户端)

---

## Phase 6: OpenAPI 与验证

**目标**: 确保 API 与 DB 一致

- [x] 更新 mock_data.py: `REPORT_CONFIRMATION_TEMPLATE` 加 `user_id` (openapi_gap #9)
- [x] 更新 mock_data.py: `INSIGHTS_DASHBOARD.district` 改为 lowercase `midtown_east`
- [x] 更新 ETL notebook 验证新表结构
- [x] 级联删除测试 (删除用户 → 收藏、通知、报告一并清除)
- [x] 第二次 ETL 幂等性验证 (不产生重复行)
- [x] 同步 Docker schema (test → docker/mysql/init/)
- [x] MySQL 5.7 COMMENT 语法兼容性检查 — 无 COMMENT 语法问题

---

## Sprint 3 数据任务（fangxun.wu）

> **说明**: 下列任务全部归属 Sprint 3 的 `fangxun.wu` 工作流，并按现有 DB 设计约束执行：基础 `venues` / `reports` 结构保持稳定，实时与预测结果写入动态层，医疗资料单独进入加密表。

| # | Task | Priority | 说明 |
|---|------|----------|------|
| S3.1 | MySQL Keyring Configuration & Tablespace Encryption Integration | P0 | 只作为加密医疗表的前置能力；失败时仅阻断需要 `ENCRYPTION='Y'` 的迁移，不阻断无关基础表 |
| S3.2 | Encrypted User Medical Profile Schema Migration Setup | P0 | `user_medical_profiles` DDL + `ENCRYPTION='Y'` + `ON DELETE CASCADE`，仅存 Tier 2 医疗字段 |
| S3.3 | Real-Time MySQL Seed Venues Ingestion & Verification | P0 | 作为幂等初始化 seed，补足静态 `venues` 基础数据，不替代 ETL 权威源 |
| S3.4 | Real-Time Zoned Telemetry Pipeline | P0 | 实时载入 live capacity / wait-time，写入动态 telemetry 层，不回写静态 `venues` |
| S3.5 | 12-Hour Capacity Forecasting Production Engine | P0 | 产出 12h 预测结果到预测层/预测表，保持与前端消费的 forecast 结构一致 |
| S3.6 | Polymorphic Crowdsourced Ingestion Engine & 2-Hour TTL Pipeline | P0 | `user_reports` / `report_confirmations` 路由 + Redis/Celery 过期状态化，TTL 仅更新 `expired` / `status`，不做硬删除 |

---

### Sprint 3 扩展：用户医疗信息加密存储

**目标**: 在服务器端加密存储用户 Tier 2 医疗数据，并通过同一账号支持 iOS / Android / Web 自动同步。

**前置条件**: Phase 2 (users 表必须存在)

**范围决策 (2026-06-17)**:

- Medical ID 不再坚持 “100% 本地”；本阶段修订为服务器端存储加密医疗资料。
- 加密边界为 MySQL InnoDB 表空间加密，应用层和 API 层按明文业务对象处理。
- 不做字段级 AES 加密、端到端加密、KMS、离线缓存、审计日志或历史版本。
- 登录注册同步切到 MySQL `users` 表；JWT 必须从真实用户记录签发。
- JWT 只做 access token，不做 refresh token、rotation 或 revoke list。
- 三端都可读写，但 Phase 7 只交付后端 + OpenAPI + 测试；iOS / Android / Web UI 接入另行排期。

| # | Task | Description | Status |
|---|------|-------------|:------:|
| 7.1 | 共享 DB helper | 抽出 `pymysql` 连接/事务 helper，供 auth 和 medical API 复用 | ⏳ 待实施 |
| 7.2 | MySQL Auth 改造 | `register/login` 读写 `users` 表，密码使用 hash，不再使用 `AUTH_USERS` mock | ⏳ 待实施 |
| 7.3 | Bearer JWT | 登录/注册返回 access token；protected API 从 `Authorization: Bearer <token>` 解析 `sub=user_id` | ⏳ 待实施 |
| 7.4 | Docker keyring 配置 | `docker-compose.yml` 启用 MySQL keyring，表空间加密不可用时硬失败 | ⏳ 待实施 |
| 7.5 | 新建 `user_medical_profiles` 表 | `user_id` FK + 结构化医疗字段 + `ENCRYPTION='Y'` | ⏳ 待实施 |
| 7.6 | 后端 Medical API | `GET` / `PUT` / `DELETE /api/v1/user/medical-profile`，用户身份只来自 JWT | ⏳ 待实施 |
| 7.7 | OpenAPI 更新 | 修订 D10 隐私边界、Auth token schema、MedicalProfile schema 和三端同步 API | ⏳ 待实施 |
| 7.8 | 后端测试 | PyTest: password hash、JWT 鉴权、用户隔离、GET/PUT/DELETE、级联删除、表加密验证 | ⏳ 待实施 |

**加密方案选择**:

| 方案 | 粒度 | 是否本阶段 | 说明 |
|------|------|:---:|------|
| InnoDB 表空间加密 | 整张表 | ✅ | 当前最小实现；医疗表必须 `ENCRYPTION='Y'` |
| 列级 AES_ENCRYPT | 单个字段 | ❌ | 不做字段级加解密，避免引入密钥管理复杂度 |
| 端到端加密 | 客户端密文 | ❌ | 不做跨 iOS / Android / Web 的客户端密钥同步 |
| 应用层加密 + KMS | 代码控制 | ❌ | 生产增强项，本阶段不引入 KMS |

> **硬约束**: 如果 MySQL keyring 或表空间加密不可用，迁移必须失败；不得降级创建未加密 `user_medical_profiles` 表。

**认证与同步方案**:

- `POST /api/v1/auth/register`: 写入 MySQL `users` 表，`password_hash = generate_password_hash(password)`。
- `POST /api/v1/auth/login`: 从 MySQL `users` 表查用户，使用 `check_password_hash()` 校验密码。
- 登录/注册返回 `access_token`，JWT payload 至少包含 `sub=user_id`。
- `GET` / `PUT` / `DELETE /api/v1/user/medical-profile` 必须使用 Bearer JWT。
- Medical API 不接受 `user_id` 参数，所有读写都绑定 JWT 当前用户。
- 三端自动同步语义: 任一端保存后，其他端下次 `GET` 获取最新资料。
- 冲突策略: 最后写入覆盖；本阶段不做 `version`、`If-Match` 或 `409 Conflict`。
- 数据保留: 每个用户最多一行医疗资料；不保留历史版本或审计日志。

**字段来源对照**:

| 字段 | Mobile MedicalId | Web userProfile | F-12 需求 | F-11/F-14 | 存储层级 |
|------|:---:|:---:|:---:|:---:|------|
| blood_type | ✅ string | ✅ string | ✅ | ✅ | Tier 2 (加密) |
| severe_allergies | ✅ {name,detail}[] | ✅ {name,detail}[] | ✅ | ✅ | Tier 2 (加密) |
| conditions | ✅ {name,detail}[] | ✅ {name,detail}[] | ✅ | ✅ | Tier 2 (加密) |
| medications | ✅ {name,dosage,frequency}[] | — | — | ✅ F-11 | Tier 2 (加密) |
| emergency_contacts | — | ✅ {name,relationship,phone,primary}[] | ✅ | ✅ F-14 | Tier 2 (加密) |
| emergency_notes | ✅ string | — | — | — | Tier 2 (加密) |
| medical_pass_title | ✅ string | — | — | — | Tier 2 (加密) |
| donor_status | — | ✅ string | — | — | Tier 2 (加密) |
| date_of_birth | — | ✅ | ✅ | ✅ F-14 | Tier 1 (已在 UserProfile) |
| gender | — | ✅ | ✅ | — | Tier 1 (已在 UserProfile) |
| address | — | ✅ | ✅ | — | Tier 1 (已在 UserProfile) |

> **注意**: date_of_birth, gender, address 已在 `users` 表 (Tier 1)，不重复存储。
> Mobile / Web / iOS / Android 统一对象数组格式，不再兼容 `string[]` 原样存储。

**Schema 草案**:

```sql
CREATE TABLE user_medical_profiles (
    -- 主键
    user_id             VARCHAR(36) PRIMARY KEY,

    -- 基础信息
    blood_type          VARCHAR(5),             -- O+, O-, A+, A-, B+, AB+
    donor_status        VARCHAR(50),            -- organ_donor 等

    -- 医疗信息 (统一对象数组)
    severe_allergies    JSON,                   -- [{"name":"Penicillin","detail":"Anaphylaxis"}]
    conditions          JSON,                   -- [{"name":"Asthma","detail":"Diagnosed 2005"}]
    medications         JSON,                   -- [{"name":"Salbutamol","dosage":"2 puffs","frequency":"As needed"}]

    -- 紧急联系人
    emergency_contacts  JSON,                   -- [{"name":"Jane Doe","relationship":"Spouse","phone":"212-555-0101","primary":true}]
    emergency_notes     TEXT,                   -- 自由文本备注

    -- Medical Passport
    medical_pass_title  VARCHAR(100),           -- 自定义标题 (如 "Medical Information")

    -- 时间戳
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_medical_profile_user
      FOREIGN KEY (user_id) REFERENCES users(user_id)
      ON DELETE CASCADE
) ENCRYPTION='Y';
```

**JSON 字段格式规范**:

```json
{
  "blood_type": "O+",
  "donor_status": "organ_donor",
  "severe_allergies": [
    {"name": "Penicillin", "detail": "Anaphylaxis"}
  ],
  "conditions": [
    {"name": "Asthma", "detail": "Diagnosed 2005"}
  ],
  "medications": [
    {"name": "Salbutamol Inhaler", "dosage": "2 puffs", "frequency": "As needed"}
  ],
  "emergency_contacts": [
    {"name": "Jane Doe", "relationship": "Spouse", "phone": "212-555-0101", "primary": true}
  ],
  "emergency_notes": "Use inhaler before calling ambulance.",
  "medical_pass_title": "Medical Information"
}
```

**默认空 Profile**:

```json
{
  "blood_type": null,
  "donor_status": null,
  "severe_allergies": [],
  "conditions": [],
  "medications": [],
  "emergency_contacts": [],
  "emergency_notes": null,
  "medical_pass_title": "Medical Information"
}
```

**API 语义**:

| Method | Path | 语义 |
|--------|------|------|
| GET | `/api/v1/user/medical-profile` | 返回当前 JWT 用户医疗资料；不存在时返回默认空 Profile |
| PUT | `/api/v1/user/medical-profile` | 全量替换/upsert 当前 JWT 用户医疗资料；最后写入覆盖 |
| DELETE | `/api/v1/user/medical-profile` | 删除当前 JWT 用户医疗资料；幂等；再次 GET 返回默认空 Profile |

**非范围**:

- 不包含 iOS / Android / Web UI 接入或 mock 替换。
- 不包含离线缓存、本地 SecureStore/Keychain/IndexedDB 存储。
- 不包含 refresh token、token rotation、token revoke list。
- 不包含医疗资料历史版本、审计日志或恢复功能。
- 不包含字段级加密、端到端加密或 KMS。

**更新文件范围与代码量预估**:

| 文件/目录 | 变更 | 预估代码量 |
|-----------|------|-----------:|
| `src/db.py` | 新增共享 MySQL 连接/事务 helper | 40-80 行 |
| `src/auth.py` | 新增 Bearer JWT 生成/解析、当前用户校验 helper | 80-150 行 |
| `src/api/auth.py` | 注册/登录从 mock 改为 MySQL users + password hash + access token | 120-220 行 |
| `src/api/user.py` | 新增 medical profile GET/PUT/DELETE | 120-220 行 |
| `docker-compose.yml` | MySQL keyring / 表空间加密配置 | 10-30 行 |
| `docker/mysql/init/001_clearpath_schema.sql` | 新增 `user_medical_profiles` 加密表；必要时调整 users 相关约束 | 50-100 行 |
| `.env.example` / `src/settings.py` | 新增 DB/JWT 配置项 | 20-60 行 |
| `openapi.yaml` | Auth token、MedicalProfile schema、medical-profile endpoints、D10 修订 | 150-260 行 |
| `backend/tests/` | JWT、password hash、medical profile、用户隔离、级联删除、表加密测试 | 180-350 行 |

**后端 + OpenAPI 总代码量**: 约 770-1,470 行。

**工作量预估**: 15-26 小时；如果 MySQL keyring / `ENCRYPTION='Y'` 在 Docker MySQL 8.4 上配置踩坑，额外 2-6 小时。

---

## 实施依赖关系

```
Phase 1 (同步+决策)
    ↓
Phase 2 (users + favorites + notifications)
    ↓
Phase 3 (reports user_id + confirmations user_id)    Phase 7 (医疗数据加密存储)
    ↓                                                  ↑ 依赖 Phase 2
Phase 4 (busyness_forecasts)
    ↓
Phase 5 (RAG 索引)
    ↓
Phase 6 (验证+清理)
```

**Phase 2 是所有后续阶段的前置条件** — 没有 users 表, Phase 3/5/7 都无法执行。

---

## 风险提示

1. **按旧 Pipeline 实现服务器医疗 Profile** — 违反 Final 隐私边界
2. **继续允许无法追踪用户身份的报告/确认** — 无法执行唯一用户确认
3. **12 小时预测数据失真** — 单值伪造数组无法支撑真实图表

---

## Sprint 2 数据任务 (fangxun.wu)

**目标**: 完成数据库 ERD 修订、数据摄取、模拟数据和 ML 模型初始化
**总工时**: Est. 46h

| # | Task | Week | Description | Status | Est. (h) |
|---|------|------|-------------|:------:|:--------:|
| D2.1 | ERD Revision, Schema Updates & District Zoning Setup | Week 4 | ERD update + 4 district nodes | ✅ 2026-06-09 | 5 |
| D2.2 | MySQL Table Implementation & Index Tuning | Week 4 | DDL scripts + FK constraints + composite indexes | ✅ 2026-06-09 | 5 |
| D2.3 | Data Parsing & Ingestion | Week 5 | ETL: 349 restrooms, 900 healthcare, 431 NYS, 3,279 AEDs, 63 LASS | ✅ 2026-06-05 | 10 |
| D2.5 | Zoned Historical Ingestion & ML Model Init (Advance Start) | Week 5 | [High Priority] traffic_hourly.csv fetched; ARIMA/LSTM pending | ⏳ 进行中 | 10 |
| D2.6 | Data Deduplication & Multi-Source Cleansing Preprocessing | Week 5 | GPS duplicate detection (grid+haversine, lat-scaled) | ✅ 2026-06-11 | 10 |
| D2.7 | Database Integrity, Privacy & Constraint Unit Testing | Week 5 | PyTest: 100% venues non-Null district; 12 test cases | ✅ 2026-06-11 | — |

### DQR Pipeline 重构 (2026-06-11)

- 6 个共享模块 in `Data+ML/test/shared/` (dqr_utils, dqr_io, dqr_checks, dqr_analysis, dqr_cleaning, external_ingestion)
- Notebook: 21 cells, 218 code lines (from 40 cells, 406 lines)
- Output moved to `output/` subdirectory
- All imports consolidated in Cell 2
- pytest: 12 tests pass (D2.7, GPS grid, export overwrite, import path, clean_venues immutability)

### Park Toilet GPS Fix (2026-06-11)

- 124 zero-coordinate restroom venues fixed using NYC Open Data (`i7jb-7jku`)
- 93 Manhattan-trusted matches written to DB
- 3 Bronx Jackie Robinson Park entries deleted (wrong Borough)
- CSV `Directory_Of_Toilets_In_Public_Parks_20260526.csv` updated: +Latitude/Longitude columns
- DB: 473 restrooms, 100% GPS, 0 null districts



Sprint2 重点任务 D2.5 进展说明：
### D2.5 ARIMA/LSTM 实施计划

#### 当前数据限制

- `traffic_hourly.csv` 是按道路方向和小时聚合的 24 小时年度平均轮廓，不是连续历史时间序列。
- 当前数据缺少日期、连续时间戳和 `venue_id`，不能直接作为可信的 ARIMA/LSTM 生产训练集。
- 该文件仅保留为小时轮廓分析和演示基线，不标记为生产训练数据。

#### 实施阶段

1. **历史序列重构**: 从 NYC SODA 保留 `yr`、`m`、`d`、`hh`，按道路方向生成 `traffic_timeseries.csv`。
2. **基线模型**: 实现 24 小时季节性朴素预测，作为 SARIMA/LSTM 的最低性能基准。
3. **SARIMA**: 使用 Statsmodels SARIMAX 为每条道路方向训练时序模型；数据不足时回退到季节性基线。
4. **LSTM**: 使用 PyTorch 训练共享模型，输入过去 24 或 48 小时，输出未来 12 小时。
5. **场馆映射**: 建立道路序列到场馆的空间映射，生成 `venue_traffic_mapping.csv`，字段为 `venue_id`、`series_id`、`distance_m`。
6. **预测发布**: 统一输出 `forecast_for`、`predicted_score`、`predicted_level`、`model_version`，最终写入 `busyness_forecasts`。

数据库写入默认关闭。只有模型通过验证且预测记录具有有效场馆映射后，才允许显式启用写入。

#### 产物与接口

- `traffic_timeseries.csv`
- `venue_traffic_mapping.csv`
- `busyness_forecasting.ipynb`
- SARIMA/PyTorch 模型文件和模型评估报告
- 连续 12 小时预测结果

`predicted_score` 必须限制在 `0-100`，等级规则如下：

- `< 30`: `quiet`
- `30-70`: `moderate`
- `> 70`: `busy`

#### Citi Bike 历史行程数据 (2026-06-17 确认)

**数据源**: Lyft Citi Bike System Data — S3 公开下载
**下载地址**: `https://s3.amazonaws.com/tripdata/{YYYYMM}-citibike-tripdata.csv.zip`

| 系统 | 文件命名 | 月度行数 | 压缩大小 |
|------|----------|---------|---------|
| **NYC 全量** | `202605-citibike-tripdata.csv.zip` | 300-500 万行 | 917 MB |
| Jersey City only | `JC-202605-citibike-tripdata.csv.zip` | ~9.5 万行 | 3.3 MB |

**CSV 字段 (13列)**: `ride_id`, `rideable_type`, `started_at`, `ended_at`, `start_station_name`, `start_station_id`, `end_station_name`, `end_station_id`, `start_lat`, `start_lng`, `end_lat`, `end_lng`, `member_casual`

**本地数据**: `JC-202605-citibike-tripdata.csv.zip` (95,350 行, 3.3 MB) — 仅 Jersey City 区域

**部署策略**: 本地用 JC 月度文件做 feature engineering 原型和模型选型；正式训练放服务器从 S3 按需拉取 NYC 全量数据。

**ML 训练需求**: Phase 3 多源活动指数 (Todolist.md) 需要 Citi Bike 历史行程作为时序特征输入，与 MTA subway ridership + NYC Traffic 构成多源特征集。

#### 验收标准

- 每条训练序列至少覆盖 7 天，推荐覆盖 28 天以上。
- 训练、验证和测试集必须按时间顺序切分，禁止随机切分。
- SARIMA 或 LSTM 至少一个模型必须优于 24 小时季节性朴素基线。
- 每次预测必须输出连续 12 个小时，且不得包含重复时间点。
- 所有预测分数必须位于 `0-100`，等级必须符合统一阈值。
- 没有有效 `venue_id` 映射的道路预测不得写入 `busyness_forecasts`。

---

## Venue ML Coverage SOP (2026-06-23)

**目标**: 将 4000+ 原始 venue catalogue 保留下来，同时明确哪些 venue 可以进入 supervised ML，哪些只能由规则 fallback 或 `no_data` 表示。

### 核心决策

- 原始 `venues` 不删除，不因为 SerpApi/Google Popular Times 缺失而 drop。
- Supervised ML 只训练有可靠 Google Popular Times / SerpApi busy label 的 venue。
- 无 label venue 不是应用范围外，而是 **out of scope for supervised ML**。
- 应用层可以继续展示无 label venue，但必须区分 `ml_model`、`rule_fallback`、`none/no_data` 来源。
- `no_data` 是数据可用性状态，不是 ML 要预测的忙碌等级。

### Label 与预测任务定义

预测任务为未来 12 小时连续 busy-level forecast，间隔 1 小时：

```text
target = quiet | moderate | busy
horizon = t+1h ... t+12h
```

Google Popular Times / SerpApi busy score 归一化规则：

```text
if peak_vol == 0 or popularity data missing:
    label_status = no_data
else:
    ratio = hourly_popularity / peak_vol

    if ratio < 0.3:
        label = quiet
    elif ratio < 0.7:
        label = moderate
    else:
        label = busy
```

训练时只使用 `quiet/moderate/busy`；`no_data` 样本不进入 supervised training 和 evaluation。

### Venue 状态字段

建议在候选清单或派生表中保留以下字段：

| 字段 | 含义 |
|------|------|
| `label_status` | `has_popular_times`, `no_popular_times`, `api_not_checked`, `api_error`, `out_of_scope_category` |
| `ml_eligible` | 是否允许进入 supervised ML training/evaluation |
| `prediction_source` | `ml_model`, `rule_fallback`, `none` |
| `display_level` | `quiet`, `moderate`, `busy`, `no_data` |
| `serpapi_checked_at` | SerpApi 检查时间 |
| `serpapi_place_id` | Google Maps place id |
| `serpapi_data_id` | SerpApi/Google Maps data id |

### SerpApi 额度策略

每月 250 次额度不支持先抓取 4000+ venues 再筛选，必须先离线筛选候选，再调用 SerpApi。

1. 从 cleaned venues 中按 `category x district/grid` 做 stratified sampling。
2. 优先选择 reviews/rating 较高、靠近 Citi Bike station、地理覆盖均衡的 venue。
3. 每个核心 category 和主要区域设置 minimum quota，避免某类或某区域全丢。
4. 对候选 venue 调 SerpApi Google Maps Place Results API，检查是否有 `popular_times` / busy score。
5. 原始 response 必须缓存，后续解析逻辑变更时不得重复浪费额度。
6. 预计 250 次调用中只有一部分会返回可用 label，因此 ML labeled set 应保守估计为 80-180 个 venue，而不是承诺稳定几百个。

候选优先级可按以下规则实现：

```text
priority_score =
    category_importance
  + log(review_count)
  + rating_quality
  + distance_to_nearest_bike_station_bonus
  + geographic_coverage_bonus
  - duplicate_or_low_confidence_penalty
```

### 存储产物

| 产物 | 说明 |
|------|------|
| `serpapi_raw_responses` | 原始 JSON、request URL、timestamp、place_id、status、error |
| `venues_label_status` | 每个 venue 的 label 可用性、ML eligibility、fallback 状态 |
| `venue_hourly_popularity` | `venue_id`, `day_of_week`, `hour`, `busyness_score`, `peak_vol`, `ratio`, `label` |
| `venue_ml_candidates.csv` | 可训练 venue 子集 |
| `venue_coverage_audit.csv` | category / district / grid 覆盖审计结果 |

### Notebook 分工

`dqr_cleaning_pipeline.ipynb` 只负责原始数据质量与清洗：

- 缺失值、重复、坐标合法性
- borough/district 修正
- venue 类型、rating、reviews 基础质量检查
- 输出 cleaned venues

`venue_coverage_walkthrough.ipynb` 负责 ML label coverage 与候选筛选：

- SerpApi candidate selection
- category coverage audit
- district/grid geographic coverage audit
- Citi Bike proximity coverage audit
- dropped/no_data/out-of-scope reporting
- final ML-labeled candidate list

实际文件：

- `Group6_Summer-Project/Data+ML/test/6.8-6.12_DB/dqr_cleaning_pipeline.ipynb`
- `Group6_Summer-Project/Data+ML/test/6.15-5.20/venue_coverage_walkthrough.ipynb`

### Rule Fallback 与展示语义

无 SerpApi label 的 venue：

- ML training: `label_status = no_data`, `ml_eligible = false`
- ML evaluation: 排除，不计入 accuracy/F1
- 内部报告: 显示 `no_data`，用于解释 label coverage
- 应用展示: 可显示 `rule_fallback` 的 `quiet/moderate/busy`，但必须保留 `prediction_source = rule_fallback`

MVP 可先显示 `no_data`；若要保证用户体验，则用规则系统补齐，但不得把 fallback 结果包装成 ML prediction。

### 汇报口径

推荐对 mentor 的说明：

> We keep the full venue catalogue for the application. SerpApi/Google Popular Times availability only defines the supervised ML boundary. Venues with reliable busy labels are used for model training and evaluation; venues without labels remain in the application but are marked as out of scope for supervised ML and handled by rule-based fallback or no_data. This avoids pretending that unlabeled venues have verifiable ML predictions, while preserving product coverage.

### 验收标准

- 原始 venue 总量不因 label 缺失而减少。
- 每个 venue 都有明确 `label_status` 和 `ml_eligible`。
- ML train/evaluation 数据集中不得包含 `no_data`。
- coverage audit 必须输出 category、district/grid、Citi Bike proximity 三类覆盖报告。
- 若某 category 或区域 label 覆盖为 0，必须在报告中显式标记，不得隐式补入 ML 训练。
- 所有 SerpApi 原始 response 必须缓存。
- 最终预测输出必须包含 `prediction_source`，区分 `ml_model` 与 `rule_fallback`。
