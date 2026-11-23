#!/usr/bin/env bash
# Full pipeline. Every step is cached/idempotent, so a failed run can simply be re-run.
set -euo pipefail
cd "$(dirname "$0")/src"

python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "ERROR: Python 3.10+ is required, found $(python --version 2>&1)."
  echo "Install Python 3.12 from python.org, then recreate the environment:"
  echo "  rm -rf .venv && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
}

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
