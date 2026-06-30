# ML 下一步任务整理

> 日期：2026-06-29  
> 输入材料：
> - `Group6_Summer-Project/docs/memory/ML_SOP.md`
> - `Group6_Summer-Project/Data+ML/test/6.28-7.3/log.md`
> - `Group6_Summer-Project/Data+ML/test/6.28-7.3/ML.ipynb`

## 0. 当前事实基线

- 模型目标仍应表述为 `Google Popular Times proxy busyness`，不能表述为真实 foot traffic。
- 当前监督训练范围只包含 `venue_type = healthcare`。
- `restroom` 与 `emergencyasset / AED` 不进入当前 ML 训练。
- `no_popular_times` 不是低繁忙负样本，只能作为无标签推理目标或覆盖状态。
- hourly rows 不能随机切分，必须按 `prediction_group_id` 分组切分。
- 本轮已新增 `src/build_populartimes_training_data.py`，可从缓存的 SerpAPI Place JSON 展开 Popular Times hourly labels。
- 本轮新增 phase B 输出：
  - `output/populartimes_hourly_labels_phase_b.csv`: 4,356 hourly rows
  - `output/populartimes_hourly_labels_phase_b_audit.csv`: 36 venues, 36 parsed ok, 0 failed

## 1. 已确认的训练标签口径

已确认后续训练以 `161` 个 healthcare `has_popular_times` venues 作为当前 full labeled set。

历史输出中仍存在以下口径来源：

| 来源 | healthcare Popular Times 数量 | 说明 |
|---|---:|---|
| `ML_SOP.md` | 161 | 当前 SOP 覆盖表 |
| `healthcare_prediction_group_members.csv` | 125 | 旧 prediction group member view，需重新生成或标记为旧口径 |
| `venue_label_status_coverage_view.csv` / `venue_ml_candidates.csv` | 161 | 当前 coverage / candidates view |
| phase B parse output | 36 | 本轮新增 venues，不是全量 |

执行决策：

- 以 `161` 作为当前全量 labeled healthcare venue 口径。
- 把 `36` 明确为 phase B 新增可解析 Popular Times venues。
- 后续训练表应合并旧的 125 与新增 36，而不是只训练 phase B 的 36。
- 重新生成或更新旧的 prediction group member view，避免 125 旧口径继续污染训练入口。

验收标准：

- 一个 canonical coverage summary 文件能同时说明：
  - healthcare total = 1086
  - healthcare has_popular_times = 161
  - phase B newly added has_popular_times = 36
  - full expected hourly label rows = 161 x 7 x observed hours, 不强行假设全部 24 小时

## 2. P0: 建立全量 hourly label pipeline

目标：

- 将 phase B 的 Popular Times 展开逻辑推广为全量 pipeline。
- 输出 161 个 labeled healthcare venues 对应的 hourly weak labels。

输入：

- `Data+ML/test/6.22-6.27/output/venue_ml_candidates.csv`
- `Data+ML/test/6.22-6.27/output/phase_b_place_results.csv`
- `Data+ML/test/6.22-6.27/output/serpapi_raw_responses/`
- 现有 `Data+ML/test/6.28-7.3/src/build_populartimes_training_data.py`

输出：

- `output/populartimes_hourly_labels_full.csv`
- `output/populartimes_hourly_labels_full_audit.csv`

验收标准：

- 覆盖 161 个 healthcare venues，或明确列出缺失 JSON / 无法解析 venue。
- 每行包含 `prediction_group_id`，不只包含 `venue_id` / `serpapi_place_id`。
- `busyness_score` 范围必须在 0-100。
- audit 中保留 `parse_status`、`parse_error`、`source_json_file`、`days_available`、`hour_rows`。

## 3. P0: 组装第一版训练表

目标：

- 形成可直接进入 baseline / sklearn 模型的 tabular training frame。

训练粒度：

```text
prediction_group_id + day_of_week + hour
```

必须包含：

- label: `busyness_score`
- group key: `prediction_group_id`
- venue / place features: `review_count`, `rating`, `mapped_venue_count`
- geography: `district`, `latitude`, `longitude`
- time features: `day_of_week`, `hour`, `is_weekend`
- nullable placeholder: `is_business_hours`

输出：

- `output/ml_training_frame_v1.csv`
- `output/ml_training_frame_v1_audit.csv`

