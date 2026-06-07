# API Schema Gap 分析状态

## 对比文件
- `src/mock_data.py` — 前端 mock 数据
- `Data+ML/test/6.2-6.5_DB/api_schema_gap_analysis_en.md` — Gap 分析文档
- `Data+ML/test/6.2-6.5_DB/001_clearpath_schema.sql` — 数据库 Schema

## 已解决冲突 (2026-06-06)

| 问题 | 处理 |
|------|------|
| `phone_number` vs `phone` | mock_data.py 已改为 `phone` |
| `weather_risk` 标 ❌ | 实际已有，gap_analysis 已更新为 ✅ |
| `forecast_4h/8h` 标 ❌ | 已从 DB 删除，gap_analysis 已更新为 ✅ |
| `supported_services` 无 DB 列 | API 层计算，不存 DB |

## 剩余字段映射（API 层处理）
| API 字段 | DB 列 | 解决方式 |
|----------|-------|----------|
| `category` | `venue_type` | API 层映射 `venue_type` → `category` |
| `busyness_forecast_12h` | `forecast_1h` (JSON) | API 层转换 12h 数组 |
| `supported_services` | 无 DB 列 | API 层从 venue 属性计算 |

## Docker Schema 文件
`docker/mysql/init/001_clearpath_schema.sql` 与 `6.2-6.5_DB/001_clearpath_schema.sql` **不同步**，需要手动同步。
