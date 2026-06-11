# 会话日志

> 用于记录重要完成项、阻塞项和后续跟进的持久化跨会话笔记。

---

## 2026-06-10 — Codex 本地对话丢失分析

- 现象：之前标题为 `codex对话丢失,检查配置` 的 Codex 线程在本地状态里存在，但新的活动线程没有把那段上下文带过来。
- 证据：`~/.codex/state_5.sqlite` 同时包含归档线程记录和新活动线程记录；归档线程标记为 `archived=1`。
- 证据：`~/.codex/config.toml` 里 `context-mode` 已启用，`hooks` 已启用，`memory_mode = "enabled"`，看起来不像是整体记忆被关闭。
- 证据：在写入这条笔记之前，`docs/memory/session-log.md` 并不存在，尽管 `AGENTS.md` 要求把重要工作写入持久化会话日志。
- 推断：这更像是一次 handoff / archive 边界上的上下文丢失，而不是全局记忆系统失效。前一个线程被保存在本地状态里，但没有被恢复进新的活动线程。
- 后续：以后每次多轮分析都继续写入这份日志，保证下一次会话可以从项目的持久化记忆重新恢复上下文，而不是依赖临时聊天状态。

---

## 2026-06-10 — Cell 14/46 执行顺序 Bug 与修复

- **问题**: `database_build.ipynb` cell 14 (schema rebuild) 每次超时。
- **根因**: cell 46 (`SHOW CREATE TABLE` sync) 会把 migration 添加的 index（如 `idx_venues_type_district`）写回 SQL 文件，导致 cell 14 重建 schema 时引用尚未创建的列（`district` 是 cell 35 才添加的）。
- **额外根因**: SQL 文件含 `CREATE DATABASE`/`USE` 语句，`clearpath_app` 用户无 CREATE DATABASE 权限 → 异常；异常后 `conn` 无 `finally` 关闭 → 连接泄漏 → 超时。
- **修复**: 注释掉 cell 27/31/35/37/46（均为已完成或危险操作），cell 14 添加 `finally: conn.close()` + 跳过 `CREATE DATABASE`/`USE`。
- **教训**: notebook cell 执行顺序假设脆弱，`SHOW CREATE TABLE` 同步回写 SQL 是隐式循环依赖。 `[ses_14a4f112bfferlcsOw1C094HjM]`

---

## 2026-06-10 — DQR Pipeline Gap 修复

- **背景**: `dqr_cleaning_pipeline.ipynb` 存在 4 处缺口。
- **修复**:
  1. `dqr_record_analysis.csv` 缺失 → 新增 cell 生成 per-record 质量评分
  2. Traffic/Weather 函数未调用 → 取消注释 `fetch_traffic_hourly()` 和 `clean_weather()`，带 `try/except` 降级
  3. WKT→WGS84 未实现 → 新增 `wkt_to_latlng()` 解析 `POINT (x y)` EPSG:2263→WGS84
  4. `gen_vid` 引用不存在 → import 行补充 `gen_vid, source_hash, MANHATTAN_BOUNDS` + `import re`
- `[ses_14a4f112bfferlcsOw1C094HjM]`

---

## 2026-06-10 — venues 行数差异分析

- **现象**: README.md 记录 3,479，DQR 输出 4,841。
- **结论**: 3,479 是文档错误（应为 4,983 = 476+1,228+3,279）。4,841 是当前实际值。差异 142 条来自 OSM Healthcare（655 vs 计划 797），可能是不同版本数据源或 `ALLOWED_OSM_TYPES` 过滤变更。
- **状态**: project-status.md 中 ETL Row Counts 需更新。 `[ses_14a4f112bfferlcsOw1C094HjM]`

---

## 2026-06-10 — Data+ML 文件清理

