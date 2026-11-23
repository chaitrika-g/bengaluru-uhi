"""Study-wide configuration. Every analytical choice lives here so it is explicit and reproducible."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
FIG = OUT / "figures"

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

# Study window: ~60 x 55 km box around Bengaluru (lon/lat, WGS84)
BBOX = [77.35, 12.75, 77.90, 13.25]
CENTER = (77.5946, 12.9716)  # Vidhana Soudha, used as the city centre
EPSG = 32643                  # UTM zone 43N (metres)
RES = 60                      # analysis resolution in metres (Landsat thermal is natively 100 m)

YEARS = list(range(2022, 2027))
SEASON = ("03-01", "05-31")   # pre-monsoon summer: Bengaluru's hottest, least cloudy months
MAX_SCENE_CLOUD = 30          # % scene cloud cover; pixel-level cloud masking is applied on top

# Spatial zones (km from centre)
CORE_RADIUS_KM = 15           # "urban core": roughly the BBMP extent
RURAL_RING_KM = (22, 30)      # "rural reference" ring, outside the city's main built-up area

GREEN_NDVI = 0.4              # NDVI threshold for "green cover" (dense vegetation / tree canopy)
GRID_KM = 1                   # cell size for the spatial change analysis
