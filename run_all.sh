#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/src"
python composites.py   # Landsat LST + NDVI yearly composites, WorldCover mask
python modis.py        # MODIS day/night LST
python analysis.py     # metrics, panel regressions, robustness
python figures.py      # figures
