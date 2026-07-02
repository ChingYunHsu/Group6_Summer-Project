# 6.22-6.27 SerpApi Label Coverage Pipeline

> 更新日期：2026-06-28

## 目录

1. [文件结构](#文件结构)
2. [核心函数说明](#核心函数说明)
3. [输出目录结构](#输出目录结构)
4. [数据特征](#数据特征)
5. [数据流](#数据流)

---

## 文件结构

```
Data+ML/test/6.22-6.27/
├── src/                              # Python 源码
│   ├── geo_utils.py                  # 公共空间计算（Haversine 距离）
│   ├── serpapi_client.py             # 公共 SerpAPI HTTP 客户端（缓存+重试）
│   ├── api_usage_tracker.py          # API 配额追踪器
│   ├── healthcare_common.py          # 公共工具（resolve_path, name matching, label 更新）
│   ├── venue_serpapi.py              # 兼容 facade：import venue_serpapi as vs 仍可用
│   ├── run_phased_search.py          # 主入口：分层抽样 + Phase A/B 预算控制
│   ├── validate_search_matched_places.py  # Place API 验证
│   ├── dedupe_healthcare_discovery_matches.py # 去重发现结果
│   ├── build_healthcare_coverage_label_view.py # 合并覆盖率视图
│   ├── build_healthcare_prediction_groups.py  # 离线预测分组
│   ├── write_healthcare_prediction_groups_to_db.py # 写回 MySQL
│   ├── populartimes_coverage_summary.py       # 离线覆盖率摘要
│   └── run_phased.sh                 # Shell 包装器（读 .serpapi_key）
├── output/                           # 输出产物
│   └── (详见下方)
└── serpapi_label_coverage.ipynb      # Notebook 入口
```

---

## 核心函数说明

### geo_utils.py — 空间计算工具

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `haversine_distance_m(lat1, lng1, lat2, lng2)` | `float, float, float, float` | `float` | 单对坐标 Haversine 距离（米） |
| `haversine_distances_m(venues, lat, lng)` | `DataFrame, float, float` | `ndarray` | 向量化：venues DataFrame 每行到 (lat,lng) 的距离数组 |

常量：`EARTH_RADIUS_M = 6_371_008.8`

### serpapi_client.py — SerpAPI HTTP 客户端

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `serpapi_request(params, api_key, output_dir, cache_prefix)` | `dict, str, Path, str` | `dict \| None` | 带磁盘缓存 + 重试的 SerpAPI 请求 |
| `get_cache_path(output_dir, prefix, params)` | `Path, str, dict` | `Path` | 返回缓存文件路径 |

常量：`SERPAPI_BASE_URL`, `SERPAPI_TIMEOUT = (3, 10)`, `SERPAPI_MAX_RETRIES = 3`

### venue_serpapi.py — 兼容 facade

所有 `import venue_serpapi as vs` 的脚本和 notebook 继续正常工作。
内部已迁移到 `geo_utils` 和 `serpapi_client`；`_find_matching_venues()` 使用 `haversine_distances_m`。

**模块级常量：**
- `EARTH_RADIUS_M = 6_371_008.8` — 地球平均半径（米）
- `DISTRICT_CENTERS` — Manhattan 4 个区域中心坐标
- `SERPAPI_SEARCH_CATEGORIES` — Search 查询模板列表 `(search_query, google_type, clearpath_type)`
- `OUT_OF_SCOPE_CATEGORIES = {"emergencyasset"}` — ML 范围外类别
- `CATEGORY_IMPORTANCE` — 各 venue_type 的重要性权重

**数据类：**
- `SerpApiSearchResult` — 单个 Search 发现结果
- `VenueLabelStatus` — 单个 venue 的 ML 标签状态
- `CoverageAuditRow` — 覆盖率审计行

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `load_venues(csv_path)` | `str \| Path` | `tuple[DataFrame, int]` | 加载去重 venues CSV，返回 (df, dup_count) |
| `get_review_count(name)` | `str` | `int` | 从 venue 名称估算 review 数（确定性 hash 占位） |
| `calculate_priority_score(...)` | `venue_type, district, review_count, rating, citibike_distance_m, district_label_coverage, is_duplicate` | `float` | SOP 优先级评分公式 |
| `audit_coverage_by_category(venues, label_status_df)` | `DataFrame, DataFrame?` | `DataFrame` | 按 venue_type 统计覆盖率 |
| `audit_coverage_by_district(venues, label_status_df)` | `DataFrame, DataFrame?` | `DataFrame` | 按 district 统计覆盖率 |
| `audit_citi_bike_proximity(venues, citibike_detail)` | `DataFrame, DataFrame?` | `DataFrame` | 按 Citi Bike 距离桶统计覆盖率 |
| `batch_search_discovery(venues, api_key, output_dir, ...)` | `DataFrame, str, Path, ...` | `list[SerpApiSearchResult]` | 批量 Search API 发现（category×district） |
| `_find_matching_venues(venues, lat, lng, max_distance_m)` | `DataFrame, float, float, float` | `DataFrame` | 在 max_distance_m 内查找匹配 venue |
| `validate_candidates_with_place_api(candidates, api_key, output_dir, max_calls)` | `list, str, Path, int` | `list[SerpApiSearchResult]` | Place API 验证 popular_times |
| `generate_label_status(venues, search_results, citibike_detail)` | `DataFrame, list, DataFrame?` | `DataFrame` | 生成全量 venue 标签状态 |
| `generate_candidate_list(label_status_df, output_path)` | `DataFrame, Path` | `DataFrame` | 生成 ML 候选列表（ml_eligible=True） |
| `generate_coverage_report(...)` | `category_audit, district_audit, citibike_audit, label_status_df, search_results, output_path` | `str` | 生成 Markdown 审计报告 |
| `save_run_metadata(...)` | `venues, search_results, label_status_df, output_dir, api_calls_search, api_calls_place` | `dict` | 保存运行元数据 JSON |

### api_usage_tracker.py — API 配额追踪

**类 `ApiUsageTracker`：**

| 方法 | 说明 |
|------|------|
| `__init__(output_dir, run_id?)` | 初始化追踪器 |
| `.search_calls` / `.place_calls` / `.total_calls` | 属性：调用计数 |
| `log_search_call(query, district, category, success, ...)` | 记录一次 Search 调用 |
| `log_place_call(place_id, venue_name, success, has_popular_times, ...)` | 记录一次 Place 调用 |
| `summary()` | 返回统计 dict |
| `print_summary(script_name)` | 打印格式化摘要 |
| `save()` | 保存 JSON + 追加 JSONL 日志 |

### healthcare_common.py — 公共工具

| 函数 | 说明 |
|------|------|
| `resolve_path(path)` | CLI 路径解析（相对脚本目录） |
| `load_uncovered_healthcare(label_file, statuses)` | 加载指定 status 的 healthcare venue |
| `normalize_name(value)` | 小写、去空格、`&` → `and` |
| `name_similarity(left, right)` | SequenceMatcher 名称相似度 (0–1) |
| `require_api_key(dry_run, confirm_live_api)` | API key 守卫：dry-run 返回 None，否则校验 |
| `apply_label_updates(labels, result_lookup, ...)` | 批量更新 label_status/ml_eligible/prediction_source 等列 |

### validate_search_matched_places.py — Place API 验证

| 函数 | 说明 |
|------|------|
| `load_validation_targets(coverage_view_file)` | 加载 `search_matched_unvalidated` 的 healthcare 行 |
| `validate_place(place_id, api_key, output_dir)` | 调用 Place API 检查 popular_times |
| `run_validation(...)` | 主执行函数 |

### build_healthcare_coverage_label_view.py — 合并覆盖率视图

| 函数 | 说明 |
|------|------|
| `apply_batch_results(labels, batch_file)` | 同步 batch 结果到 labels |
| `apply_discovery_matches(labels, discovery_map_file)` | 同步 discovery 映射（标记 `search_matched_unvalidated`） |
| `rename_unmatched_healthcare(labels)` | 未匹配 healthcare → `search_not_matched` |
| `apply_restroom_audit(labels, restroom_audit_file)` | 同步 restroom Popular Times 审计 |
| `build_label_view(...)` | 主函数 |

### build_healthcare_prediction_groups.py — 离线预测分组

| 函数 | 说明 |
|------|------|
| `build_group_id(row)` | 用 place_id 或 venue_id 构建分组 ID |
| `build_prediction_groups(coverage_view_file)` | 主函数，输出 3 个 CSV |

### populartimes_coverage_summary.py — 离线覆盖率摘要

| 函数 | 说明 |
|------|------|
| `default_paths(project_root)` | 返回默认文件路径 dict |
| `build_type_summary(venues, label_scope)` | 按 venue_type 统计覆盖率 |
| `build_status_breakdown(label_scope)` | label_status 分布 |
| `build_district_summary(venues, label_scope)` | 按 district 统计 |
| `build_summary_bundle(...)` | 一次性返回所有展示表 |

### write_healthcare_prediction_groups_to_db.py — 写回 MySQL

| 函数 | 说明 |
|------|------|
| `write_healthcare_groups(grouped_view_file, live)` | 自动添加缺失列 + UPDATE 写入 MySQL `venues` 表 |

---

## 输出目录结构

```
output/
├── venue_label_status.csv                    # 基线标签状态（全量 4,838 行）
├── venue_label_status_coverage_view.csv      # 合并覆盖率视图（含 discovery + batch + restroom）
├── venue_label_status_grouped_view.csv       # 分组视图（含 prediction_group_id）
├── venue_ml_candidates.csv                   # ML 候选列表（仅 ml_eligible=True）
├── healthcare_prediction_groups.csv          # 预测分组汇总
├── healthcare_prediction_group_members.csv   # 预测分组成员明细
├── healthcare_uncovered_discovery_matches.csv # Discovery 匹配结果
├── restroom_popular_times_audit.csv          # Restroom Popular Times 审计
├── run_metadata.json                         # 运行元数据
├── api_usage_20260628T222906Z.json           # API 配额消耗摘要
├── api_usage_log.jsonl                       # API 调用逐条日志
├── coverage_audit_report_zh.md               # 中文覆盖率审计报告
└── serpapi_raw_responses/                    # SerpApi 原始 JSON 响应缓存
    └── *.json (81 个文件)
```

---

## 数据特征

### venue_label_status.csv — 基线标签

| 指标 | 值 |
|------|-----|
| 总行数 | 4,838 |
| 列数 | 18 |
| venue_type 分布 | emergencyasset=3,279 · healthcare=1,086 · restroom=473 |
| district 分布 | downtown=1,467 · midtown_west=1,428 · midtown_east=1,182 · uptown=703 |
| label_status | api_not_checked=4,799 · has_popular_times=35 · no_popular_times=4 |
| ml_eligible | True=35 · False=4,803 |

> ⚠️ 此文件为 DRY-RUN 合成数据，LIVE 运行后数值会变化。

### venue_label_status_coverage_view.csv — 合并覆盖率视图

| 指标 | 值 |
|------|-----|
| 总行数 | 4,838 |
| label_status | search_not_matched=4,254 · api_not_checked=471 · has_popular_times=71 · no_popular_times=42 |
| ml_eligible | True=71 · False=4,767 |

> 相比基线文件，更多 venue 被评估（`api_not_checked` 减少，`search_not_matched` 增加）。

### venue_label_status_grouped_view.csv — 预测分组视图

| 指标 | 值 |
|------|-----|
| 总行数 | 4,838 |
| 列数 | 22（基础 18 + prediction_group_id, prediction_shared, group_match_source, group_member_count） |
| group_type | fallback_singleton=4,560 · shared_place=278 |
| prediction_shared | False=4,560 · True=278 |

> `shared_place` 表示多个本地 venue 共享同一个 Google Place 的预测结果。

### venue_ml_candidates.csv — ML 候选列表

| 指标 | 值 |
|------|-----|
| 总行数 | 35 |
| 全部为 | label_status=has_popular_times · ml_eligible=True · prediction_source=ml_model |
| venue_type | 全部 healthcare |
| district 分布 | midtown_west=17 · midtown_east=10 · uptown=5 · downtown=3 |
| display_level | 全部 quiet |

### healthcare_prediction_groups.csv — 预测分组汇总

| 指标 | 值 |
|------|-----|
| 总行数 | 488 |
| group_type | shared_place=278 · fallback_singleton=210 |
| has_popular_times | 0=416 · 1=72 |

### healthcare_prediction_group_members.csv — 分组成员明细

| 指标 | 值 |
|------|-----|
| 总行数 | 1,426 |
| group_type | fallback_singleton=1,148 · shared_place=278 |
| prediction_source | venue_id_fallback=1,148 · serpapi_place_id=278 |

### healthcare_uncovered_discovery_matches.csv — Discovery 匹配

| 指标 | 值 |
|------|-----|
| 总行数 | 337 |
| 列数 | 22 |
| label_status | 全部 search_matched_unvalidated |
| name_similarity | 范围 0.48–0.97 |
| place_checked | 全部 False（待 Place API 验证） |

### restroom_popular_times_audit.csv — Restroom 审计

| 指标 | 值 |
|------|-----|
| 总行数 | 425 |
| has_popular_times | True=47 · False=378 |
| counts_as_restroom_coverage | True=47 · False=378 |
| exclude_reason | direct_restroom_without_popular_times=378 · (空)=47 |

### run_metadata.json — 运行元数据

```json
{
  "run_id": "20260628T224231Z",
  "venue_input": { "total_rows": 4838 },
  "serpapi_usage": { "total_calls": 0, "monthly_quota_remaining": 250 },
  "results": { "total_discovered": 80, "with_popular_times": 30 },
  "label_status": { "has_popular_times": 35, "no_popular_times": 4 },
  "ml_eligible_count": 35
}
```

### serpapi_raw_responses/ — API 响应缓存

- 文件数量：81 个 JSON
- 命名规则：`{type}_{place_id_hash}.json`（如 `restroom_place_b8627331c38a.json`）
- 内容：SerpApi Search/Place API 完整响应（含 popular_times、reviews、photos 等）

---

## 数据流

```
run_phased_search.py (主入口)
  │
  ├── Phase A: 分层抽样 DB-driven Search → phase_a_search_results.csv
  │
  ├── Phase B: Place API on unique place_ids → phase_b_place_results.csv
  │
  └── merge: 更新 venue_label_status_coverage_view.csv
                  │
validate_search_matched_places.py  ← discovery 匹配的 Place API 验证
                  │
build_healthcare_coverage_label_view.py  ← 合并 batch + discovery + restroom
                  ↓ venue_label_status_coverage_view.csv
         build_healthcare_prediction_groups.py  ← 离线分组
                  ↓ venue_label_status_grouped_view.csv
         write_healthcare_prediction_groups_to_db.py → MySQL
```

**覆盖策略（统一入口 `run_phased_search.py`）：**

| Phase | 说明 | API 消耗 |
|-------|------|----------|
| **Phase A** | 分层抽样 DB-driven Search（按 subtype 分配预算） | 低（每个 venue 1 次 Search） |
| **Phase B** | 对 Phase A 去重后的 unique place_id 调 Place API | 中（每个 unique place 1 次 Place） |
