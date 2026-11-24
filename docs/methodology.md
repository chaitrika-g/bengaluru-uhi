# Methodology and Limitations

## 1. Study design

| Choice | Value | Why |
|---|---|---|
| Season | 1 March – 31 May | Bengaluru's hottest months, before the southwest monsoon. Also the least cloudy, which matters for optical and thermal satellites. |
| Years | 2022–2026 | The period I have lived in the city. Five comparable summers. |
| Core city | 15 km radius from Vidhana Soudha (12.9716 N, 77.5946 E) | Approximates the BBMP area. The radius is transparent and simple to vary. |
| Rural reference | Ring 22–30 km from the centre; WorldCover vegetation or cropland pixels only | Outside the continuous built-up area. Water and built pixels are excluded. |
| Resolution | 60 m (Landsat), 1 km (MODIS, grid panel) | Landsat thermal is natively 100 m; 60 m keeps NDVI detail without spurious thermal precision. |
| Green cover | NDVI > 0.4 | A common threshold for dense vegetation or canopy. Excludes dry grass and bare ground. |

## 2. Processing

**Landsat 8/9 (Collection 2, Level-2)**

1. Scenes with < 30 % cloud are selected (10, 12, 18, 17 and 19 scenes for 2022–2026).
2. Pixel mask from QA_PIXEL: fill, dilated cloud, cirrus, cloud and cloud shadow are rejected.
3. Scaling to physical units, following USGS:
   - `LST(°C) = ST_B10 × 0.00341802 + 149.0 − 273.15`
   - `SR = DN × 0.0000275 − 0.2`
   - `NDVI = (NIR − Red) / (NIR + Red)`
4. Per-pixel **median** across the season. This is robust to residual cloud edges and haze.

**MODIS (MOD11A2 + MYD11A2, v6.1)**

1. Mean of all 8-day composites in March–May from both satellites.
2. Urban pixels: within 15 km and > 50 % built-up. Rural pixels: 22–30 km ring and < 10 % built-up.

## 3. Metrics

- **Surface Urban Heat Island (SUHI) intensity** = mean LST(urban) − mean LST(rural).
- **Green cooling** = mean LST(non-green pixels) − mean LST(green pixels), within the core city.
- **UTFVI** (Urban Thermal Field Variance Index) = (Ts − T̄)/Ts in Kelvin. Values above 0.02 mark "strongest" heat-stress zones. This is reported in `outputs/yearly_metrics.csv`.

## 4. Statistical models (src/analysis.py)

**(a) Two-way fixed effects.** The panel is 624 cells of ~1 km × 5 years, balanced, with cells ≥ 90 % inside the core and cloud-free in every year.

```
LST_it = α_i + γ_t + β·Green_it + ε_it      (SE clustered by cell)
```

**(b) Long difference.** Changes are taken from the 2022–23 average to the 2025–26 average:

```
ΔLSTrel_i = a + b·ΔGreen_i + u_i            (HC1 robust SE)
```

LSTrel is each cell's LST minus that year's city mean. Averaging two years at each end reduces the effect of single-year rainfall shocks.

**(c) Robustness.** Model (a) is re-estimated on cells with < 10 % cropland and on cells with > 50 % built-up.

## 5. The daytime "cool island" result

By day, Bengaluru's built core was 1.0–3.8 °C *cooler* than the rural ring in every year (Landsat). MODIS shows the same direction, at −0.4 to −2.0 °C. This is not an error. In semi-arid South Asia the pre-monsoon countryside is largely dry, bare or fallow farmland, which heats up faster than the city with its trees, lakes and shading. The heat residents experience comes from two other things:

1. **Nights:** the city is 2.1–2.5 °C warmer than the countryside at night, every year. Concrete and asphalt release heat that was stored during the day.
2. **Rising absolute temperatures inside the city**, driven partly by the loss of green cover documented here.

## 6. Limitations

