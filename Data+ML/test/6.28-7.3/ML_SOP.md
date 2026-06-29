# Healthcare 繁忙度 ML SOP

> 更新时间：2026-06-28  
> 当前目标：使用 SerpAPI / Google Popular Times 作为 weak label，预测 healthcare venue 的相对繁忙指数。

---

## 1. 模型目标定义

当前模型不声明预测真实客流 ground truth，而是预测：

```text
Google Popular Times proxy busyness
```

也就是使用 SerpAPI / Google Popular Times 作为弱监督标签，学习不同 healthcare venue 在不同星期和小时的相对繁忙模式。

推荐表述：

```text
The model estimates relative venue busyness using Google Popular Times as a proxy label.
```

避免表述：

```text
The model predicts actual foot traffic.
```

输出字段：

```text
predicted_score: 0-100
predicted_level: quiet | moderate | busy | no_data
prediction_confidence
model_version
```

有效预测等级规则：

```text
< 30   -> quiet
30-70  -> moderate
> 70   -> busy
```

产品显示默认：

```text
no_data -> no ML prediction available
```

`no_data` 是产品 / API fallback level，不是 healthcare supervised training 的正负标签。它用于 healthcare 以外的 venue，或当前没有可用预测结果的 venue。Google Popular Times 中的 `busyness_score = 0` 仍是有效弱标签，应按分数规则归为 `quiet`，不要误当成 `no_data`。

---

## 2. 适用范围

监督式繁忙度预测仅用于：

```text
venue_type = healthcare
```

不进入当前 ML 训练：

```text
restroom
emergencyasset / AED
```

原因：

- `restroom` 只有 8 条 `popular_times`，样本量不足。
- restroom 多数位于公园或公共设施内部，交通和天气特征与 restroom 使用量的相关性弱。
- `emergencyasset / AED` 是静态应急设施，使用行为是罕见事件，不适合繁忙度预测。

推荐产品策略：

```text
healthcare -> ML busyness prediction
restroom   -> rule fallback / availability display, default busyness level = no_data
AED        -> static presence / location confidence, default busyness level = no_data
```

---

## 3. 当前标签覆盖

基于：

```text
Data+ML/test/6.22-6.27/output/venue_label_status_coverage_view.csv
```

当前覆盖口径：

| venue_type | DB total | SerpAPI matched | has_popular_times | no_popular_times | search_not_matched |
|---|---:|---:|---:|---:|---:|
| healthcare | 1086 | 743 | 161 | 582 | 343 |
| restroom | 473 | 37 | 8 | 29 | 436 |

解释：

```text
SerpAPI matched = has_popular_times + no_popular_times
```

healthcare 当前可作为 supervised target 的 venue 数：

```text
161
```

说明：

```text
161 是当前 full labeled healthcare set；phase B 新增 36 个 has_popular_times venue。
```

注意：

```text
no_popular_times != not busy
```

没有 Popular Times 的 venue 是推理目标，不是负样本。

---

## 4. Popular Times 数据粒度

本地 raw JSON 检查结果：

```text
带 popular_times.graph_results 的 JSON 文件: 84
总 hourly busyness points: 10,576
常见跨度: 7 days x 18 hours = 126 points
多数覆盖时间: 06:00-23:00
少数覆盖时间: 00:00-23:00
```

训练数据展开粒度：

```text
prediction_group_id / venue_id
day_of_week
hour
busyness_score
```

注意：

- Popular Times 是典型周模式，不是真实日期历史观测。
- 同一 venue 的 hourly rows 高度相关，不能当作完全独立样本。
- 训练 / 验证 / 测试切分必须按 `prediction_group_id` 或 `venue_id` 分组。

---

## 5. Venue 与 Place 映射策略

当前存在多对一关系：

```text
多个 DB venue -> 同一个 serpapi_place_id
```

因此推荐引入：

```text
prediction_group_id = serpapi_place_id
```

预测结果在 group 层共享：

```text
prediction_group_id
busy_score
busy_level
has_popular_times
model_version
```

venue 层保留：

```text
venue_id
serpapi_place_id
prediction_group_id
match_distance_m
name_similarity
mapped_venue_count
```

