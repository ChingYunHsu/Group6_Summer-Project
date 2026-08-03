# Todolist - Venue Busyness Prediction Optimization

## Core Problem

The heat/crowdedness data of venues themselves cannot be obtained directly:

- Google Popular Times: no public API
- BestTime: single query, paid, no batch training
- Yelp/Google Places: no real-time footfall interface

**Training labels need to be built from public proxy signals.**

---

## Confirmed Available Proxy Data Sources

### 1. MTA Subway Hourly Ridership ⭐ Most Valuable

| Item | Value |
|---|---|
| Dataset ID | `wujg-7c2s` |
| API | `https://data.ny.gov/resource/wujg-7c2s.json` |
| Granularity | station_complex + hour |
| Manhattan Row Count | 36,828,057 |
| Time Range | 2020–2024 (latest 2024-12-31) |
| Key Fields | `station_complex_id`, `station_complex`, `ridership`, `transfers`, `latitude`, `longitude`, `borough`, `transit_timestamp` |
| Cost | Free |

**Value**: The number of entries and exits per station per hour directly reflects the activity intensity of the surrounding area.

### 2. Citi Bike GBFS (existing)

| Item | Value |
|---|---|
| Endpoint | station_information + station_status |
| Granularity | station-level real-time |
| Manhattan Stations | ~2,328 |
| Cost | Free |

**Value**: The frequency of stations being borrowed empty/returned full reflects surrounding activity.

### 3. NYC Traffic (existing)

| Item | Value |
|---|---|
| Dataset ID | `7ym2-wayt` |
| Granularity | segment-level/hourly |
| Manhattan Segments | 28 (sparse) |
| Cost | Free |

**Value**: After aggregating at the district level, it can serve as an auxiliary feature.

---

## Todo Items

### Phase 1: MTA Data Integration (Priority P0)

- [ ] **Integrate MTA Hourly Ridership API**
  - Dataset `wujg-7c2s`, filter Manhattan with `borough='Manhattan'`
  - Aggregate ridership by `station_complex_id` + `transit_timestamp`
  - Output: total hourly ridership per station_complex

- [ ] **MTA Station -> Venue Mapping**
  - Use haversine distance to match venues to the nearest MTA station
  - Reuse the BallTree logic from venue_coverage
  - Mapping table: `venue_id -> nearest_station_complex_id -> distance_m`

- [ ] **Storage Design**
  - New table `mta_hourly_ridership`: `station_complex_id, hour, ridership, transfers`
  - Or query on-demand directly in the ETL without persisting (large data volume: 36M+ rows)

### Phase 2: Multi-source Activity Index (Priority P0)

- [ ] **Build district + hour level activity index**
  ```python
  activity_index = w1 * citibike_norm + w2 * mta_norm + w3 * traffic_norm
  ```
  - Normalize each data source to 0-100 by district + hour
  - Set weights w1/w2/w3 to 1/1/1 initially, adjust later based on correlation

- [ ] **Validate Time Correlation**
  - Compute Pearson/Spearman correlation coefficients grouped by district
  - Align 24h curves, check consistency of peak hours
  - Expected: MTA ridership vs venue busyness r > 0.7

### Phase 3: Model Training (Priority P1)

- [ ] **Training Data Construction**
  - Input features: MTA ridership (hour, district) + Citi Bike activity + Traffic volume + time features (hour, day_of_week, is_holiday)
  - Label: multi-source activity index (activity_index)
  - Training set: 2020-2023, validation set: 2024

- [ ] **Model Selection**
  - Baseline: LightGBM / XGBoost (tabular data)
  - Advanced: LSTM / Prophet (time series forecasting)
  - Output: activity_index forecast for the next 12h

- [ ] **Evaluation Metrics**
  - MAE / RMSE: deviation between predicted and actual activity index
  - Ranking accuracy: whether predicted peak/trough hours are accurate
  - Ablation study: impact of Traffic presence/absence on prediction accuracy

### Phase 4: Production Integration (Priority P2)

- [ ] **Replace existing busyness_scores table**
  - Replace pure Traffic scores with MTA + Citi Bike activity index
  - Maintain district-level granularity

- [ ] **Scheduled Update Pipeline**
  - Pull MTA ridership hourly (incremental query `transit_timestamp > last_update`)
  - Recompute activity index and update busyness_scores

- [ ] **Frontend API Adaptation**
  - `get_venue_busyness` returns the new activity index
  - `get_venue_busyness_forecast` returns the 12h forecast

---

## Data Volume Estimation

| Data Source | Rows per Day | Rows per Month | Storage Requirement |
|--------|---------|---------|---------|
| MTA hourly (Manhattan) | ~250K | ~7.5M | ~1.5GB/month |
| Citi Bike | ~55K | ~1.6M | ~300MB/month |
| Traffic | ~672 | ~20K | ~5MB/month |

MTA has the largest data volume; on-demand querying is recommended instead of full storage.

---

## Risks and Considerations

1. **MTA data ends 2024-12-31**: need to confirm whether 2025 data has been released
2. **payment_method dimension**: metrocard vs omny may have statistical caliber differences, pay attention during aggregation
3. **station_complex duplicate coordinates**: the same complex_id may have multiple rows (different payment_method), deduplicate by complex_id + hour during aggregation
4. **Citi Bike real-time vs historical**: GBFS only provides real-time status, historical data must be obtained separately
