# SerpAPI Busyness Coverage - Presentation Notes

## 1. Core Conclusion

We built a SerpAPI-based weak-labeling pipeline to collect Google Popular Times signals for NYC healthcare venues.

For the healthcare venue set:

| Metric | Value |
|---|---:|
| Total healthcare venues | 1,086 |
| SerpAPI matched / validated venues | 743 |
| Venues with Google Popular Times | 161 |
| Venues without Popular Times after validation | 582 |
| Search-not-matched venues | 343 |
| Estimated hourly weak labels | 161 × 7 × 24 = 27,048 |

Final presentation wording:

> Built a SerpAPI-based venue busyness labeling pipeline for 1,086 NYC healthcare venues, identifying 161 venues with Google Popular Times signals and generating approximately 27K hourly proxy busyness labels for ML training.

Chinese version:

> 构建 SerpAPI 场地繁忙度弱标签管线，对 1,086 个 NYC healthcare venue 进行覆盖筛查，最终获取 161 个带 Google Popular Times 信号的场地，生成约 2.7 万条小时级 busyness proxy 训练标签。

## 2. What The Label Means

The ML target is not ground-truth foot traffic.

The target is:

> Google Popular Times proxy busyness

This means the model predicts the typical busyness pattern implied by Google's historical Popular Times signal, not real-time measured occupancy.

Why this is acceptable:

- Google Popular Times provides high-resolution weekly patterns.
- Each labeled venue provides up to 7 days × 24 hours of hourly labels.
- The signal is suitable as a proxy target for demonstration and baseline modeling.
- The limitation is explicit and defensible: it is a weak label, not an official pedestrian-count dataset.

## 3. Feature Timing and Alignment

Google Popular Times is treated as a typical weekly pattern, not as an exact timestamped historical observation.

The supervised learning grain is:

```text
prediction_group_id + day_of_week + hour
```

It is not:

```text
venue + exact_date + exact_timestamp
```

Implications for feature design:

| Feature group | Strict timestamp alignment needed? | Reason |
|---|---|---|
| `review_count`, `rating` | No | Slow-changing venue visibility features |
| `nearest_subway_distance_m` | No | Static spatial accessibility |
| `nearest_citibike_distance_m` | No | Station-location accessibility proxy |
| `poi_density_300m` | No | Static surrounding activity proxy |
| `capacity`, `hospital_level` | No strict alignment | Slow-changing facility scale / type proxy |
| `day_of_week`, `hour` | Yes | These are the core weekly-pattern indexes |
| real-time traffic / weather | Not as real-time causal observations | The label is not real-time measured footfall |

If traffic or weather features are added, they should be framed conservatively as typical contextual proxies, for example:

```text
typical_traffic_by_district_day_hour
typical_weather_by_season_hour
```

Recommended first baseline:

```text
venue static features + spatial features + day_of_week + hour
```

This avoids overstating causal or real-time alignment between Google Popular Times and external context data.

## 4. Busyness Level Semantics

The product-level busyness enum has four display states:

```text
quiet | moderate | busy | no_data
```

For the healthcare ML model, the learned prediction states are:

```text
quiet | moderate | busy
```

`no_data` is not a supervised training class. It is the default display / API fallback when no ML prediction is available, especially for venue types outside the current healthcare ML scope.

Recommended mapping:

| Case | Display level |
|---|---|
| healthcare venue with prediction score `< 30` | `quiet` |
| healthcare venue with prediction score `30-70` | `moderate` |
| healthcare venue with prediction score `> 70` | `busy` |
| restroom / AED / out-of-scope venue | `no_data` |
| healthcare venue with no available prediction | `no_data` |
| healthcare venue outside parsed business hours | `no_data` |

Important distinction:

```text
Google Popular Times busyness_score = 0 is valid quiet signal.
Missing prediction = no_data.
Outside business hours = no_data at serving time, not a model training class.
```

## 5. Coverage Improvement Result

Before the final DB-driven search and Place validation round:

| Status | Count |
|---|---:|
| Healthcare venues with Popular Times | 125 |

After the final round:

