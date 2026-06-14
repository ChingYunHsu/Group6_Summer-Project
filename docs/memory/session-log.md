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