- 交叉检查 `Data+ML/test/6.2-6.5_DB/` 中 5 个冗余 .md 文件（api_schema_gap_analysis CN/EN, fix_plan CN/EN, fix_summary），均已被 memory 记录覆盖，已删除。
- 剩余: `README.md`（notebook 完整文档）、`backend_database_README.md`（架构概览）。 `[ses_14a4f112bfferlcsOw1C094HjM]`

---

## 2026-06-11 — 架构检查确认

- `backend/` 目录为空（仅 `.gitkeep`），实际后端在 `src/`（Flask）。
- `project-status.md` 中的架构图和模块地图与实际代码一致。 `[ses_14a4e663affegfxKE16LRaRdQW]`


## 2026-06-11: Sprint 2 Data 任务审计

### 完成工作
1. **PR #12 分析** — alex 分支合并到 main，覆盖 6.1-6.10 版本
2. **Sprint 2 Data 任务审计** — 对比计划 vs 实际进度
3. **问题更新** — 新增 #18-#20 到 project-issues.md
4. **执行计划更新** — 详细更新 execution-plan.md

### 关键发现
- **已完成**: D2.1, D2.2, D2.3, D2.6 (4/7 任务)
- **进行中**: D2.4 (部分), D2.5 (DQR 完成)
- **未开始**: D2.7 (单元测试)
- **整体进度**: 60%

### 待办事项
1. D2.4 Mock 数据扩展 (4h)
2. D2.5 ML 模型实现 (8h)
3. D2.7 单元测试 (4h)

---

## 2026-06-11: DQR Pipeline 重构 + Park Toilet GPS 修复

### 完成工作

1. **DQR Notebook 拆分** — 从 40 cells/406 lines 拆为 21 cells/218 lines + 6 shared modules
   - `dqr_utils.py`, `dqr_io.py`, `dqr_checks.py`, `dqr_analysis.py`, `dqr_cleaning.py`, `external_ingestion.py`
   - 所有 imports 统一在 Cell 2
   - 输出移到 `output/` 子目录

2. **GPS 网格修复** — `detect_gps_duplicates` 经度网格按 `cos(40.88°)` 缩放，修复高纬度漏检

3. **导出覆盖修复** — `export_dqr_artifacts` 空结果时 `unlink()` 删除过期 CSV

4. **导入路径修复** — conftest.py 用 `Path(__file__)` 解析，cwd 无关

5. **D2.7 pytest** — 12 个测试用例覆盖 D2.7/GPS/导出/不可变性

6. **Park Toilet GPS** — 124 零坐标 restroom venues 修复
   - NYC Open Data (`i7jb-7jku`) 匹配 93 条 Manhattan 坐标
   - 3 条 Bronx Jackie Robinson Park 删除
   - CSV 更新: +Latitude/Longitude 列，126/126 Manhattan 有 GPS
   - DB: 473 restrooms, 100% GPS, 0 null districts

### 产出文件
- `Data+ML/test/shared/` — 6 modules (1,141 lines total)
- `Data+ML/test/6.8-6.12_DB/output/` — CSV + PNG outputs
- `Data+ML/test/6.8-6.12_DB/tests/test_dqr_modules.py` — 12 tests

### 文档更新
- `execution-plan.md` — Sprint 2 tasks D2.1-D2.7 全部标记完成
- `project-status.md` — File structure, DQR pipeline status, 进行中改为 ML forecast
- `project-overview.md` — 新增 DQR shared modules 架构描述
- `dqr-pipeline-architecture.md` — 新增 memory file

### Sprint 2 进度
- **D2.1-D2.4**: ✅ All completed
- **D2.5**: ⚠️ traffic_hourly.csv fetched; ARIMA/LSTM pending
- **D2.6**: ✅ GPS duplicate detection (grid + haversine)
- **D2.7**: ✅ 12 pytest cases in test_dqr_modules.py

### 决策
- 优先完成 D2.5 ML 模型，因为阻塞 Sprint 3
- D2.4 Mock 数据可与 D2.5 并行
