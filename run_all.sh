#!/usr/bin/env bash
# Full pipeline. Every step is cached/idempotent, so a failed run can simply be re-run.
set -euo pipefail
cd "$(dirname "$0")/src"

echo "== Part A: city-wide grid study (Landsat summer composites, MODIS night) =="
python composites.py   # Landsat LST + NDVI yearly summer composites, WorldCover mask
python modis.py        # MODIS day/night LST
python analysis.py     # grid metrics, panel regressions, robustness
python figures.py      # figures 1-4

echo "== Part B: ward-level panel (225 BBMP wards x 5 years x 2 dry seasons) =="
python wards.py        # Step 1: KML -> validated GeoParquet/GeoJSON
python seasonal.py     # Step 2: Landsat LST + Sentinel-2 NDVI per year x season (cached)
python air_quality.py  # Step 3: PM2.5 IDW per ward (asks for OpenAQ key at runtime; Enter skips)
python panel.py        # Step 4: zonal stats -> validated panel in DuckDB + Parquet
python ward_models.py  # Step 5a: fixed-effects models, top-10 wards, equity
python ward_maps.py    # Step 5b: interactive + static ward maps
