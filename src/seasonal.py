"""Step 2 - Satellite extraction per year x dry season over the BBMP ward extent.

  * Land Surface Temperature: Landsat 8/9 Collection 2 L2 (ST_B10), 60 m  [reuses composites.py]
  * NDVI + green cover: Sentinel-2 L2A, 20 m, SCL cloud mask             [this module]

Both are seasonal per-pixel medians, cached to data/seasonal/{sensor}_{year}_{season}.nc so a
failed run resumes where it stopped. Accessed through Microsoft Planetary Computer (no account).
"""
import logging
import time

import geopandas as gpd
import numpy as np
import rasterio
import stackstac
import xarray as xr

import config as cfg
from composites import catalog, year_composite

log = logging.getLogger("seasonal")
OUT = cfg.DATA / "seasonal"
SCL_CLEAR = [4, 5, 6]  # Sentinel-2 scene classes: vegetation, not-vegetated, water
BOA_OFFSET = 1000      # processing baseline >= 04.00 (all scenes from 25 Jan 2022) adds +1000 DN


def ward_bounds(res, buffer_m=1000):
    wards = gpd.read_parquet(cfg.DATA / "wards.parquet").to_crs(cfg.EPSG)
    x0, y0, x1, y1 = wards.total_bounds
    snap = lambda v, f: float(f(v / res) * res)
    b = (snap(x0 - buffer_m, np.floor), snap(y0 - buffer_m, np.floor),
         snap(x1 + buffer_m, np.ceil), snap(y1 + buffer_m, np.ceil))
    bbox = list(gpd.GeoSeries(gpd.points_from_xy([b[0], b[2]], [b[1], b[3]]), crs=cfg.EPSG)
                .to_crs(4326).total_bounds)
    return b, bbox


def with_retry(fn, tries=5):
    """Call fn(cat) up to `tries` times. Each attempt opens a NEW catalog connection, which
    issues fresh signed download URLs - old ones expire if the laptop sleeps or Wi-Fi drops."""
    for i in range(tries):
        try:
            return fn(catalog())
        except Exception as e:  # network drop, DNS failure, expired signed URL, API reset
            if i == tries - 1:
                log.error("Giving up after %d attempts. Check your internet connection, then re-run: "
                          "finished files are kept and skipped.", tries)
                raise
            wait = min(15 * 2 ** i, 240)
            log.warning("Attempt %d/%d failed (%s: %s); retrying in %ds with fresh links",
                        i + 1, tries, type(e).__name__, str(e)[:150], wait)
            time.sleep(wait)


def sentinel2_ndvi(cat, year, season, bounds, bbox):
    s0, s1 = cfg.SEASONS[season]
    items = list(cat.search(collections=["sentinel-2-l2a"], bbox=bbox,
                            datetime=f"{year}-{s0}/{year}-{s1}",
                            query={"eo:cloud_cover": {"lt": cfg.S2_MAX_CLOUD}}).items())
    if not items:
        raise RuntimeError(f"No Sentinel-2 scenes for {year} {season}")
    log.info("%d %s: %d Sentinel-2 scenes", year, season, len(items))
    stack = stackstac.stack(items, assets=["B04", "B08", "SCL"], epsg=cfg.EPSG,
                            resolution=cfg.S2_RES, bounds=bounds, rescale=False,
                            fill_value=np.uint16(0), dtype="uint16",
                            resampling=rasterio.enums.Resampling.nearest,
                            chunksize=(1, 1, 1024, 1024))
    baseline = stack["s2:processing_baseline"].astype(str)
    offset = xr.where(baseline >= "04.00", BOA_OFFSET, 0)
    red = (stack.sel(band="B04").astype("float32") - offset) / 10000
    nir = (stack.sel(band="B08").astype("float32") - offset) / 10000
    clear = stack.sel(band="SCL").isin(SCL_CLEAR) & (stack.sel(band="B04") > 0)
    ndvi = ((nir - red) / (nir + red)).where(clear & (red > 0) & (nir > 0))
    out = xr.Dataset({
        "ndvi": ndvi.median("time", skipna=True),
        "n_obs": clear.sum("time").astype("int16"),
    }).compute()
    out = out.drop_vars([v for v in out.coords if v not in ("x", "y")])
    out["scenes"] = len(items)
    return out


def landsat_lst(cat, year, season, bounds):
    ds = year_composite(cat, year, bounds, season=cfg.SEASONS[season]).squeeze("year", drop=True)
    return ds[["lst_c", "n_obs", "scenes"]]


def save(ds, path):
    for v in ds.variables:
        ds[v].attrs = {}
    ds.attrs = {}
    ds.to_netcdf(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s2_bounds, bbox = ward_bounds(cfg.S2_RES)
    ls_bounds, _ = ward_bounds(cfg.RES)
    for year in cfg.YEARS:
        for season in cfg.SEASONS:
            for sensor, fn in [("landsat", lambda cat: landsat_lst(cat, year, season, ls_bounds)),
                               ("s2", lambda cat: sentinel2_ndvi(cat, year, season, s2_bounds, bbox))]:
                path = OUT / f"{sensor}_{year}_{season}.nc"
                if path.exists() and not cfg.FORCE:
                    log.info("cached: %s", path.name)
                    continue
                t = time.time()
                save(with_retry(fn), path)
                log.info("wrote %s in %.0fs", path.name, time.time() - t)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    main()