前端建议：

- 地图 marker 按 `prediction_group_id` 合并。
- 详情页保留多个 DB venue 名称。
- 搜索仍支持任意 DB venue name。
- 繁忙预测结果由同一 group 下的 venue 共享。

---

## 6. 已有特征

### 静态特征

```text
venue_id
venue_type
healthcare_subtype
district
latitude
longitude
rating
review_count
capacity
hospital_level
```

### 动态 / 上下文特征

```text
urban_activity_spatial_score   # v1: 空间活动 proxy (Citi Bike / MTA / Traffic 距离)
urban_activity_proxy_score     # v2: 小时级活动指数 (暂未实现)
day_of_week
hour
is_weekend
```

---

## 7. 需要补充的 9 个关键特征

| 实现方式 | 特征 | 数据源 | 说明 |
|---|---|---|---|
| SerpAPI 已有但未入库 | `review_count` | `place_results.reviews` | 反映 venue 活跃度和 Google 关注度 |
| SerpAPI 已有但未入库 | `traffic_score` | `place_results.popular_times.graph_results.busyness_score` | 作为 weak label 或派生繁忙曲线 |
| 外部数据 + 空间计算 | `nearest_subway_distance_m` | MTA GTFS | 最近地铁站距离，表示 transit accessibility |
| 外部数据 + 空间计算 | `nearest_citibike_distance_m` | Citi Bike API | 最近 Citi Bike 站点距离，表示微出行可达性 |
| 外部数据 + 空间计算 | `poi_density_300m` | OSM Overpass | 300m 范围 POI 密度，表示周边活动强度 |
| 新增数据源 | `capacity` | NYC DOH / CMS Hospital Compare | 容量、床位或服务规模 proxy |
| 新增数据源 | `hospital_level` | NYC DOH / CMS Hospital Compare | 医院等级、机构类型、服务级别 |
| 可派生 | `is_business_hours` | `opening_hours` 解析 | 当前小时是否处于营业时间 |
| 可派生 | `mapped_venue_count` | SerpAPI place 映射结果 | 一个 Google place 对应多少 DB venue，表示 group 聚合程度 |

优先级：

```text
P0: review_count, traffic_score, is_business_hours
P1: nearest_subway_distance_m, nearest_citibike_distance_m, poi_density_300m
P2: capacity, hospital_level, mapped_venue_count
```

---

## 8. 特征构建规则

### SerpAPI 特征

从 Place API response 提取：

```text
review_count = place_results.reviews
rating = place_results.rating
popular_times = place_results.popular_times.graph_results
```

`busyness_score` 展开为：

```text
venue_id / prediction_group_id
day_of_week
hour
busyness_score
```

### 空间特征

统一用 venue 坐标计算：

```text
nearest_subway_distance_m
nearest_citibike_distance_m
poi_density_300m
healthcare_density_300m
```

距离计算建议使用 haversine 或投影坐标，输出单位统一为米。

### 营业时间特征

从 `opening_hours` 解析：

```text
is_business_hours
hours_status
```

如果无营业时间：

```text
is_business_hours = unknown
```

不要默认视为关闭。

营业时间不作为复杂模型输入展开。第一版将其作为 serving / post-processing constraint：

```text
outside business hours -> serving_predicted_level = no_data
```

`opening_hour`、`closing_hour`、`hours_open_per_day` 可作为内部解析审计字段，但不进入第一版模型特征列表。

### Capacity / Hospital Level 数据源约束

`capacity` 和 `hospital_level` 作为 optional enrichment，不作为第一版模型的必需字段。

可用数据源：

```text
NYS Health Data - New York State Statewide Hospital Bed Capacity
Dataset ID: 2dbc-sqe7
用途: staffed bed capacity / ICU capacity / occupied / available

NYS Health Data - Health Facility General Information
Dataset ID: vn5v-hh5r
用途: facility description / short type / ownership / location

NYS Health Data - Health Facility Certification Information
Dataset ID: 2g9y-7kqm
用途: certified service / bed type / measure_value

CMS Provider Data - Hospital General Information
Dataset ID: xubh-q36u
用途: hospital_type / ownership / emergency_services / overall_rating
```

