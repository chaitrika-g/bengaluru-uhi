"""Step 4 - Zonal statistics + reconciliation into a validated ward x year x season panel.

Output:
  data/uhi.duckdb             tables: wards, ward_panel, validation_log
  outputs/ward_panel.parquet  same panel, for anyone without DuckDB
  outputs/ward_panel.csv

Grain: one row per (ward_id, year, season). Key columns:
  mean_lst_c, mean_ndvi, green_cover_pct, valid_lst_pct, valid_ndvi_pct, in_sample,
  night_lst_c (summer only, MODIS 1 km - approximate for small wards), est_pm25 (if available)
"""
import logging

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from rasterio.features import rasterize
from rasterio.transform import from_origin

import config as cfg

log = logging.getLogger("panel")
SEASONAL = cfg.DATA / "seasonal"


def ward_raster(wards, da):
    """Burn ward ids onto a raster grid (pixel centre inside polygon)."""
    res = float(abs(da.x[1] - da.x[0]))
    transform = from_origin(float(da.x[0]) - res / 2, float(da.y[0]) + res / 2, res, res)
    return rasterize(zip(wards.geometry, wards.ward_id), out_shape=(da.sizes["y"], da.sizes["x"]),
                     transform=transform, fill=0, dtype="int32")


def zonal(ids, arrays: dict):
    """Mean (ignoring NaN) and valid-pixel share of each array, per ward id."""
    flat = ids.ravel()
    m = flat > 0
    df = pd.DataFrame({"ward_id": flat[m], **{k: v.ravel()[m] for k, v in arrays.items()}})
    g = df.groupby("ward_id")
    out = g.mean()
    for k in arrays:
        out[f"valid_{k}_pct"] = 100 * g[k].count() / g.size()
    out["pixels"] = g.size()
    return out


def build(wards):
    rows = []
    for year in cfg.YEARS:
        for season in cfg.SEASONS:
            ls = xr.open_dataset(SEASONAL / f"landsat_{year}_{season}.nc")
            s2 = xr.open_dataset(SEASONAL / f"s2_{year}_{season}.nc")
            z_ls = zonal(ward_raster(wards, ls), {"lst": ls.lst_c.values})
            ndvi = s2.ndvi.values
            green = np.where(np.isnan(ndvi), np.nan, (ndvi > cfg.GREEN_NDVI) * 100.0)
            z_s2 = zonal(ward_raster(wards, s2), {"ndvi": ndvi, "green": green})
            df = pd.DataFrame({
                "ward_id": wards.ward_id.values, "year": year, "season": season,
            }).set_index("ward_id")
            df["mean_lst_c"] = z_ls["lst"]
            df["valid_lst_pct"] = z_ls["valid_lst_pct"]
            df["mean_ndvi"] = z_s2["ndvi"]
            df["green_cover_pct"] = z_s2["green"]
            df["valid_ndvi_pct"] = z_s2["valid_ndvi_pct"]
            df["landsat_scenes"] = int(ls.scenes)
            df["s2_scenes"] = int(s2.scenes)
            rows.append(df.reset_index())
            log.info("%d %s: LST valid median %.0f%%, NDVI valid median %.0f%%", year, season,
                     df.valid_lst_pct.median(), df.valid_ndvi_pct.median())
    panel = pd.concat(rows, ignore_index=True)

    # MODIS night LST (summer only): 1 km, bilinear-resampled to 250 m before zonal mean
    md = xr.open_dataset(cfg.DATA / "modis.nc")
    xs = np.arange(float(md.x.min()), float(md.x.max()), 250.0)
    ys = np.arange(float(md.y.max()), float(md.y.min()), -250.0)
    fine = md.lst_night_c.interp(x=xs, y=ys)
    ids = ward_raster(wards, fine.isel(year=0))
    night = pd.concat([zonal(ids, {"night": fine.sel(year=y).values})[["night"]]
                       .assign(year=y, season="summer") for y in cfg.YEARS]).reset_index()
    panel = panel.merge(night.rename(columns={"night": "night_lst_c"}),
                        on=["ward_id", "year", "season"], how="left")

    pm = cfg.DATA / "ward_pm25.parquet"
    if pm.exists():
        panel = panel.merge(pd.read_parquet(pm), on=["ward_id", "year", "season"], how="left")
        log.info("Merged PM2.5 estimates")
    else:
        panel["est_pm25"] = np.nan
        log.info("No PM2.5 file - est_pm25 left empty (run air_quality.py first to populate)")

    panel["period"] = panel.year.astype(str) + "_" + panel.season
    panel["in_sample"] = (panel.valid_lst_pct >= cfg.MIN_VALID_PCT) & (panel.valid_ndvi_pct >= cfg.MIN_VALID_PCT)
    return panel


def validate(panel, wards):
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": str(detail)})
        (log.info if ok else log.error)("[%s] %s %s", "PASS" if ok else "FAIL", name, detail)

    n_exp = len(wards) * len(cfg.YEARS) * len(cfg.SEASONS)
    check("row count = wards x years x seasons", len(panel) == n_exp, f"{len(panel)} vs {n_exp}")
    check("primary key unique", not panel.duplicated(["ward_id", "year", "season"]).any())
    check("LST within physical range 10-70 C", panel.mean_lst_c.dropna().between(10, 70).all(),
          f"min {panel.mean_lst_c.min():.1f}, max {panel.mean_lst_c.max():.1f}")
    check("NDVI within [-1, 1]", panel.mean_ndvi.dropna().between(-1, 1).all())
    check("green cover within [0, 100]", panel.green_cover_pct.dropna().between(0, 100).all())
    share = panel.in_sample.mean()
    check("in-sample share >= 80%", share >= 0.8, f"{100 * share:.1f}% of ward-seasons")
    per_ward = panel.groupby("ward_id").in_sample.sum()
    check("every ward has >= 6 of 10 periods", (per_ward >= 6).all(),
          f"min {per_ward.min()} periods; wards below: {per_ward[per_ward < 6].index.tolist()[:10]}")
    r = panel[panel.in_sample][["mean_ndvi", "mean_lst_c"]].corr().iloc[0, 1]
    check("sanity: NDVI-LST correlation negative", r < 0, f"r = {r:.2f}")
    return pd.DataFrame(checks)


def store(panel, wards, checks):
    cfg.OUT.mkdir(exist_ok=True)
    panel.to_parquet(cfg.OUT / "ward_panel.parquet", index=False)
    panel.round(4).to_csv(cfg.OUT / "ward_panel.csv", index=False)
    attrs = pd.DataFrame(wards.drop(columns="geometry"))
    attrs["geometry_wkt"] = wards.geometry.to_wkt()
    with duckdb.connect(str(cfg.DATA / "uhi.duckdb")) as con:
        for name, df in [("wards", attrs), ("ward_panel", panel), ("validation_log", checks)]:
            con.register("tmp", df)
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp")
            con.unregister("tmp")
        log.info("DuckDB tables: %s", con.execute("SHOW TABLES").fetchall())


def main():
    wards = gpd.read_parquet(cfg.DATA / "wards.parquet").to_crs(cfg.EPSG)
    panel = build(wards)
    checks = validate(panel, wards)
    store(panel, wards, checks)
    if not checks.passed.all():
        log.warning("%d validation check(s) failed - see validation_log", (~checks.passed).sum())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    main()
