# ETL Dedup Rules & Confidence Levels

来源：`Data+ML/test/6.2-6.5_DB/README.md` §5

## Two-Phase ETL

```
Phase 1: Dedup Preprocessing (Cell 12)
    ├─ dedup_restrooms()    → restrooms_deduped
    ├─ dedup_parks()        → parks_deduped
    ├─ dedup_aed()          → aed_deduped
    ├─ dedup_healthcare()   → nys_deduped, osm_deduped
    └─ dedup_ramps()        → ramps_deduped
    ▼
Phase 2: Data Import (Cells 16, 18, 20, 22, 40, 42)
    ├─ etl_restrooms()      → venues + restroom_profiles + venue_source_links
    ├─ etl_aed()            → venues + emergency_assets + venue_source_links
    ├─ etl_healthcare()     → venues + healthcare_profiles + venue_source_links
    ├─ etl_ramps()          → pedestrian_ramps
    ├─ etl_weather()        → external_context_cache
    └─ etl_venue_language() → venue_language
```

## Dedup Rules

| Function | Dedup Key | Filter | Output |
|----------|-----------|--------|--------|
| `dedup_restrooms()` | `name.lower()` | Manhattan GPS | `restrooms_deduped` |
| `dedup_parks()` | `name.lower()` | Manhattan Borough | `parks_deduped` |
| `dedup_aed()` | `ename|address|floor` | Manhattan Borough | `aed_deduped` |
| `dedup_healthcare()` | GPS <30m (NYS priority) | Manhattan | `nys_deduped, osm_deduped` |
| `dedup_ramps()` | `ramp_id` | Borough=1 | `ramps_deduped` |

### Dedup 策略说明

- **Restrooms**: 源内按名称去重，不跨源合并（Parks Toilets 无 GPS，无法跨源匹配）
- **AED**: `Entity_Name + Address + Floor` 保留安装级别粒度，仅移除完全相同的行（~114 条）
- **Healthcare**: NYS 优先的跨源 GPS 去重——OSM 记录在 30m 内匹配到 NYS 则被移除
- **Ramps**: 按 `ramp_id` 去重，Manhattan Borough code = `'1'`

## Data Source Confidence Levels

| Source | Confidence | Reason |
|--------|------------|--------|
| NYS Health | 0.9 | Official government data |
| AED Inventory | 0.8 | Verified inventory |
| NYC Restrooms | 0.6 | City data, may be outdated |
| OSM Healthcare | 0.5 | Community-sourced |
| Parks Toilets | 0.3 | No coordinates available |
| LASS Ratings | 0.4 | Government evaluation data |

## ETL Import Functions

| Function | Source | Target Tables | Import Method |
|----------|--------|---------------|---------------|
| `etl_restrooms()` | NYC Restrooms + Parks | venues, restroom_profiles, venue_source_links | INSERT ON DUPLICATE |
| `etl_healthcare()` | OSM + NYS Health | venues, healthcare_profiles, venue_source_links | INSERT ON DUPLICATE |
| `etl_aed()` | AED Inventory | venues, emergency_assets, venue_source_links | INSERT ON DUPLICATE |
| `etl_ramps()` | Pedestrian Ramps | pedestrian_ramps | INSERT ON DUPLICATE (batch) |
| `etl_weather()` | NWS API | external_context_cache | INSERT ON DUPLICATE |
| `etl_venue_language()` | LASS Ratings | venue_language | INSERT ON DUPLICATE |
