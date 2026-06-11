# ClearPath DQR + Cleaning Pipeline

> 创建日期：2026-06-09 | 数据源：Docker MySQL `clearpath` 库
> 目标：标准 7 模块 DQR → 清洗 → 输出 CSV 给 ML 拥挤度预测

## 决策清单 (grill-me 2026-06-09)

| # | 决策 | 结论 |
|---|------|------|
| D1 | ML 任务 | 拥挤度预测 = 时间序列 + 用户报告（大权重） |
| D2 | 数据源 | Docker MySQL (`clearpath` 库) — 数据由 `database_build.ipynb` 加载 |
| D3 | 交付形式 | 新建独立 notebook |
| D4 | Venue 类别 | 医疗 / AED / Restroom 三大类 |
| D5 | 历史交通 | NYC SODA API (`7ym2-wayt`) Manhattan 2024-2025 |
| D6 | 实时交通 | TomTom Flow API |
| D7 | 天气 | NWS API |
| D8 | DQR 深度 | 分析 + 清洗 pipeline |
| D9 | 空间范围 | Manhattan |
| D10 | 时间粒度 | 15min → 小时级聚合 |
| D11 | 输出格式 | 只输出 CSV，不写 DB |
| D12 | DQR 结构 | 标准 7 模块（Executive Summary → Appendix） |

---

## DQR 标准 7 模块结构

```
dqr_cleaning_pipeline.ipynb
├── Part 0: Configuration & DB Connection
├── 1. Executive Summary（执行摘要）
├── 2. Data Profiling（数据画像）
│   ├── 2.1 Column-level Analysis（列级分析）
│   ├── 2.2 Row-level Analysis（行级分析）
│   └── 2.3 Cross-table Analysis（跨表分析）
├── 3. Data Quality Dimensions（质量维度评估）
│   ├── 3.1 Completeness（完整性）
│   ├── 3.2 Accuracy（准确性）
│   ├── 3.3 Consistency（一致性）
│   ├── 3.4 Uniqueness（唯一性）
│   ├── 3.5 Timeliness（及时性）
│   └── 3.6 Validity（有效性）
├── 4. Anomaly Detection（异常检测）
├── 5. DQ Score & Rating（质量评分）
├── 6. Cleaning Pipeline（清洗 + CSV 输出）
├── 7. Action Items & Recommendations（改进建议）
└── 8. Appendix（附录）
```

---

## 数据源 (MySQL)

### DQR 范围内表

| 表名 | 用途 | Busyness 相关性 |
|------|------|----------------|
| `venues` | 主场馆表 | 核心 — 场馆属性 |
| `restroom_profiles` | 卫生间详情 | 中 — 状态/可访问 |
| `healthcare_profiles` | 医疗详情 | 中 — 设施类型 |
| `emergency_assets` | AED 数据 | 中 — 位置/楼层 |
| `pedestrian_ramps` | 无障碍坡道 | 低 — 空间特征 |
| `venue_source_links` | 数据溯源 | 高 — 完整性追踪 |
| `busyness_scores` | 拥挤度预测 | 核心 — 目标变量 |
| `external_context_cache` | 缓存 API 数据 | 高 — 天气/交通 |

### DQR 范围外表 (不分析)

`users`, `user_favorite_venues`, `notification_preferences`, `report_categories`, `venue_embeddings`, `venue_language`, `venue_warnings`, `user_reports`, `report_confirmations`, `busyness_forecasts`

### 外部 API 数据

| API | 端点 | 用途 |
|-----|------|------|
| NYC SODA | `data.cityofnewyork.us/resource/7ym2-wayt.json` | 历史交通流量 |
| TomTom | `api.tomtom.com/traffic/services/4/flowSegmentData` | 实时交通 |
| NWS | `api.weather.gov/gridpoints/OKX/33,37/forecast` | 天气 |

---

## 代码复用策略

- `dqr_utils.py` (在 `6.2-6.5_DB/`)：提取共享函数（`get_conn`, `is_manhattan`, `gps_to_district`, `validate_coords`, `haversine_m`, `source_hash`, `gen_vid`）
- DQR notebook 通过 `sys.path` 导入 `dqr_utils`
- `database_build.ipynb` **不修改** — 避免触碰工作中的 notebook

---

## 输出文件

| 文件 | 内容 |
|------|------|
| `venues_clean.csv` | 清洗后场馆（统一 schema） |
| `traffic_hourly.csv` | 曼哈顿小时级交通 |
| `weather_current.csv` | 当前天气 |
| `dqr_field_summary.csv` | 列级 profiling |
| `dqr_record_analysis.csv` | 行级质量评分 |
| `dqr_gps_duplicates.csv` | 跨源 GPS 重复 |
| `dqr_outliers.csv` | 坐标异常 |
| `dqr_report.csv` | 审计日志 |
| `dqr_missing_heatmap.png` | 缺失率热力图 |
| `dqr_venue_scatter.png` | 场馆分布图 |
| `dqr_dimension_scores.png` | 六维度雷达图 |

---

## 已知 DQR 问题 (来自 `database.md` Section 10)

| 问题 | 表 | 影响 | 清洗策略 |
|------|-----|------|----------|
| Parks Toilets 无坐标 | venues (restroom) | 无法空间分析 | 跳过无坐标记录 |
| NYS Health 部分无坐标 | venues (healthcare) | 同上 | 同上 |
| OSM 标签不一致 | venue_source_links | 标准化困难 | 统一标签映射 |
| AED 无稳定 ID | emergency_assets | 去重困难 | hash(venue_id + floor) |
| 跨源重复 POI | venues (多类型) | 场馆重复 | GPS 30m 聚类 + 优先级 |
| 交通坐标系不一致 | external_context_cache | WKT→WGS84 | pyproj 转换 |

---

## 前置条件

1. Docker MySQL 运行中：`docker-compose up -d mysql`
2. 数据已加载：运行 `database_build.ipynb`
3. Python 依赖：`pymysql`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `requests`
