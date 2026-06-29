# ML Notebook 搭建日志

> 日期：2026-06-28 ~ 2026-06-29
> 位置：`Data+ML/test/6.28-7.3/`

---

## 一、已完成

### 1.1 基础框架搭建（6.28）

- [x] 重建 `ML.ipynb` 为有效 Jupyter notebook。
- [x] 根据 `docs/memory/ML_SOP.md` 搭建中文 ML 框架。
- [x] 写入 9 个新增特征登记表：
  - `review_count`
  - `traffic_score`
  - `nearest_subway_distance_m`
  - `nearest_citibike_distance_m`
  - `poi_density_300m`
  - `capacity`
  - `hospital_level`
  - `is_business_hours`
  - `mapped_venue_count`
- [x] 增加标签覆盖读取模块。
- [x] 增加 Popular Times target 展开模块骨架。
- [x] 增加 SerpAPI feature 模块骨架。
- [x] 增加 MTA / Citi Bike / OSM 空间特征模块占位。
- [x] 增加 capacity / hospital_level 数据源说明。
- [x] 增加 group-aware split 骨架。
- [x] 增加 seasonal mean baseline 骨架。
- [x] 增加 12h prediction curve 输出接口骨架。
- [x] 新增 `src/build_populartimes_training_data.py`，将缓存的 SerpAPI Place JSON 展开为小时级 Popular Times 训练标签。
- [x] 完成本轮新增 36 个 `has_popular_times` venue 的 JSON 解析审计：
  - 输入 venue：36
  - 成功解析：36
  - 解析失败：0
  - 小时级 label 行数：4,356
  - `busyness_score` 范围：0-100
  - 输出：`output/populartimes_hourly_labels_phase_b.csv`
  - 审计：`output/populartimes_hourly_labels_phase_b_audit.csv`

### 1.2 城市活动空间 proxy 特征接入（6.29）

- [x] 接入 Citi Bike / MTA / Traffic 城市活动空间 proxy 特征 (v1)。

#### 数据源

```text
Data+ML/test/6.15-6.20/output/venue_coverage_detail.csv
```

该文件包含 4838 个 venue 的 Citi Bike / MTA / Traffic 空间覆盖详情，字段包括：

```text
venue_id, venue_type, district, latitude, longitude,
citibike_nearest_source_id, citibike_nearest_distance_m, citibike_covered_100m..500m,
mta_nearest_source_id, mta_nearest_distance_m, mta_covered_100m..500m,
traffic_nearest_source_id, traffic_nearest_distance_m, traffic_covered_100m..500m
```

#### 新增字段（7 个 v1 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `citibike_nearest_distance_m` | float | 最近 Citi Bike 站点距离（米） |
| `mta_nearest_distance_m` | float | 最近 MTA 站点距离（米） |
| `traffic_nearest_distance_m` | float | 最近 NYC Traffic segment 距离（米） |
| `citibike_covered_200m` | bool | 200m 内有 Citi Bike 站点 |
| `mta_covered_200m` | bool | 200m 内有 MTA 站点 |
| `traffic_covered_500m` | bool | 500m 内有 Traffic segment |
| `urban_activity_spatial_score` | float | 综合空间活动 proxy 分数（0-100） |

#### 综合分数公式

```python
score = max(0, 100 * (1 - distance_m / 500))

urban_activity_spatial_score =
    0.4 * citibike_score +
    0.4 * mta_score +
    0.2 * traffic_score
```

权重说明：
- Citi Bike 和 MTA 各 0.4：覆盖密度高，城市活动相关性强。
- Traffic 0.2：NYC Traffic segment 稀疏，更多是辅助 proxy。
- 缺失距离记为 0 分（fill 500m → score = 0）。

#### v2 占位字段（暂未实现）

| 字段 | 说明 |
|---|---|
| `mta_hourly_ridership` | 小时级 MTA ridership 指数 |
| `citibike_station_activity` | 小时级 Citi Bike 站点活动指数 |
| `nyc_traffic_hourly_volume` | 小时级 NYC Traffic 流量指数 |
| `urban_activity_proxy_score` | v2 综合小时级活动 proxy 分数 |