1. **LST is not air temperature.** Validating against IMD station air temperature (Bengaluru City and HAL Airport) is the obvious next step.
2. **NDVI measures greenness, not trees.** Watered lawns count as green; a deciduous tree in leaf-drop does not. A canopy product, or Sentinel-2 at 10 m with a tree classifier, would sharpen this.
3. **Seasonal and drought confounding.** The 2024 dip in green cover is mostly drought, not felling. Year fixed effects handle the city-wide part of this. The remaining risk is that *some* neighbourhoods are more drought-sensitive than others. The cropland-excluded check suggests this risk is small.
4. **Composite timing.** Each year's median mixes different acquisition dates. Year fixed effects and relative-to-city-mean metrics neutralise this for the spatial models, but not for the raw yearly means.
5. **MODIS orbit drift** since 2022 shifts overpass times. Treat absolute night LST trends with caution; urban-minus-rural differences are more robust.
6. **Fixed land-cover mask.** WorldCover 2021 is used for zoning, so new construction after 2021 is not reflected in the urban/rural masks.
7. **Identification.** Two-way fixed effects rule out time-invariant and city-wide confounders, but not time-varying local ones (for example, construction both clearing trees and adding dark surfaces). β should be read as the heat associated with green loss *as it actually happened in Bengaluru*, development included, not the pure physical effect of a tree.

## 7. Part B: ward-level panel

| Choice | Value | Why |
|---|---|---|
| Unit | 225 BBMP wards, 2023 delimitation (KML from OpenCity) | Administrative unit for policy and census data |
| Seasons | Dry winter (January–February) and summer (March–May) | Landsat is largely clouded out from June to December, and missing observations would track the weather |
| LST | Landsat 8/9 ST_B10, 60 m, seasonal median | Same processing as Part A |
| NDVI and green cover | Sentinel-2 L2A B04/B08 at 20 m; SCL classes 4/5/6 kept; −1000 DN offset removed for processing baseline ≥ 04.00 | Sharper than Landsat; captures street trees and small parks |
| Zonal statistic | Mean of pixels whose centre falls inside the ward polygon | The smallest ward (0.3 km²) still holds about 80 Landsat pixels |
| Inclusion | ≥ 60 % valid pixels for both LST and NDVI | All 2,250 ward-seasons qualified |
| Night LST | MODIS 1 km, bilinear to 250 m, summer only | **Approximate:** many wards are smaller than one MODIS pixel |

**Ingestion checks (`wards.py`):**
- 225 features with unique ids and no empty geometries.
- 36 self-intersecting polygons repaired with `make_valid`.
- Areas computed in EPSG:32643 match the file's `ward_area` field to within 0.01 %.

**Panel checks (`panel.py`, stored in the `validation_log` table):**
- Row count equals wards × years × seasons.
- Primary key is unique.
- LST, NDVI and green-cover values fall within physical ranges.
- Coverage thresholds are met.
- NDVI and LST correlate negatively (a sanity check).

**Models (`ward_models.py`):**
- Two-way fixed effects (ward and year × season); standard errors clustered by ward.
- Season-specific models (ward and year fixed effects).
- A pooled comparison model without ward fixed effects.
- A ward-level long difference from 2022–23 to 2025–26.
- Descriptive Spearman correlations with population density and SC/ST share.

**PM2.5 (`air_quality.py`):**
- IDW with power 2, from station seasonal means (≥ 20 valid days per station-season) to ward representative points.
- Leave-one-out RMSE and distance to the nearest station are stored for each estimate.
- PM2.5 is used as an outcome and a sensitivity check, never as a control in the headline model.
- **Inference for A1:** interpolated values are spatially correlated (all wards near a station share its shocks), so ward-clustered standard errors are over-confident. A1 is therefore judged by a 200-run permutation test (station readings shuffled within each period), alongside a fixed-station-set model (A2) and a near-station model (A3, within 3 km). On synthetic random data, clustered p was < 0.001 while the permutation p was 0.33.

**Additional limitations:**
- Ward population and SC/ST counts come from the delimitation file and are Census-2011-based. Treat equity results as indicative.
- Bengaluru's governance changed in 2025 with the Greater Bengaluru Authority. These boundaries are the 225-ward BBMP delimitation and may not match current corporation boundaries.
- Seasonal medians from Sentinel-2 at 20 m and Landsat at 60 m are not directly comparable to the Part A NDVI. Compare effect *directions* across parts, not magnitudes.
