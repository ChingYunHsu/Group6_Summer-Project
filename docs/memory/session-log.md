# 会话记录

## 2026-06-06

### 完成事项
- ✅ 删除 `busyness_scores` 表的 `forecast_4h` 和 `forecast_8h` 字段
- ✅ 更新 SQL 文件 `001_clearpath_schema.sql`
- ✅ 在数据库中执行 DROP COLUMN
- ✅ 修复 `SCHEMA_PATH` 指向 `6.2-6.5_DB/`
- ✅ 更新 `expected_tables` 为 13 个表
- ✅ 修正 Cell 11 markdown 中的 cell 引用
- ✅ 添加 `emergency_assets` 唯一约束到 MIGRATIONS
- ✅ 更新 `migration_is_applied` 支持 `index` 类型
- ✅ 更新 `api_schema_gap_analysis_en.md` 状态
- ✅ 修改 `mock_data.py` 中 `phone_number` → `phone`
- ✅ 保存项目记忆到 `docs/memory/`
- ✅ 解析 Backend/Data Lead Pipeline 文档（Sprint 2-4 需求）
- ✅ 实现 District Zoning（GPS→district 映射）
- ✅ 更新 mock_data.py: phone_number→phone
- ✅ 更新 api_schema_gap_analysis_en.md（forecast/weather_risk/supported_services）
- ✅ 更新 venue_language markdown: 61→63
- ✅ 修正 MANIFEST_PATH 指向 6.2-6.5_DB/

### 关键决策
- SQL 文件需要手动执行 "Sync schema file" cell 才能与数据库同步
- PR 目标分支是 `main` (不是 `dev`)
- `emergency_assets` 需要唯一约束 `(venue_id, floor, location_type)` 防止重复写入
- `category`/`venue_type` 和 `phone_number`/`phone` 字段名差异由 API 层映射处理
- District Zoning 只改 2 张表（venues + pedestrian_ramps），其他表通过 JOIN 获取
- MySQL 5.7 不支持 ALTER TABLE ADD COLUMN COMMENT 语法
- Cell 37 (Migrations) 必须在 ETL Cell 之前执行，否则 district 列不存在

### 新增记忆文件
- `docs/memory/database-build-notebook-status.md` — Notebook 状态和执行顺序
- `docs/memory/api-schema-gap-status.md` — API Schema 对齐状态
- `docs/memory/pipeline-requirements.md` — Sprint 2-4 Backend/Data Pipeline 需求总结

### Git 历史 (eq_sprint1)
- `2d1aac8` - Merge commit
- `f914e82` - feat: insights API + OpenAPI
- `0d713ec` - Fix AttributeError

### 待办事项
- [ ] 完成其他 API 开发
- [ ] 前端开发
- [ ] 部署配置
