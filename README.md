# Concrete Summers: Green Cover Loss and Urban Heat in Bengaluru, 2022–2026

*An open, reproducible satellite study of how losing urban greenery is making Bengaluru hotter, with a view to the economics of who pays for it.*

> **Motivation.** I moved to Bengaluru in 2022. Each summer since then has felt harsher than the last, and the city I arrived in was visibly greener than the one I live in now. As a data engineer I wanted to test that feeling against evidence. Is the city actually getting hotter? Is green cover actually disappearing? And can the two be linked in a way that would stand up to scrutiny?

![Land surface temperature maps](outputs/figures/fig1_lst_maps.png)

## Key findings

All figures refer to the pre-monsoon summer (March–May) in the **core city**, a 15 km radius around Vidhana Soudha that roughly matches the BBMP area.

| # | Finding | Evidence |
|---|---|---|
| 1 | **Daytime surface temperature rose by 2.7 °C**, from 37.1 °C (2022) to 39.8 °C (2026). The peak was 40.5 °C in the 2024 drought year. | Landsat 8/9, 10–19 cloud-free scenes per summer |
| 2 | **Green cover fell from 30.0 % to 23.7 % of the core city**, a loss of 6.2 percentage points (pp). It dropped to 16.9 % in 2024. | NDVI > 0.4 share |
| 3 | **Green areas are about 2.2 °C cooler** than non-green areas in every year, with a range of 2.0–2.5 °C. | Pixel-level comparison |
| 4 | **Each 10 pp of green cover lost raises local surface temperature by about 0.69 °C** (95 % CI 0.60–0.78). | Two-way fixed-effects panel: 624 cells of ~1 km × 5 years |
| 5 | Cells in the quartile that lost the most green (−13.7 pp) warmed **0.82 °C relative to the city**. Cells that gained green cooled by 0.51 °C. | Long-difference, 2022–23 → 2025–26 |
| 6 | **The heat island is a night-time phenomenon.** The city stays **2.1–2.5 °C warmer than the countryside at night**, every year. By day, the city core is actually *cooler* than the dry pre-monsoon farmland around it. | MODIS Terra/Aqua, 8-day, 1 km |
| 7 | **58 % of neighbourhoods lost more than 2 pp of green cover. Only 5 % gained.** Losses are concentrated on the expanding periphery. | Grid change analysis |

**On finding 1.** Five summers are too few to call +2.7 °C a statistically significant *trend*: the linear slope is +0.59 °C/yr with p = 0.20, and weather (especially the 2024 drought) moves single years a lot. That is why the causal claim (finding 4) rests on a panel design that removes city-wide weather. It does not rest on the raw time series.

![Green vs heat](outputs/figures/fig4_green_vs_heat.png)

## Why the design matters (the econometrics)

Comparing green and grey neighbourhoods directly is misleading. Leafy areas such as Cubbon Park or Malleshwaram differ from industrial belts in many ways. So the core estimate uses a **two-way fixed-effects panel**:

```
LST(cell, year) = α(cell) + γ(year) + β · GreenCover(cell, year) + ε
```

- **Cell fixed effects α** absorb everything permanent about a location: elevation, lakes, building density, soil.
- **Year fixed effects γ** absorb everything city-wide in a given year: rainfall, El Niño, the 2024 drought, and the satellite overpass mix.
- **β** is therefore identified only from neighbourhoods whose green cover changed *more or less than the city average*. Standard errors are clustered by cell.

The pooled cross-sectional estimate (−0.47 °C per 10 pp) is *smaller* than the fixed-effects estimate (−0.69). Geography confounds the naive comparison, which is the reason to use fixed effects.

**Robustness.** Peri-urban farmland greens and browns with rainfall, not with development. Restricting the sample to dense urban cells gives the same answer:

| Sample | °C per 10 pp green lost | Cells |
|---|---|---|
| All core cells | +0.69 (SE 0.05) | 624 |
| Cropland < 10 % of cell | +0.65 (SE 0.09) | 454 |
| Built-up > 50 % of cell | +0.71 (SE 0.05) | 461 |

## Data (all free and open, no account needed)

| Dataset | Use | Resolution |
|---|---|---|
| USGS Landsat 8/9 Collection 2 Level-2 | Daytime land surface temperature (LST, band ST_B10) and NDVI | 30 m (thermal 100 m), analysed at 60 m |
| NASA MODIS MOD11A2 / MYD11A2 v6.1 | Day and night LST | 1 km, 8-day |
| ESA WorldCover 2021 | Fixed land-cover mask (built-up, cropland, water) | 10 m |

All data are accessed through the [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) STAC API.

## Reproduce it

```bash
pip install -r requirements.txt
bash run_all.sh        # ~5 minutes: download, composite, analyse, plot
```

| File | Role |
|---|---|
| `src/config.py` | Every analytical choice (study area, season, thresholds) in one place |
| `src/composites.py` | Landsat search, cloud masking, scaling to °C, yearly median composites |
| `src/modis.py` | MODIS day/night LST |
| `src/analysis.py` | Yearly metrics, panel regressions, robustness → `outputs/*.csv`, `results.json` |
| `src/figures.py` | Figures → `outputs/figures/` |

## Limitations (read before citing a number)

See [`docs/methodology.md`](docs/methodology.md) for detail. In short:

- **Surface temperature is not air temperature.** LST measures how hot roofs, roads and canopy are, not the air people breathe. It correlates with the heat people feel, but it is not identical to it.
- **NDVI-based green cover mixes permanent loss with seasonal browning.** Two-year averaging, year fixed effects and the cropland-excluded robustness check address this, but they do not eliminate it.
- **Five years is short.** The *relationship* between green cover and heat is well identified. The city-wide *trend* is not yet statistically significant.
- **MODIS orbital drift.** Terra and Aqua overpass times have drifted since 2022. Urban-minus-rural differences are robust to this; absolute night temperatures are less so.
- **Correlation, not experiment.** Fixed effects remove fixed and city-wide confounders. They do not remove time-varying local ones, such as a construction site that both clears trees and adds heat-absorbing materials.

## Where this goes next

The economic questions this raises are in [`docs/economics_extension.md`](docs/economics_extension.md):

- What does a degree of urban heat cost in lost labour productivity, electricity demand and health?
- Who bears that cost?
- What is the shadow price of a tree in Bengaluru?

---
*Author: [Your name], Senior Data Engineer. Built with Python (xarray, stackstac, statsmodels).*