---

## 二、代码改动明细

### 2.1 `src/ml_feature_pipeline.py`

#### 新增函数

**`load_venue_coverage_features(paths)`**
- 读取 `6.15-6.20/output/venue_coverage_detail.csv`
- 只选取 ML 需要的 7 个字段（3 距离 + 3 覆盖 + venue_id）
- 返回 `(coverage_df, audit_df)`

**`build_urban_activity_spatial_features(paths, healthcare)`**
- 调用 `load_venue_coverage_features()` 获取覆盖数据
- 按 `venue_id` left join 到 healthcare venue 列表
- 对三个距离字段计算 `score = max(0, 100*(1-d/500))`
- 计算加权 `urban_activity_spatial_score`
- 输出 `urban_activity_spatial_features_v1.csv`（1086 行）
- 输出 `urban_activity_spatial_features_v1_audit.csv`（审计行）
- 返回 `(features_df, audit_df)`

#### 修改函数

**`build_feature_registry()`**
- 新增 7 个 v1 特征登记（group = `UrbanActivity_Spatial`）
- 新增 4 个 v2 占位登记（group = `UrbanActivity_Hourly`，status = `v2_not_implemented`）

**`build_feature_coverage()`**
- 新增 7 个字段到覆盖率统计列表

**`build_io_dictionary()`**
- 新增 11 个字段条目（7 v1 + 4 v2）

**`build_training_frame()`**
- 新增参数 `urban_activity_features: pd.DataFrame | None = None`
- 在 capacity_features merge 之后、split 赋值之前，merge urban_activity_features

**`run_pipeline()`**
- 调用 `build_urban_activity_spatial_features(paths, healthcare)`
- 将 urban_activity_features 传入 `build_training_frame()`
- outputs 字典新增 `urban_activity_features` 和 `urban_activity_audit`
- 写入循环新增两个 CSV 输出

### 2.2 `src/ml_modeling.py`

#### `build_model_feature_blocks()`

新增 block：

```python
"urban_activity_spatial": baseline + [
    "citibike_nearest_distance_m",
    "mta_nearest_distance_m",
    "traffic_nearest_distance_m",
    "citibike_covered_200m",
    "mta_covered_200m",
    "traffic_covered_500m",
    "urban_activity_spatial_score",
]
```

移除 block：

```python
"weather": baseline + [...]   # 数据源缺失
"traffic": baseline + [...]   # traffic_score 不再作为特征
```

修改 `full_available`：

```python
"full_available": baseline + [
    # 原有 spatial + capacity 特征
    "nearest_subway_distance_m", "nearest_citibike_distance_m", "poi_density_300m",
    "capacity", "icu_capacity", "facility_level", "facility_short_type",
    "cms_hospital_type", "cms_rating",
    # 新增 urban activity spatial 特征
    "citibike_nearest_distance_m", "mta_nearest_distance_m", "traffic_nearest_distance_m",
    "citibike_covered_200m", "mta_covered_200m", "traffic_covered_500m",
    "urban_activity_spatial_score",
]
```

#### `build_ablation_summary()`

消融组从：

```python
["baseline", "weather", "traffic", "mobility", "poi_density", "capacity", "full_available"]
```

改为：

```python
["baseline", "mobility", "poi_density", "capacity", "urban_activity_spatial", "full_available"]
```

### 2.3 `ML.ipynb`

新增 cell：

| Section | 类型 | 内容 |
|---|---|---|
| §5.1 | markdown | Urban Activity Spatial Features 概述 + 公式 + v1/v2 说明 + 中英文 disclaimer |
| §5.1 | code | 读取 urban_activity CSV、显示 audit、打印 non-null 覆盖率和 score 统计 |
| §5.1 | code | 三个距离字段分布直方图（1×3 subplots） |
| §5.1 | code | score 分布直方图 + 覆盖率柱状图（1×2 subplots） |
| §9.1 | markdown | Ablation 对比说明 |
| §9.1 | code | baseline / mobility / urban_activity_spatial / full_available 四组消融对比表 + MAE/F1 柱状图 |

