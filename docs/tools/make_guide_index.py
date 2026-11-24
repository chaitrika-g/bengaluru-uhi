"""Rebuild the Contents and Term index in docs/BEGINNERS_GUIDE.md.
Usage: python docs/tools/make_guide_index.py docs/BEGINNERS_GUIDE.md
Re-run after adding or renaming guide sections; edit TERMS to add index entries."""
import re, sys
p = sys.argv[1]
s = open(p).read()
START, END = "<!-- INDEX:START -->", "<!-- INDEX:END -->"
if START in s:  # regenerate cleanly
    s = s[:s.index(START)] + s[s.index(END) + len(END) + 1:]

def slug(h, seen):
    t = h.strip().lower()
    t = re.sub(r"[^\w\- ]", "", t, flags=re.UNICODE).replace("_", "_")  # GitHub keeps letters, digits, _, -, space
    t = t.replace(" ", "-")
    n = seen.get(t, 0); seen[t] = n + 1
    return t if n == 0 else f"{t}-{n}"

seen, heads = {}, []
in_code = False
for line in s.splitlines():
    if line.startswith("```"):
        in_code = not in_code
    if in_code:
        continue
    m = re.match(r"^(#{2,3}) (.+)$", line)
    if m:
        text = m.group(2)
        heads.append((len(m.group(1)), text, slug(text, seen)))
anchor = {t: a for _, t, a in heads}

def find(prefix):
    for _, t, a in heads:
        if t.startswith(prefix):
            return t, a
    raise KeyError(prefix)

toc = ["## Contents", ""]
for lvl, t, a in heads:
    label = t.replace("**", "")
    toc.append(("- " if lvl == 2 else "  - ") + f"[{label}](#{a})")

TERMS = {  # term -> heading prefix where it is explained
    "API key": "1.12", "Attributable heat": "2.7", "Band (satellite)": "1.2", "Bad control": "2.6",
    "Bounding box (bbox)": "1.9", "Branch (Git)": "7.1", "CDN": "7.3", "Choropleth map": "7.3",
    "Cloud mask (QA_PIXEL, SCL)": "1.7", "Clustered standard errors": "2.6", "Coefficient": "2.2",
    "COG (Cloud-Optimized GeoTIFF)": "1.10", "Commit / push / pull": "7.2", "Composite": "1.8",
    "Confidence interval (CI)": "0.6", "Confounding / confounder": "0.7", "Correlation": "0.4",
    "CRS / EPSG / UTM": "1.9", "Discount rate": "2.7", "Distributional analysis": "2.7",
    "DuckDB": "1.11", "Environment variable": "1.12", "Externality": "2.7", "Extrapolation": "2.7",
    "Fixed effects (FE)": "0.7", "GDAL": "Python libraries used", "GeoJSON / KML / Parquet / NetCDF": "1.11",
    "GitHub Pages": "7.4", "Hedonic pricing": "2.7", "Heterogeneity": "2.6", "IDW (interpolation)": "1.12",
    "Jekyll": "7.4", "Landsat / Sentinel-2 / MODIS": "1.6", "Leave-one-out cross-validation (LOO-CV)": "1.12",
    "Long difference": "2.6", "LST (Land Surface Temperature)": "1.4", "Mean vs median": "0.2",
    "NDVI": "1.3", "OLS (ordinary least squares)": "0.5", "p-value": "0.6", "Panel data": "2.4",
    "Percentage points (pp)": "2.2", "Person-°C": "2.7", "Pigouvian levy": "2.7", "Pixel / resolution": "1.2",
    "Placebo / permutation test": "2.6", "PM2.5": "1.12", "Pooled OLS": "2.6", "Public good": "2.7",
    "Quartile": "2.6", "R²": "2.2", "Raster vs vector": "1.2", "Rasterize": "1.12", "Reflectance": "1.2",
    "Regression": "0.5", "Reproject / resample": "1.9", "Robustness check": "2.6", "Shadow price": "2.7",
    "Signed URL": "1.10", "Spatial correlation": "2.6", "Spearman's ρ": "2.1", "Standard deviation": "0.3",
    "Standard error (SE)": "0.6", "STAC (catalog)": "1.10", "Statistical significance": "0.6",
    "SUHI / Urban Heat Island": "1.5", "Two-way fixed effects (TWFE)": "2.5", "UTFVI (hotspots)": "src/analysis.py",
    "Zonal statistics": "1.12",
}
def pref(k):
    v = TERMS[k]
    return f"`{v}" if v.startswith("src/") else v
idx = ["## Term index (A–Z)", "", "Click a term to jump to where it's explained.", "",
       "| Term | Explained in |", "|---|---|"]
for term in sorted(TERMS, key=str.lower):
    t, a = find(pref(term))
    idx.append(f"| {term} | [{t.replace('**', '').replace('`', '')}](#{a}) |")

block = "\n".join([START] + toc + [""] + idx + ["", END, ""])
s = s.replace("\n---\n\n## Part 0:", "\n" + block + "\n---\n\n## Part 0:", 1)
assert START in s, "insertion point not found"
open(p, "w").write(s)
print(f"{len(heads)} headings, {len(TERMS)} terms")