验收标准：

- 同一 `prediction_group_id` 不会在 train / validation / test 中交叉泄漏。
- 明确记录哪些字段是真实可用，哪些字段是 placeholder / null。
- `is_business_hours` 缺失时为 unknown/null，不默认当作 closed。

## 4. P0: 跑最低基线与泄漏检查

模型顺序：

1. seasonal mean baseline
2. Ridge / ElasticNet
3. RandomForestRegressor
4. GradientBoostingRegressor

第一轮最低基线：

```text
healthcare_subtype + district + day_of_week + hour mean busyness_score
```

如果 `healthcare_subtype` 暂缺，先用：

```text
district + day_of_week + hour mean busyness_score
```

输出：

- `output/model_metrics_v1.csv`
- `output/group_split_v1.csv`
- `output/predictions_validation_v1.csv`

验收标准：

- split 按 `prediction_group_id`，比例建议 70/15/15。
- 报告 MAE、RMSE、R2、busy-level accuracy、macro F1、busy recall。
- 同时输出 train / validation / test 的 group 数、venue 数、hourly row 数。

## 5. P0: 生成前端 12h 曲线样例

目标：

- 给前端一个可消费的 busyness prediction curve 示例。

输出：

- `output/frontend_12h_curve_sample.json`

字段：

```text
prediction_group_id
venue_ids
forecast_generated_at
model_version
points[].forecast_for
points[].predicted_score
points[].predicted_level
points[].prediction_confidence
```

验收标准：

- 12 个 future hours 独立构造 feature row。
- 文档中明确该曲线是典型周模式估计，不是实时历史序列外推。

## 6. P1: 空间特征接入

优先级：

1. `nearest_subway_distance_m` from MTA GTFS
2. `nearest_citibike_distance_m` from Citi Bike station data
3. `poi_density_300m` from OSM / local POI cache

输出：

- `output/spatial_features_v1.csv`
- `output/spatial_features_v1_audit.csv`

验收标准：

- 距离单位统一为 meters。
- venue 坐标缺失、外部点位缺失、计算失败必须进入 audit。
- 不在训练报告中声称空间特征有效，除非 ablation 显示增益。

## 7. P2: Capacity / Hospital Level enrichment

目标：

- 接入 NYS / CMS 数据，作为 optional enrichment。

数据源：

- NYS `2dbc-sqe7`: staffed bed capacity / ICU capacity
- NYS `vn5v-hh5r`: facility description / short type
- NYS `2g9y-7kqm`: certification / bed type / measure value
- CMS `xubh-q36u`: hospital type / ownership / emergency services / rating

输出：

- `output/healthcare_capacity_level_features_v1.csv`
- `output/healthcare_external_match_audit_v1.csv`

验收标准：

- 匹配不能只靠 name，必须至少使用 `normalized_name + distance <= 200m`，必要时加 ZIP / county / address tokens。
- `capacity = NULL` 合法，特别是 pharmacy / dentist / clinic。
- 必须保留 `capacity_source`、`capacity_as_of_date`、`hospital_level_source`。
- 必须增加 `has_capacity_feature`、`has_hospital_level_feature`，不要静默丢弃缺失。

## 8. 推荐执行顺序

1. 统一 labeled venue 口径：确认 161 是全量、36 是 phase B 增量。
2. 更新 SOP / notebook / presentation 中的覆盖数字。
3. 改造 `build_populartimes_training_data.py`，输出 full labels 和 full audit。
4. 增加 `prediction_group_id` 到 hourly label rows。
5. 构建 `ml_training_frame_v1.csv`。
6. 实现 group-aware split 并保存 split 文件。
7. 跑 seasonal mean baseline。
8. 跑 Ridge / ElasticNet / RandomForest / GradientBoosting。
9. 输出 metrics、validation predictions 和 frontend 12h sample JSON。
10. 再接入 P1 空间特征并做 ablation。
11. 最后接入 P2 capacity / hospital_level，并单独做匹配审计。

## 9. 已确认决策

决策：

```text
后续以 161 个 healthcare has_popular_times venues 作为当前全量训练标签口径。
```

执行含义：

```text
161 是当前 full labeled healthcare set；36 是 phase B 新增子集。下一步训练必须先合并到 full label pipeline，不能只用 36 训练。
```
