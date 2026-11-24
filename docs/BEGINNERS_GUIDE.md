# Beginner's Guide to This Project

This guide explains **every concept and every file** in the repo, assuming no background in satellites, geography or econometrics. Read it in order: Part 1 covers the ideas, Part 2 the statistics, Parts 3–5 the code, Part 6 is an interview cheat sheet, and Part 7 covers Git, GitHub and the website.

---

## Part 1: The core ideas

### 1.1 The question
Bengaluru feels hotter. Is it? And is losing trees and parks part of the reason? To answer that, we need to **measure temperature and greenery everywhere in the city, every year**. No ground network can do that, but satellites can.

### 1.2 How satellites "see"
A satellite camera measures how much light (energy) comes back from each patch of ground, in several **colours**, including invisible ones.

| Term | Meaning |
|---|---|
| **Pixel** | One square of ground in the image. The satellite records one value per pixel per colour. |
| **Resolution** | The size of a pixel on the ground. "10 m resolution" means each pixel covers 10 m × 10 m. Smaller pixels show more detail. |
| **Band** | One "colour channel". Red, Near-Infrared (NIR) and Thermal are the bands that matter here. |
| **Near-Infrared (NIR)** | Light just beyond red that our eyes can't see. **Healthy plants reflect a lot of it.** |
| **Thermal infrared** | Heat radiation. Everything warm gives it off, so a thermal band measures how hot a surface is. |
| **Reflectance** | The fraction of incoming sunlight a surface bounces back (0 = none, 1 = all). |
| **Scene** | One satellite photo of one area on one date. |
| **Revisit time** | How often a satellite passes over the same place. |
| **Raster** | Data stored as a grid of pixels (an image). Satellite data are rasters. |
| **Vector** | Data stored as shapes (points, lines, polygons). Ward boundaries are vectors. |

### 1.3 NDVI: measuring greenery
**NDVI (Normalized Difference Vegetation Index)** is a single number per pixel that says how green and leafy it is.

```
NDVI = (NIR − Red) / (NIR + Red)
```

**Why it works:** leaves absorb red light (they use it for photosynthesis) but strongly reflect near-infrared. So for vegetation NIR is high and Red is low, which gives a large positive NDVI. Concrete, roads and bare soil reflect the two similarly, which gives an NDVI near 0. Water gives a negative NDVI.

| NDVI | Typical surface |
|---|---|
| below 0 | water |
| 0 – 0.2 | concrete, roads, rooftops, bare soil |
| 0.2 – 0.4 | grass, sparse or dry vegetation |
| **above 0.4** | **dense vegetation and tree canopy** (counted as "green cover" in this project) |

**Green cover %** is the share of pixels in an area with NDVI above 0.4.

### 1.4 LST: measuring heat
**LST (Land Surface Temperature)** is how hot the **ground surface** is (roofs, roads, treetops), measured from the thermal band and given here in °C.

- **It is not air temperature.** On a sunny afternoon a road can be 50 °C while the air is 35 °C. LST is still a good guide to how much heat a place absorbs and gives off.
- **It is a snapshot.** Landsat passes over at about **10:30 am**, so Landsat LST is a mid-morning measurement.

### 1.5 Urban Heat Island (UHI)
An **Urban Heat Island** is when a city is hotter than the countryside around it. Concrete and asphalt soak up heat during the day and release it at night; trees and water cool their surroundings.

- **SUHI (Surface Urban Heat Island) intensity** = LST of urban areas − LST of rural areas.
- **This project's surprise:** by day, Bengaluru's core is *cooler* than the dry farmland around it in summer. At night it is 2–2.5 °C *warmer*. The heat people feel is mostly a night-time effect, plus rising temperatures inside the city.

### 1.6 The satellites and datasets