| Status | Count |
|---|---:|
| Healthcare venues with Popular Times | 161 |
| Newly added venues with Popular Times | 36 |

Final round execution summary:

| Step | Result |
|---|---:|
| DB-driven Search calls | 250 |
| Search-matched venues | 157 |
| Unique Place IDs | 154 |
| Place API validations | 155 |
| New Popular Times venues | 36 |
| Place validation hit rate | 36 / 155 = 23.2% |

Important correction:

- The pipeline did not prove that every healthcare venue has a Google profile.
- It completed the current SerpAPI coverage workflow.
- Remaining `search_not_matched` venues are venues that could not be matched under the current name + GPS search strategy.

Accurate wording:

> We completed the SerpAPI coverage workflow for 1,086 healthcare venues. Of these, 743 were matched and validated through SerpAPI, and 161 contained usable Google Popular Times signals.

## 6. Why We Stopped API Expansion

The final round produced:

```text
250 Search calls -> 36 new Popular Times venues
= 14.4 new labels per 100 Search calls
```

This falls into the middle decision zone:

| Yield per 100 Search | Decision |
|---|---|
| >= 15 | Continue API expansion |
| 10-14 | Conditional continuation |
| < 10 | Stop |

The result is close to the continuation threshold, but the better next step is to process the newly acquired labels into a training-ready dataset before spending more API quota.

## 7. ML Implication

The final labeled venue count is small at the venue level:

```text
161 labeled venues
```

But the hourly training sample count is usable for a baseline model:

```text
161 venues × 7 days × 24 hours = 27,048 hourly labels
```

Recommended first model:

> Tabular baseline model for typical weekly busyness prediction.

Not recommended as the first model:

- LSTM
- SARIMA
- real-time rolling forecast

Reason:

- The data is not a real-time historical time series.
- It is a typical weekly pattern from Google Popular Times.
- A tabular model is simpler, explainable, and better aligned with the available target.

## 8. Product / Frontend Interpretation

Frontend prediction should be presented as:

> Typical future-hour busyness estimate based on venue and context features.

Not as:

> Real-time live crowd prediction.

Suggested frontend display:

- 12-hour busyness line chart.
- Label the output as "Predicted busyness pattern".
- Use `quiet`, `moderate`, and `busy` for healthcare venues with predictions.
- Use `no_data` as the default fallback for restroom, AED, out-of-scope venues, or healthcare venues without a prediction.

## 9. Method Summary For PPT

Pipeline:

1. Start from cleaned healthcare venue database.
2. Use venue name and GPS location to query SerpAPI Google Maps Search.
3. Match returned Google place candidates using:
   - spatial threshold: 200 meters
   - name similarity threshold: 0.4
4. Deduplicate by `serpapi_place_id`.
5. Query SerpAPI Place API only for matched unique places.
6. Extract Google Popular Times when available.
7. Store label status:
   - `has_popular_times`
   - `no_popular_times`
   - `search_not_matched`

## 10. Limitations

Key limitations to disclose:

- Google Popular Times is a proxy label, not official footfall ground truth.
- Some valid healthcare venues could not be matched due to naming mismatch, missing Google profile, or weak geospatial alignment.
- Venue-level labeled count remains limited at 161.
- Model validation must use group-aware splitting by `serpapi_place_id` / venue group to avoid hourly data leakage.

## 11. Best Resume / Demo Bullet

English:

> Developed a SerpAPI-driven weak-labeling pipeline for NYC healthcare venue busyness prediction, matching and validating 743 of 1,086 venues and extracting Google Popular Times signals for 161 venues, producing approximately 27K hourly proxy labels for ML baseline training.

Chinese:

> 构建 NYC healthcare 场地繁忙度弱标签管线，基于 SerpAPI 完成 1,086 个场地的覆盖筛查，匹配并验证 743 个 Google Maps 场地，最终提取 161 个场地的 Google Popular Times 信号，生成约 2.7 万条小时级 ML 训练标签。

Direct mapping is our baseline. The ML model improves on it by transferring weak labels from Google Popular Times to uncovered venues using venue-level and context features, so two clinics in the same district and hour do not receive the same score by default.