# ClearPath 6.2 Codex 工作记录

## 1. 目录边界

`ml_training/plan/6.2_codex` 是 Codex 专属工作区，用于保存 Codex 对数据库架构、数据源范围、过程记录和后续任务的整理。

边界约定：

- `ml_training/plan/6.2_codex`：Codex 工作记录与 Codex schema 副本。
- `ml_training/plan/6.2_CC`：CC / Claude 风格参考文档，不由 Codex 修改。
- `ml_training/plan/6.2`：如存在，应视为其他 agent / Claude 任务区，不由 Codex 修改。
- Docker 初始化主 schema 当前使用 Codex 方案：`docker/mysql/init/001_clearpath_schema.sql`。

## 2. 本轮目标

本轮目标是为 ClearPath Sprint 1 的 Data Analysis & ML Lead 工作建立数据库和数据底座：

- 明确保留数据源范围。
- 设计合理数量的 MySQL 8.4 表。
- 合并同类型数据源，避免 one-table-per-source。
- 保留数据来源追踪。
- 为后续 ETL、API、ML busyness prediction 提供结构基础。
- 生成过程文档和后续任务清单。

## 3. 已确认的数据源范围

只使用 9 个来源：

| Type | Source | Role |
| --- | --- | --- |
| Internal | User Reports Database | 实时报告与确认 |
| Toilet | NYC Public Restrooms `i7jb-7jku` | 主要厕所数据 |
| Toilet | Directory of Toilets in Public Parks `hjae-yuav` | 公园厕所补充 |
| Healthcare | OpenStreetMap / Overpass POI | 广覆盖医疗 POI |
| Healthcare | NYS Health Facility General Information `vn5v-hh5r` | 官方医疗设施验证 |
| Healthcare | AED Inventory `2er2-jqsx` | AED / emergency asset |
| Accessibility | Pedestrian Ramp Locations `ufzp-rrqu` | 轮椅路线基础设施 |
| Traffic | Google Map API | 路线 / 交通上下文缓存 |
| Weather | Weather / NYC Urban Heat Portal | 天气 / 热风险上下文缓存 |

明确排除：

- `POI_accessibility.geojson`
- HRSA
- CityMD
- Google Places
- MTA outages / stations
- Taxi data
- Traffic volume counts
- Language datasets
- 任何未在 9 个来源中列出的数据源

## 4. 已完成任务

### 4.1 数据库 schema

已设计并落地 MySQL 8.4 / 10 表 Codex schema：

1. `venues`
2. `venue_source_links`
3. `restroom_profiles`
4. `healthcare_profiles`
5. `emergency_assets`
6. `pedestrian_ramps`
7. `user_reports`
8. `report_confirmations`
9. `busyness_scores`
10. `external_context_cache`

对应文件：

- `docker/mysql/init/001_clearpath_schema.sql`
- `ml_training/plan/6.2_codex/001_clearpath_schema.sql`

两份 schema 应保持完全一致。

### 4.2 数据源 manifest 与验证

已新增：

- `backend/database/clearpath_sources.json`
- `backend/database/validate_sources.py`
- `backend/database/README.md`

作用：

- 记录 9 个保留来源。
- 记录废弃本地文件。
- 校验 6 个本地数据文件存在。
- 防止废弃来源被误加入 MVP 数据库路径。

### 4.3 数据库架构文档

已扩展：

- `ml_training/plan/database.md`
- `ml_training/plan/6.2_codex/database.md`

内容吸收了 CC 文档结构，但保持 Codex 的 9 来源 + 10 表方案。新增重点：

- 需求来源与当前约束
- 整体架构
- 云端 MySQL 表分层
- ER 关系图
- 数据合并规则
- 字段映射摘要
- 数据质量问题
- 索引策略
- API 与数据库映射
- ETL Flow
- 非功能需求
- 验收标准

### 4.4 过程文档

已写入：

- `ml_training/plan/6.2_codex/database_implementation_process.md`

记录内容：

- 输入范围
- 设计决策
- 已实现文件
- 10 张表
- 验证命令和结果
- 下一步 ETL / API 接入方向

### 4.5 测试与验证

已新增：

- `test/6.2_DB/test_database_plan.py`

已通过验证：

```bash
python3 -m unittest test/6.2_DB/test_database_plan.py
python3 backend/database/validate_sources.py
docker compose config
cmp docker/mysql/init/001_clearpath_schema.sql ml_training/plan/6.2_codex/001_clearpath_schema.sql
```

验证结果：

- schema 只包含 Codex 10 表。
- manifest 只包含 9 个来源。
- 6 个本地数据文件存在。
- Docker Compose config 有效。
- Docker initializer 与 Codex schema 副本一致。

## 5. 本轮关键判断

### 5.1 Data Lead 与 Backend Lead 的责任拆分

Data & ML Lead 负责：

- 数据源选择
- 数据采集
- 数据清洗
- 字段映射
- 数据质量问题
- 去重规则
- ETL 逻辑
- ML 特征与 `busyness_scores` 输出

Backend Lead 负责：

- Flask API 与数据库连接
- endpoint 实现
- Docker / MySQL 运行环境
- 数据库连接池、事务、部署
- 非功能需求在后端架构中的实现

共同边界：

- schema 概念设计
- API contract 与数据库字段对齐
- 查询路径和索引策略

### 5.2 当前完成度

如果目标是“数据库搭建架构分析 + schema 落地设计”，当前完成度约 **80%**。

如果目标是“完整数据库系统可运行并有真实数据”，当前完成度约 **45%-50%**。

尚未完成：

- 实际启动 MySQL 并执行建表检查。
- ETL 脚本导入 CSV / GeoJSON。
- 厕所、医疗、AED 去重合并逻辑。
- Flask API 查询数据库。
- ML baseline / dummy score 写入 `busyness_scores`。
- Google Maps / Weather cache 真实接入。

## 6. 文件索引

| File | Purpose |
| --- | --- |
| `ml_training/plan/6.2_codex/readme.md` | Codex 工作记录总览 |
| `ml_training/plan/6.2_codex/todolist.md` | Sprint 1 后续任务清单 |
| `ml_training/plan/6.2_codex/001_clearpath_schema.sql` | Codex schema 副本 |
| `ml_training/plan/6.2_codex/database.md` | Codex 架构文档副本 |
| `ml_training/plan/6.2_codex/database_implementation_process.md` | 过程记录 |
| `ml_training/plan/database.md` | 当前主数据库架构文档 |
| `docker/mysql/init/001_clearpath_schema.sql` | Docker MySQL initializer |
| `backend/database/clearpath_sources.json` | 数据源 manifest |
| `backend/database/validate_sources.py` | 数据源校验脚本 |
| `tests/test_database_plan.py` | schema / manifest 测试 |

## 7. 注意事项

- 不要把 CC schema 中的 `toilets`、`reports`、`busyness_predictions`、`traffic_cache`、`weather_cache` 直接合并到 Codex schema。
- CC 文档可作为 presentation / task breakdown / field mapping 参考，但 Docker initializer 的 source of truth 是 Codex 10 表 schema。
- 后续如果需要修改 schema，应同时更新：
  - `docker/mysql/init/001_clearpath_schema.sql`
  - `ml_training/plan/6.2_codex/001_clearpath_schema.sql`
  - `ml_training/plan/database.md`
  - `test/6.2_DB/test_database_plan.py`
