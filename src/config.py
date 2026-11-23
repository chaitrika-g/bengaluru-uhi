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

# ---------------------------------------------------------------- Ward-level panel (v2)
WARDS_KML = DATA / "raw" / "bbmp_wards_225.kml"
SEASONS = {  # Dry seasons only: Landsat is largely clouded out over Bengaluru Jun-Dec
    "winter": ("01-01", "02-28"),   # dry winter
    "summer": ("03-01", "05-31"),   # pre-monsoon summer
}
S2_RES = 20                        # Sentinel-2 NDVI resolution (m); bands are 10 m native
S2_MAX_CLOUD = 20
MIN_VALID_PCT = 60                 # a ward-season needs >=60% clear pixels to enter the panel