### 2.4 `ML_SOP.md`

- §6 动态特征：`traffic_score` → `urban_activity_spatial_score` (v1) + `urban_activity_proxy_score` (v2)
- §9 训练数据结构：移除 `weather_*` / `traffic_score`，新增 7 个 urban activity 字段
- §12 特征组消融：更新消融组列表，新增说明段落

---

## 三、验证结果

### 3.1 管线输出

```bash
python Data+ML/test/6.28-7.3/src/ml_feature_pipeline.py
```

| 输出文件 | 状态 | 行数 |
|---|---|---|
| `urban_activity_spatial_features_v1.csv` | ✅ | 1086 |
| `urban_activity_spatial_features_v1_audit.csv` | ✅ | 1 |
| `ml_training_frame_v1.csv` | ✅ | 22,645 |
| `model_metrics_v1.csv` | ✅ | 9 |
| `prediction_curve_v1.csv` | ✅ | 36 (3 models × 12h) |
| `ablation_summary_v1.csv` | ✅ | 6 |

### 3.2 字段覆盖

```
Venue-level non-null rate (among rows with venue_id):
citibike_nearest_distance_m     1.0
mta_nearest_distance_m          1.0
traffic_nearest_distance_m      1.0
citibike_covered_200m           1.0
mta_covered_200m                1.0
traffic_covered_500m            1.0
urban_activity_spatial_score    1.0

Row-level non-null rate (all 22645 rows):
citibike_nearest_distance_m     0.95
mta_nearest_distance_m          0.95
traffic_nearest_distance_m      0.95
citibike_covered_200m           0.95
mta_covered_200m                1.0
traffic_covered_500m            0.95
urban_activity_spatial_score    0.95
```

说明：row-level 95% 是因为 1134 行（5%）无 `venue_id`（popular_times 未映射到 venue），与所有 venue-dependent 特征一致。venue-level 覆盖率 100%。

### 3.3 urban_activity_spatial_score 分布

```
count    21511
mean      55.69
std       14.03
min       22.68
25%       46.29
50%       57.69
75%       65.70
max       86.71
```

### 3.4 消融结果（Ridge, test split）

```
            block_name  status  feature_count     mae    rmse
              baseline      ok              9  25.448  29.401
              mobility      ok             11  25.499  29.477
           poi_density      ok             10  25.363  29.340
              capacity      ok             18  25.118  29.336
urban_activity_spatial      ok             16  25.808  29.951
        full_available      ok             25  25.285  29.653
```

### 3.5 已有特征保留确认

```text
nearest_subway_distance_m     ✅ 保留
nearest_citibike_distance_m   ✅ 保留
poi_density_300m              ✅ 保留
```

新旧 Citi Bike 距离字段说明：
- `nearest_citibike_distance_m`：从 GBFS station_information.json 实时计算，保留旧名兼容。
- `citibike_nearest_distance_m`：从 venue_coverage_detail.csv 读取，使用 coverage 原始命名。
- 两者来源不同，notebook 展示时会说明。

---

## 四、当前约束

- notebook 不直接触发外部 API。
- SerpAPI / Google Popular Times 仅作为 weak label，不作为真实客流 ground truth。
- restroom 样本不足，不进入当前 ML 训练。
- hourly rows 不能随机切分，必须按 `prediction_group_id` 分组切分。
- `traffic_score` 不再作为 SerpAPI 字段或模型特征；SerpAPI 的 `busyness_score` 是 target，不是交通特征。
- Citi Bike / MTA / Traffic 是城市活动 proxy，不是实时交通观测。

---

## 五、后续任务

- [x] 接入 Citi Bike / MTA / Traffic 空间活动 proxy 特征 (v1)。
- [ ] 接入 MTA Hourly Ridership API (v2)。
- [ ] 接入 Citi Bike historical API (v2)。
- [ ] 接入 NYC Traffic API (v2)。
- [ ] 接入实时天气 (v2)。
- [ ] 训练 seasonal baseline / Ridge / RandomForest / GradientBoosting。
- [ ] 生成前端 12h 预测折线图样例数据。
