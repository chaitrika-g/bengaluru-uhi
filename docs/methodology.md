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