| Source | What it gives us | Pixel size | Revisit |
|---|---|---|---|
| **Landsat 8 and 9** (NASA/USGS) | Red, NIR, **thermal → LST** | 30 m (thermal natively 100 m) | 16 days each, about 8 days combined |
| **Sentinel-2** (European Space Agency) | Red and NIR → **sharper NDVI** | 10 m | about 5 days |
| **MODIS** (on NASA's Terra and Aqua satellites) | **Day and night LST** | 1 km | daily; we use **8-day averages** |
| **ESA WorldCover 2021** | A land-type map: tree, crop, built-up, water and so on | 10 m | one map |
| **BBMP ward KML** | The 225 ward boundaries, with population | n/a | n/a |
| **OpenAQ / CPCB** (optional) | PM2.5 readings from air-quality monitoring stations | points | daily |

**Collection 2 Level-2** (Landsat) and **L2A** (Sentinel-2) mean the data are already corrected for haze and atmospheric effects, so we get surface reflectance and surface temperature directly.

### 1.7 Clouds: the biggest practical problem
Satellites can't see through clouds, and clouds are cold, so they would look like "cold, non-green" ground. Two defences:

1. **Scene filter:** only use scenes with less than 30 % cloud (less than 20 % for Sentinel-2).
2. **Cloud mask:** each scene comes with a quality layer that flags cloud and shadow pixels. Landsat's is **QA_PIXEL**, a number per pixel whose individual bits mean cloud, shadow and so on. Sentinel-2's is **SCL** (Scene Classification Layer), a class per pixel. Flagged pixels are thrown away.

### 1.8 Composites and the median
For each season we have 10–40 scenes. A **composite** combines them into one clean image. For every pixel we take the **median** (the middle value) of all its cloud-free observations. The median ignores the odd leftover cloud edge or haze better than the average does.

### 1.9 Maps and coordinates
| Term | Meaning |
|---|---|
| **CRS (Coordinate Reference System)** | The "language" for locations on Earth. |
| **EPSG code** | A standard number identifying a CRS. |
| **EPSG:4326 (WGS84)** | Latitude/longitude in degrees, as GPS uses. Good for storing; bad for measuring distance or area, because degrees aren't metres. |
| **EPSG:32643 (UTM zone 43N)** | A flat map projection in **metres**, accurate for Bengaluru's region. Used for areas, distances and pixel grids. |
| **Bounding box (bbox)** | The rectangle `[min longitude, min latitude, max longitude, max latitude]` enclosing the study area. |
| **Reproject** | Convert data from one CRS to another. |
| **Resample** | Change pixel size (for example 10 m → 20 m). *Nearest* takes the closest pixel's value; *bilinear* blends neighbours; *mode* takes the most common value (for categories like land type). |

### 1.10 Where the data come from technically
| Term | Meaning |
|---|---|
| **Microsoft Planetary Computer** | A free, public archive of satellite data. No account needed. |
| **STAC (SpatioTemporal Asset Catalog)** | A standard "search engine" format for satellite data: you ask for "Landsat scenes over this box, these dates, under 30 % cloud" and get a list of **items** (scenes), each with **assets** (band files). |
| **COG (Cloud-Optimized GeoTIFF)** | An image format that lets you download *only the part you need* instead of the whole file. That's why we can process the whole city in minutes. |
| **Signed URL** | A temporary download link. Planetary Computer adds a time-limited token, which is why links expire if a run stalls for hours. |

### 1.11 File formats used
| Format | What it holds |
|---|---|
| **KML** | Shapes plus attributes, XML-based (from Google Earth). Your ward file. |
| **GeoJSON** | The same thing in JSON; the web standard. Used for the interactive map. |
| **GeoParquet / Parquet** | Fast, compressed table format (columns), with or without shapes. |
| **NetCDF (.nc)** | Format for multi-dimensional grids, here *year × y × x*. Stores the satellite composites. |
| **CSV** | Plain text table, opens in Excel. |
| **DuckDB (.duckdb)** | A small analytics database in one file. You can query it with SQL. |
| **HTML** | A web page. The interactive map. |

### 1.12 Other terms
| Term | Meaning |
|---|---|
| **Zonal statistics** | Summarising raster pixels inside each shape. For example, "mean LST of all pixels inside ward 138". |
| **Rasterize** | Paint shapes onto a pixel grid, so each pixel knows which ward it belongs to. |
| **PM2.5** | Fine airborne particles smaller than 2.5 micrometres; a key air-pollution measure (µg/m³). |
| **IDW (Inverse Distance Weighting)** | Estimating a value at an unmeasured place as a weighted average of nearby stations, where closer stations count more (weight = 1 / distance²). |
| **Monitoring station network** | The set of air-quality stations. Stations open, close or have data gaps, so the network changes from season to season. |
| **Leave-one-out cross-validation (LOO-CV)** | A test of how good IDW is: hide one station, predict it from the others, measure the error, and repeat for each station. **RMSE** (root mean squared error) summarises those errors. |
| **API key** | A personal password for a web service, such as OpenAQ. |
| **Environment variable** | A named setting held by the terminal session (for example `OPENAQ_API_KEY`) that programs can read without it being written in code. |

---

## Part 2: The statistics and economics, in plain English

### 2.1 Correlation vs regression
- **Correlation (r or ρ)** runs from −1 to +1 and says whether two things move together. −0.5 means "when NDVI is higher, LST tends to be lower".
- **Spearman's ρ** is a correlation based on rankings. It's robust to outliers and doesn't assume a straight line.
- **Regression** goes further: it estimates *how much* Y changes when X changes, while holding other things fixed.

### 2.2 Reading a regression result
Take `LST = a + b × GreenCover + error`.

| Term | Meaning |
|---|---|
| **Coefficient (b)** | The effect size. If b = −0.069, then +1 percentage point of green cover goes with 0.069 °C cooler, so **10 pp less green ≈ 0.69 °C hotter**. |
| **Standard error (SE)** | The uncertainty in b. Smaller is more precise. |
| **95 % confidence interval (CI)** | The range of plausible values for b (roughly b ± 2 × SE). A CI of 0.60–0.78 means the effect is very likely between those numbers. |
| **p-value** | The chance of seeing an effect this large if there were really *no* effect. Below 0.05 is called "statistically significant". |
| **R²** | Share of the variation in Y explained by the model (0–1). |
| **n / observations** | How many data points went in. |
| **pp (percentage points)** | An absolute change in a percentage: 30 % → 24 % is −6 pp (but −20 % in relative terms). |

### 2.3 Why simple comparisons mislead: **confounding**
Leafy neighbourhoods (such as Cubbon Park or Malleshwaram) differ from industrial areas in many ways: building density, lakes, elevation, road widths. If you just compare them, you can't tell whether trees *or those other differences* cause the temperature gap. A hidden factor that affects both X and Y is a **confounder**.

### 2.4 Panel data
**Panel data** follow the **same units over time**. Here that's the same grid cells or wards, measured every year (and every season). Panels let us compare each place **with itself** over time.

### 2.5 Fixed effects (FE): the key idea
- **Unit fixed effects** (one for each cell or ward) absorb everything **permanent** about a place: its lakes, density, elevation. The model then only uses *changes within each place*.
- **Time fixed effects** (one for each year or season) absorb everything that hit **the whole city at once** that year, such as a drought (2024!), El Niño or a hotter summer overall.
- **Two-way fixed effects (TWFE)** use both. What's left is: *places whose greenery changed more than the city average; did they also warm more than the city average?* This is far more convincing than a raw comparison.

In the code, `C(cell)` and `C(year)` in a formula create these fixed effects: `C()` means "treat as categories".

### 2.6 Other designs used
| Term | Meaning |
|---|---|
| **Pooled OLS** | A plain regression ignoring that observations come from the same places. It's shown for comparison to demonstrate why FE matters. **OLS** = ordinary least squares, the standard regression method. |
| **Clustered standard errors** | The same ward measured 10 times isn't 10 independent facts. Clustering by ward makes the SE honest about that. |
| **Long difference** | Compare each place's *change* between two periods: 2022–23 average vs 2025–26 average. Averaging two years at each end reduces random year-to-year noise. |
| **Robustness check** | Re-run the model on a different sample or specification. If the answer stays similar, it's more believable. |
| **Bad control** | A variable that *shouldn't* be in a regression because it's itself an outcome of what you're studying, or not a real cause. Including it distorts the main estimate. That's why PM2.5 isn't used as a control in the heat model. |
| **Spatial correlation** | Nearby places share the same shocks. With interpolated PM2.5, all wards around one station move together whenever that station's reading moves. Ordinary standard errors treat those wards as independent and become **too small**, so p-values look more significant than they are. |
| **Placebo / permutation test** | A "fake treatment" check. Shuffle the data so any real relationship is destroyed (here, which station had which reading), re-estimate many times (200), and see how big the effects are by pure chance. **Permutation p-value** = the share of shuffled runs with an effect at least as large as the real one. If the real effect is bigger than almost all shuffled ones (p < 0.05), it's unlikely to be an artefact. |
| **Heterogeneity** | The effect differs across groups. Here it differs across seasons: greenery cools far more in summer. |
| **Quartile** | Split the data into four equal-sized groups by some value (lowest 25 %, …, highest 25 %). |
| **Statistically significant trend** | Our +2.7 °C over 2022–2026 has p = 0.20 as a simple trend: with only 5 years and big weather swings, we can't call it a trend yet. That's why the conclusions rest on the FE models instead. |

### 2.7 Economics terms used in the write-ups
| Term | Meaning |
|---|---|
| **Externality** | A cost or benefit that falls on people who didn't choose it. Cutting a tree heats the neighbours' street too. |
| **Public good** | Something everyone benefits from and no one can be excluded from, such as shade and cooling. Markets under-provide these. |
| **Shadow price** | The "true" value of something that has no market price, such as the cooling a tree provides. |
| **Pigouvian levy** | A tax set equal to the harm an externality causes, to correct behaviour. |
| **Hedonic pricing** | Inferring the value of a feature (for example, nearby parks) from how much more people pay for houses that have it. |
| **Dose-response function** | How an outcome (productivity, deaths) changes per unit of exposure (per °C). |
| **Discount rate** | How much less we value future benefits than present ones. Central to climate cost-benefit debates. |

---

## Part 3: How the repo is organised

```
bengaluru-uhi/
├── README.md                ← the project's front page: findings + how to run
├── run_all.sh               ← runs every step in order
├── requirements.txt         ← list of Python libraries to install
├── .gitignore               ← files Git should NOT upload (big data, secrets)
├── src/                     ← all the code
├── data/                    ← inputs and downloaded data (mostly not uploaded)
│   ├── raw/bbmp_wards_225.kml
│   └── wards_web.geojson
├── outputs/                 ← results: tables, figures, maps
└── docs/                    ← write-ups (methodology, economics, application guide, this file)
```

**Two parts of the analysis:**
- **Part A (city grid):** `composites.py` → `modis.py` → `analysis.py` → `figures.py`
- **Part B (wards):** `wards.py` → `seasonal.py` → `air_quality.py` → `panel.py` → `ward_models.py` → `ward_maps.py`

### Python libraries used
| Library | Job |
|---|---|
| `numpy` | Fast maths on arrays of numbers |
| `pandas` | Tables (DataFrames), like Excel in code |
| `xarray` | Labelled multi-dimensional arrays (year × y × x); pandas for grids |
| `dask` | Splits big computations into chunks; works *lazily* (plans first, computes on `.compute()`) |
| `pystac-client` | Searches the STAC catalog |
| `planetary-computer` | Signs download URLs for Planetary Computer |
| `stackstac` | Turns a list of STAC scenes into one xarray "stack" (time × band × y × x), downloading only the needed window |
| `rasterio` | Reads and writes raster images; built on **GDAL**, the core open-source geospatial engine |
| `geopandas` | pandas with a geometry column, for shapes |
| `shapely` | Geometry operations (repair, simplify, area) |
| `pyproj` | Coordinate conversions between CRSs |
| `scipy` | Scientific tools (correlations, trends) |
| `statsmodels` | Regression models with proper standard errors |
| `matplotlib` | Static charts (PNG) |
| `plotly` | Interactive charts and maps (HTML) |
| `duckdb` | Embedded SQL database |
| `requests` | Calling web APIs (OpenAQ) |

---

## Part 4: Every file explained

### `run_all.sh`: the conductor
A **shell script** (a list of terminal commands).
- `set -euo pipefail` means "stop immediately if anything fails", so you never get results built on a broken step.
- It checks that Python is 3.10 or newer, then runs each Python script in order.

### `requirements.txt`
One library per line. `pip install -r requirements.txt` installs them all.

### `.gitignore`
Tells Git not to upload large downloaded files (`data/*.nc`, `data/seasonal/`, the database) or secrets (`.env`). They can be rebuilt by running the pipeline.

---

### `src/config.py`: every setting in one place
All analytical choices live here, so they're visible and easy to change.

| Setting | Meaning |
|---|---|
| `BBOX` | The ~60 × 55 km study rectangle around Bengaluru |
| `CENTER` | Vidhana Soudha's coordinates, used as the city centre |
| `EPSG = 32643` | Work in UTM metres |
| `RES = 60` | Landsat analysis pixel size, 60 m |
| `YEARS` | 2022–2026 |
| `SEASON` | 1 March – 31 May (pre-monsoon summer) |
| `MAX_SCENE_CLOUD = 30` | Skip scenes over 30 % cloudy |
| `CORE_RADIUS_KM = 15` | The "core city" circle (≈ BBMP area) |
| `RURAL_RING_KM = (22, 30)` | The countryside comparison ring |
| `GREEN_NDVI = 0.4` | The green-cover threshold |
| `GRID_KM = 1` | Grid cell size for Part A |
| `SEASONS` | Part B seasons: winter (January–February) and summer (March–May) |
| `S2_RES = 20` | Sentinel-2 pixel size used, 20 m |
| `MIN_VALID_PCT = 60` | A ward-season needs at least 60 % cloud-free pixels |

It also:
- registers a **progress bar** for long computations;
- has `UHI_SINGLE_THREADED=1`, a troubleshooting switch to process one piece at a time;
- sets GDAL network **retry** settings;
- has `UHI_FORCE=1`, which rebuilds outputs even if they exist.

---

### `src/composites.py`: Landsat summer images (Part A, step 1)
**Goal:** for each summer from 2022 to 2026, one clean image of **LST** and **NDVI**.

1. **`catalog()`** opens the Planetary Computer STAC catalog. `sign_inplace` adds download tokens automatically.
2. **`utm_bounds()`** converts the lat/lon `BBOX` into UTM metres, snapped to the 60 m grid.
3. **`year_composite(cat, year, bounds, season)`**:
   - **Search** for Landsat 8/9 scenes over Bengaluru in that season with less than 30 % cloud.
   - **Stack** them with `stackstac.stack(...)`, downloading only the `red`, `nir08`, `lwir11` (thermal) and `qa_pixel` bands for our box at 60 m.
   - **Cloud mask:** `QA_REJECT` combines the QA bits for fill, dilated cloud, cirrus, cloud and cloud shadow. A pixel is "clear" only if none of those bits are set.
   - **Convert raw numbers to physical units** using USGS's published scale factors:
     - reflectance = `DN × 0.0000275 − 0.2`;
     - temperature in Kelvin = `DN × 0.00341802 + 149.0`, minus 273.15 to get °C.

     (**DN** = "digital number", the raw integer stored in the file.)
   - Compute **NDVI**, drop impossible values (LST outside 5–75 °C, NDVI outside −1 to 1), and take the **median** over time.
   - Output: `lst_c`, `ndvi` and `n_obs` (how many clear observations each pixel had).
4. **`worldcover()`** downloads ESA WorldCover 2021, resampled with *mode* to 60 m. It's used as a fixed map of where built-up, cropland and water are.
5. **`main()`** runs all five years, then saves `data/composites.nc` and `data/worldcover.nc`. It skips if those exist (unless `UHI_FORCE=1`).

### `src/modis.py`: night and day temperature (Part A, step 2)
**Why:** Landsat only passes at 10:30 am. MODIS also passes at night, when heat islands are strongest.
- Searches MODIS 8-day LST products (Terra and Aqua) for March–May each year.
- Reads `LST_Day_1km` and `LST_Night_1km` at 1 km. Raw value × 0.02 = Kelvin; values below 7500 (150 K) are "no data".
- Averages each season and saves `data/modis.nc`.

### `src/analysis.py`: Part A statistics (step 3)
- **`load()`** opens the three data files.
- **`dist_km()`** gives each pixel's distance from the city centre in km.
- **`zones()`** creates three masks (true/false grids):
  - **core:** within 15 km, not water;
  - **urban:** within 15 km and WorldCover "built-up";
  - **rural:** 22–30 km out and vegetation or cropland.
- **`yearly()`** makes one row per year with, among others:
  - core, urban and rural mean LST, and **daytime SUHI** = urban − rural;
  - NDVI and **green cover %**;
  - **green cooling** = LST of non-green pixels − LST of green pixels;
  - a regression slope of LST on NDVI ("°C per 0.1 NDVI");
  - **UTFVI hotspots** (Urban Thermal Field Variance Index = (pixel temperature − mean) / pixel temperature; above 0.02 marks the strongest heat stress);
  - **MODIS night and day SUHI**.
- **`grid_panel()`** aggregates 60 m pixels into ~1 km cells (17 × 17 pixels) inside the core. Each cell-year gets mean LST, green %, NDVI, built-up % and cropland %. It keeps only cells that are fully inside the core and valid in all 5 years, a **balanced panel** of 624 cells.
- **`panel_models()`**:
  - **TWFE:** `lst ~ green + C(cell) + C(year)`, with SE clustered by cell. Result: **10 pp less green → +0.69 °C**.
  - **Pooled** model for comparison: −0.47, smaller because geography confounds it.
  - **Long difference** 2022–23 → 2025–26, using LST *relative to that year's city mean*: **+0.80 °C**.
  - **Quartiles** of green change: the biggest-loss cells warmed +0.82 °C relative to the city.
  - **Robustness:** the same TWFE on cells with less than 10 % cropland (0.65) and more than 50 % built-up (0.71). Rain makes farmland green or brown, so excluding it checks that we're measuring development, not rainfall.
- **`main()`** writes `outputs/yearly_metrics.csv`, `grid_panel.csv`, `grid_long_difference.csv` and `results.json`.

### `src/figures.py`: Part A charts (step 4)
- **Colour rules:** temperature uses a single-hue orange scale; *changes* use blue ↔ grey ↔ red (red = bad: hotter, or green lost).
- **`fig_lst_maps`**: summer 2022 vs 2026 LST maps, plus a map of relative warming.
- **`fig_green_maps`**: green cover in 2022–23, plus the change to 2025–26.
- **`fig_timeseries`**: five summers of core LST, green %, and the night heat island.
- **`fig_scatter`**: each cell's green change vs warming, with the fitted line, plus a quartile bar chart.

---

### `src/wards.py`: ward boundaries (Part B, step 1)
1. **`read_kml()`** reads the KML with geopandas/GDAL. Quirk: the file's `id` field arrives as `id2`.
2. **`standardise()`** sets the CRS to EPSG:4326, renames columns (`ward_id`, `ward_name`, …), converts text to numbers, and drops altitude (`force_2d`).
3. **`validate()`**:
   - checks for exactly 225 wards, unique ids and no empty shapes;
   - **repairs** 36 self-crossing polygons (`make_valid`);
   - computes area in km² in UTM and **checks it against the file's own `ward_area`** (they match);
   - adds **population density** and **SC/ST share %**.
4. **`main()`** saves `data/wards.parquet` (full detail) and `data/wards_web.geojson` (simplified to ±25 m for the web map).

### `src/seasonal.py`: satellite data per ward season (Part B, step 2)
For each year × season (winter and summer), produces two files:
- **Landsat LST** (`landsat_YEAR_SEASON.nc`), reusing `composites.year_composite` over the ward area.
- **Sentinel-2 NDVI** (`s2_YEAR_SEASON.nc`), via `sentinel2_ndvi()`:
  - bands `B04` (red), `B08` (NIR) and `SCL` (cloud classes) at 20 m;
  - keeps SCL classes 4 (vegetation), 5 (bare or built) and 6 (water);
  - **processing-baseline fix:** since January 2022, Sentinel-2 files add +1000 to every value, so it is subtracted before dividing by 10000 to get reflectance;
  - NDVI, then median over time.
- **`ward_bounds()`** gives the rectangle around all wards plus a 1 km buffer.
- **`with_retry()`** retries up to 5 times with growing waits, **opening a fresh catalog each time** so the download links are new.
- **Caching:** finished files are skipped on re-run.

### `src/air_quality.py`: PM2.5 per ward (Part B, step 3, optional)
1. **Source priority:** first a local CPCB CSV at `data/raw/air_quality.csv`, otherwise OpenAQ with a key supplied **at runtime** (`runtime_api_key()`: an environment variable, or a hidden prompt), otherwise skip.
2. **`from_openaq()`** finds PM2.5 stations within 25 km of the centre, then downloads daily values page by page. It waits automatically if rate-limited (HTTP 429). The key goes only in a request header and is never logged.
3. **`load_readings()`** checks the columns and drops impossible values.
4. **`seasonal_station_means()`** averages each station's readings per year × season, keeping only station-seasons with at least 20 days of data.
5. **`idw()`** estimates PM2.5 at each ward's centre from all stations.
6. **`loo_rmse()`** runs leave-one-out cross-validation, reporting how accurate the interpolation is.
7. **Thin seasons dropped:** seasons with fewer than 5 stations are excluded (`MIN_STATIONS_PER_PERIOD`). With one station, every ward gets the same value, so there is no spatial information. **Fixed station set:** stations reporting in **every remaining** season are identified, and a second estimate, `est_pm25_fixed`, uses only those. This means changes in the network (stations appearing or disappearing) can't create fake changes in a ward's PM2.5.
8. **Diagnostics:** for each season, it records the number of stations, how many are in the fixed set, the LOO-CV error, the median distance from a ward to its nearest station, and the % of wards within 3 km of a station. These are printed and saved to `outputs/aq_diagnostics.csv`.
9. Output: `data/ward_pm25.parquet` with `est_pm25`, `est_pm25_fixed`, `nearest_station_km`, `n_stations` and `idw_loo_rmse`.

### `src/panel.py`: building the ward dataset (Part B, step 4)
1. **`ward_raster()`** "paints" ward ids onto the satellite pixel grid (**rasterize**), so each pixel knows its ward.
2. **`zonal()`** computes each ward's mean value and the % of valid pixels.
3. **`build()`** loops over 5 years × 2 seasons and creates one row per ward-season: `mean_lst_c`, `mean_ndvi`, `green_cover_pct`, the valid-pixel percentages and scene counts. It adds **MODIS night LST** for summer (approximate, since many wards are smaller than a 1 km MODIS pixel), merges **PM2.5** if available, and flags `in_sample` (enough clear pixels).
4. **`validate()`** runs 8 automated checks, such as the right row count, a unique key, values in physical ranges, enough coverage, and NDVI–LST correlation being negative.
5. **`store()`** writes the panel to `outputs/ward_panel.parquet` and `.csv`, and to **DuckDB** tables `wards`, `ward_panel` and `validation_log`.

Result: **2,250 rows** (225 wards × 5 years × 2 seasons), all passing.

### `src/ward_models.py`: Part B econometrics (step 5a)
- **`fe()`** is a helper: OLS with SE clustered by ward.
- **`models()`**:
  - **M1:** `LST ~ NDVI + ward FE + period FE`. Effect of a 0.1 NDVI drop: **+0.82 °C**.
  - **M2:** the same with green cover %: 10 pp lost → +0.37 °C (both seasons).
  - **M3/M4:** summer only (**+1.9 °C** per 0.1 NDVI) vs winter only (+0.24 °C).
  - **M2s:** summer, green cover: **10 pp lost → +1.0 °C**.
  - **Pooled** model for comparison.
  - **M1-PM** (only if PM2.5 exists): M1 re-run on **only the seasons that have PM2.5 data**. It's the like-for-like baseline for M5. Comparing M5 with the full M1 would mix two changes (adding PM2.5 *and* dropping seasons).
  - **M5:** M1-PM plus PM2.5 as a control, a sensitivity check of whether pollution explains the heat result.
  - **A1:** PM2.5 as the *outcome*: does green loss go with more pollution?
  - **A2:** A1 re-run using the **fixed station set** only.
  - **A3:** A1 re-run on **wards within 3 km of a station**, where the interpolated values are most reliable.
- **`placebo_a1()`**: the **permutation test** for A1. Within each season it shuffles which station had which reading, re-interpolates to wards, and re-estimates A1, 200 times. It reports the real effect, the range of shuffled ("placebo") effects, and the **permutation p-value**, and saves them to `outputs/aq_placebo_test.csv`. *Why it's needed:* when tested on completely random fake station data, the normal clustered p-value said "highly significant" (p < 0.001), but the placebo test correctly said "not real" (p = 0.33). Interpolation makes ordinary p-values over-confident, as explained under spatial correlation in Part 2.
- **`ward_change()`** computes each ward's summer change 2022–23 → 2025–26, joined with ward attributes.
- **`equity()`** computes Spearman correlations of heat and green cover with SC/ST share and density, plus a quartile table.
- **`main()`** writes `ward_model_results.csv`, `ward_change_2022_2026.csv`, `top10_heat_wards.csv`, `equity_by_scst_quartile.csv` and `ward_results.json`.

### `src/ward_maps.py`: ward maps (step 5b)
- **`interactive()`** builds `outputs/maps/ward_explorer.html` with Plotly:
  - a **dropdown** with 6 layers: summer LST, heat vs city average, green %, green change, relative warming, night LST;
  - **hover** shows each ward's name, constituency, values and SC/ST share;
  - the **top 10** hottest wards are outlined and numbered, with a key.
  - It uses SVG drawing, so no WebGL or internet map tiles are needed.
- **`static()`** draws the two-panel PNG for the README.

---

## Part 5: The outputs and how to read them

| File | What it is |
|---|---|
| `outputs/figures/fig1_lst_maps.png` | Summer heat in 2022 vs 2026 and where it rose most |
| `outputs/figures/fig2_green_change.png` | Green cover and where it was lost |
| `outputs/figures/fig3_timeseries.png` | Five summers: heat, green, night heat island |
| `outputs/figures/fig4_green_vs_heat.png` | The core result: losing green → warming |
| `outputs/figures/fig5_ward_maps.png` | Hottest wards, and green change by ward |
| `outputs/maps/ward_explorer.html` | Interactive ward map (open in a browser) |
| `outputs/yearly_metrics.csv` | Part A: one row per year |
| `outputs/results.json` | Part A: all model results |
| `outputs/ward_panel.csv` / `.parquet` | Part B: the 2,250-row dataset |
| `outputs/ward_model_results.csv` | Part B: every model's effect, SE, CI and p-value |
| `outputs/top10_heat_wards.csv` | The 10 hottest wards |
| `outputs/equity_by_scst_quartile.csv` | Heat and green cover by SC/ST-share quartile |
| `outputs/aq_diagnostics.csv` | PM2.5: stations, interpolation error and distance to stations, per season (only if the air-quality step ran) |
| `outputs/aq_placebo_test.csv` | PM2.5: placebo-test result for A1 (only if the air-quality step ran) |
| `data/uhi.duckdb` | Everything queryable with SQL |

**Your PM2.5 results, read in plain English** (from `outputs/ward_model_results.csv` and `aq_placebo_test.csv`):

| Row | Value | Meaning |
|---|---|---|
| M1-PM | +0.50 °C | On the 5 seasons with PM2.5 data, a 0.1 NDVI drop goes with a 0.50 °C hotter ward. |
| M5 | +0.42 °C | Adding PM2.5 as a control barely changes this, so **pollution doesn't explain the heat result**. (Its drop from the full-sample 0.82 °C comes mostly from using fewer seasons, which is why M1-PM is needed.) |
| A1 | +8.7 µg/m³ | Wards that lost vegetation also saw higher interpolated PM2.5. |
| A2 | +6.0 µg/m³ | Still there using only the 7 stations present in every season, so it isn't an artefact of the network changing. |
| A3 | +9.5 µg/m³ (wide CI) | Still there near stations, where the estimates are most reliable. |
| Placebo | p = 0.025 | The real effect is larger than 97.5 % of 200 "shuffled" fakes. |

**Overall:** a **secondary, suggestive** finding. It is consistent across checks, but it's an association (construction may drive both green loss and dust) based on only 7–13 stations, 5 of 10 seasons, and large interpolation error.

**Example of reading a model row:** `M2s summer only: 10 pp green-cover loss -> °C | effect 1.017 | ci95 0.763–1.272 | p 0.000`
→ *"In summer, a ward that loses 10 percentage points of green cover becomes about 1 °C hotter, most likely between 0.76 and 1.27 °C, and this is very unlikely to be chance."*

---

## Part 6: Interview cheat sheet

1. **"What is NDVI?"** A greenness index from red and near-infrared light. Plants reflect NIR and absorb red, so higher NDVI means more vegetation.
2. **"What is LST, and how is it different from air temperature?"** Surface skin temperature from thermal satellite bands. Roads can be 15 °C hotter than the air above them. It's a proxy for felt heat, not the same thing.
3. **"Why fixed effects?"** To compare each place with itself over time (removing permanent differences) and remove city-wide weather shocks (year effects).
4. **"Why is the daytime heat island negative?"** In Bengaluru's pre-monsoon summer the surrounding farmland is dry and bare, and heats up faster than the city with its trees and lakes. The heat island appears at night.
5. **"Why isn't PM2.5 in your heat regression?"** It doesn't drive surface temperature and is itself an outcome of urbanisation, so it would be a bad control. It's analysed separately.
6. **"How do you know the PM2.5 result isn't an artefact of interpolation?"** I ran a permutation (placebo) test: shuffle station readings 200 times and compare the real effect with the shuffled ones. I also checked it with a fixed station set and with wards near a station. On fake random data, ordinary p-values were wrongly "significant" but the placebo test wasn't, which is why I rely on it.
7. **"What are the limits?"** Surface vs air temperature, NDVI vs actual trees, only 5 years, MODIS's 1 km pixels vs small wards, Census-2011 population data, and correlation rather than a controlled experiment.
8. **"What would you do next?"** Validate against IMD air temperatures, use tree-canopy data, link to income data, and convert °C into economic costs.

---

## Part 7: Git, GitHub and the website

### 7.1 Three copies of the project
```
  Cloud session (Claude)        GitHub (online)              Your MacBook
  ──────────────────────        ───────────────              ────────────
  ran the pipeline     ──push──▶  repo "main"   ──clone/pull──▶  your copy
                                  + website (Pages)            ran the pipeline again
```
- **Git** is version control. It saves snapshots of the project so you can see and undo every change.
- **GitHub** is a website that hosts Git repositories online.
- **Repository (repo):** the project folder plus its full history.
- **Branch:** a line of development. Ours is `main`.

### 7.2 The Git commands you will use
| Command | What it does |
|---|---|
| `git clone <url>` | Download a repo from GitHub for the first time |
| `git pull` | Download new changes from GitHub into your copy |
| `git status` | Show what changed on your laptop since the last commit: **modified** files and **untracked** (new) files |
| `git add <files>` | Choose which changes go into the next snapshot |
| `git commit -m "message"` | Save a snapshot locally, with a description |
| `git push` | Upload your commits to GitHub |

**Key point:** running the code on your laptop changes files **only on your laptop**. Nothing reaches GitHub until you `add`, `commit` and `push`. The map currently on the website was generated in the cloud session and pushed from there. Your laptop run made an identical heat map, plus PM2.5 results that are not uploaded yet.

**What never goes to GitHub:** files listed in `.gitignore` (large downloads, the database, `.env`) and anything secret, such as your API key. Git keeps history forever, so a secret pushed once stays in the history even if you delete it later.

### 7.3 How the interactive map (HTML) is created
In `src/ward_maps.py`, `interactive()`:
1. **Loads** ward shapes (`data/wards_web.geojson`) and ward results (`outputs/ward_change_2022_2026.csv`, `top10_heat_wards.csv`).
2. **Builds a Plotly figure:**
   - six **choropleth** layers (a choropleth is a map where each area is coloured by a value);
   - **hover text** for each ward;
   - outlines and numbered markers for the top 10 wards;
   - a **dropdown** that shows one layer at a time.
3. **Writes it** with `fig.write_html(..., include_plotlyjs="cdn")`. Plotly puts all the shapes, numbers and settings **inside the HTML file**, plus one line that loads Plotly's drawing code from a **CDN** (content-delivery network, a public server for common code libraries).

When anyone opens the file, their **browser** reads the embedded data and draws the map itself. No Python or server is needed. That makes it a **static** web page, which is why it works both by double-clicking it on your laptop and when hosted on GitHub Pages.

### 7.4 How GitHub Pages turned the repo into a website
- **GitHub Pages** is free static web hosting built into GitHub. Turning it on (repo **Settings → Pages → Deploy from a branch → `main` / root**) tells GitHub to serve the repo's files as a public website.
- GitHub then runs an automatic job, visible in the **Actions** tab as "pages build and deployment". It copies the files on `main`, runs **Jekyll** (a simple site builder that turns Markdown such as `README.md` into web pages), and publishes the result.
- **Web address = username + repo + folder path:** `https://chaitrika-g.github.io/bengaluru-uhi/` + `outputs/maps/ward_explorer.html`.
- **Every push to `main` automatically re-publishes the site** within a minute or two.

**One-line version for interviews:** *"The analysis is published as a static GitHub Pages site; the interactive ward map is a self-contained Plotly HTML page generated by the pipeline and redeployed automatically on every push."*