实现注意事项：

- NYS 数据主要覆盖 Article 28 / 医院 / 诊疗中心等机构，对 pharmacy、dentist、普通 clinic 可能大量缺失。
- `capacity` 对 pharmacy / dentist 没有明确业务含义，应允许 `NULL`，不要填 `0`。
- `2dbc-sqe7` 的 staffed bed capacity 是按 `as_of_date` 更新的动态容量，不是永久静态容量。
- 必须保留：

```text
capacity_as_of_date
capacity_source
hospital_level_source
```

匹配规则：

```text
normalized_name + distance <= 200m
```

必要时增加：

```text
ZIP / county / address token
```

不要只用名称匹配。

由于 CMS、NYS 和项目 DB 的 ID 体系不同，需要保留外部映射审计字段：

```text
venue_id
nys_fac_id
nys_facility_pfi
cms_facility_id
external_name
match_distance_m
name_similarity
match_confidence
```

第一版建议固定字段定义：

```text
facility_level = NYS description
facility_short_type = NYS fac_desc_short
cms_hospital_type = CMS hospital_type
cms_rating = CMS hospital_overall_rating
```

缺失值处理：

```text
capacity = NULL
hospital_level = NULL
has_capacity_feature = 0/1
has_hospital_level_feature = 0/1
```

缺失本身可能携带信息，因此需要显式 indicator，而不是静默丢弃。

---

## 9. 训练数据结构

训练表粒度：

```text
prediction_group_id + day_of_week + hour
```

推荐字段：

```text
prediction_group_id
venue_id
healthcare_subtype
district
latitude
longitude
review_count
rating
capacity
hospital_level
nearest_subway_distance_m
nearest_citibike_distance_m
poi_density_300m
mapped_venue_count
day_of_week
hour
is_weekend
is_business_hours
urban_activity_spatial_score
citibike_nearest_distance_m
mta_nearest_distance_m
traffic_nearest_distance_m
citibike_covered_200m
mta_covered_200m
traffic_covered_500m
busyness_score
busy_level
```

---

## 10. 模型路线

第一版不使用 LSTM / SARIMA。

原因：

- Popular Times 不是连续历史时间序列。
- 它没有真实日期，也没有连续观测窗口。
- 适合 tabular supervised learning，而不是 autoregressive forecasting。

推荐模型阶段：

1. `seasonal mean baseline`
2. `Ridge / ElasticNet`
3. `RandomForestRegressor`
4. `GradientBoostingRegressor`

前端 12 小时折线图生成方式：

```text
对未来 12 个小时分别构造 feature row
每个 future hour 独立预测 predicted_score
再组合成 12h curve
```

该预测不是基于最近几小时真实观测滚动外推，而是基于：

```text
典型周模式 + venue/context features
```

---

## 11. 切分与评估

必须使用 group-aware split：

```text
group = prediction_group_id
```

禁止随机切分 hourly rows。

原因：

```text
同一 venue 的不同小时高度相关。
如果同一 venue 同时出现在 train/test，会造成数据泄漏。
```

推荐评估：

```text
MAE
RMSE
R2
busy-level accuracy
macro F1
busy recall
```

最低基线：

```text
healthcare_subtype + district + day_of_week + hour 的平均 busyness_score
```

---

## 12. 特征组消融

使用固定 group split 比较：

```text
Baseline: venue static + time
Baseline + mobility
Baseline + POI density
Baseline + capacity
Baseline + urban_activity_spatial (v1)
Baseline + full_available
```

如果某组特征不提升 MAE / RMSE / busy recall，不应声称该特征有效。

保守表述：

```text
Under the current weak-label sample, urban activity spatial proxy features provided limited incremental value beyond venue and temporal features.
```

说明：
- `traffic_score` 不再作为 SerpAPI 字段或模型特征。
- SerpAPI 的 `busyness_score` 是 target，不是交通特征。
- Citi Bike / MTA / Traffic 是城市活动 proxy，通过空间距离和覆盖标记接入。
- v1 使用空间距离；v2 再接小时级活动指数。

避免表述：

```text
Traffic features are useless.
```

---
