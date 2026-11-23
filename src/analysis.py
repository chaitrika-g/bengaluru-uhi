"""All statistics for the study. Reads data/*.nc, writes outputs/*.csv and outputs/results.json.

Analyses
  A. Yearly city metrics (Landsat daytime LST, NDVI, green cover; MODIS day/night UHI)
  B. Intra-urban "cooling value" of green cover: LST of green vs non-green pixels, per year
  C. ~1 km grid panel (core city): two-way fixed-effects regression of LST on green cover,
     plus a long-difference (2022-23 -> 2025-26) model
  D. Heat hotspots: Urban Thermal Field Variance Index (UTFVI)
"""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import xarray as xr
from pyproj import Transformer
from scipy import stats

import config as cfg

WC_TREE, WC_BUILT, WC_WATER = 10, 50, 80
VEG_CLASSES = [10, 20, 30, 40]  # tree, shrub, grass, cropland


def load():
    ds = xr.open_dataset(cfg.DATA / "composites.nc")
    wc = xr.open_dataarray(cfg.DATA / "worldcover.nc")
    md = xr.open_dataset(cfg.DATA / "modis.nc")
    return ds, wc, md


def dist_km(obj):
    cx, cy = Transformer.from_crs(4326, cfg.EPSG, always_xy=True).transform(*cfg.CENTER)
    return (np.hypot(obj.x - cx, obj.y - cy) / 1000).transpose("y", "x")


def zones(ds, wc):
    d = dist_km(ds)
    core = (d < cfg.CORE_RADIUS_KM) & (wc != WC_WATER)
    urban = (d < cfg.CORE_RADIUS_KM) & (wc == WC_BUILT)
    rural = (d >= cfg.RURAL_RING_KM[0]) & (d <= cfg.RURAL_RING_KM[1]) & wc.isin(VEG_CLASSES)
    return core, urban, rural


def mean(da, mask):
    return float(da.where(mask).mean())


# ---------------------------------------------------------------- A + B + D
def yearly(ds, wc, md):
    core, urban, rural = zones(ds, wc)
    # MODIS zones on its own 1 km grid: built share from WorldCover
    built_share = (wc == WC_BUILT).astype(float).interp_like(md, method="linear")
    dm = dist_km(md)
    m_urban = (dm < cfg.CORE_RADIUS_KM) & (built_share > 0.5)
    m_rural = (dm >= cfg.RURAL_RING_KM[0]) & (dm <= cfg.RURAL_RING_KM[1]) & (built_share < 0.1)

    rows = []
    for y in cfg.YEARS:
        lst, ndvi = ds.lst_c.sel(year=y), ds.ndvi.sel(year=y)
        green = ndvi > cfg.GREEN_NDVI
        valid_core = core & lst.notnull() & ndvi.notnull()
        # UTFVI = (Ts - Tmean) / Ts, Ts in Kelvin, computed over the core city
        tk = lst.where(valid_core) + 273.15
        utfvi = (tk - tk.mean()) / tk
        slope = stats.linregress(ndvi.where(valid_core).values.ravel()[valid_core.values.ravel()],
                                 lst.where(valid_core).values.ravel()[valid_core.values.ravel()])
        nd = md.lst_night_c.sel(year=y)
        dd = md.lst_day_c.sel(year=y)
        rows.append({
            "year": y,
            "scenes": int(ds.scenes.sel(year=y)),
            "core_valid_pct": 100 * float(valid_core.sum() / core.sum()),
            "core_lst_c": mean(lst, core),
            "urban_lst_c": mean(lst, urban),
            "rural_lst_c": mean(lst, rural),
            "day_suhi_landsat_c": mean(lst, urban) - mean(lst, rural),
            "core_ndvi": mean(ndvi, core),
            "rural_ndvi": mean(ndvi, rural),
            "core_green_cover_pct": 100 * float((green & valid_core).sum() / valid_core.sum()),
            "lst_green_c": mean(lst, valid_core & green),
            "lst_nongreen_c": mean(lst, valid_core & ~green),
            "green_cooling_c": mean(lst, valid_core & ~green) - mean(lst, valid_core & green),
            "lst_per_0.1ndvi_c": slope.slope * 0.1,
            "ndvi_lst_r": slope.rvalue,
            "hotspot_pct": 100 * float((utfvi > 0.02).sum() / valid_core.sum()),
            "night_urban_c": mean(nd, m_urban),
            "night_rural_c": mean(nd, m_rural),
            "night_suhi_modis_c": mean(nd, m_urban) - mean(nd, m_rural),
            "day_suhi_modis_c": mean(dd, m_urban) - mean(dd, m_rural),
        })
    return pd.DataFrame(rows).round(3)


# ---------------------------------------------------------------- C
def grid_panel(ds, wc):
    """Aggregate 60 m pixels to ~1 km cells inside the core city."""
    f = round(cfg.GRID_KM * 1000 / cfg.RES)  # 17 px * 60 m = 1.02 km
    core, _, _ = zones(ds, wc)
    lst = ds.lst_c.where(core)
    green = (ds.ndvi > cfg.GREEN_NDVI).where(core & ds.ndvi.notnull())
    built = (wc == WC_BUILT).where(core).astype(float)
    cropland = (wc == 40).where(core).astype(float)
    cov = core.astype(float)
    agg = lambda a: a.coarsen(x=f, y=f, boundary="trim").mean()
    g = xr.Dataset({"lst": agg(lst), "green": agg(green) * 100, "ndvi": agg(ds.ndvi.where(core)),
                    "built": agg(built.where(core)) * 100,
                    "cropland": agg(cropland.where(core)) * 100, "cov": agg(cov)})
    df = g.to_dataframe().reset_index()
    df = df[df["cov"] > 0.9].dropna()  # cells (almost) fully inside the core and cloud-free
    df["cell"] = df.x.astype(int).astype(str) + "_" + df.y.astype(int).astype(str)
    n_years = df.groupby("cell").year.transform("count")
    return df[n_years == len(cfg.YEARS)].copy()  # balanced panel


def panel_models(p):
    out = {}
    # Two-way FE: cell effects absorb permanent geography (elevation, lakes, density);
    # year effects absorb city-wide weather (e.g. the 2024 drought). Identification comes from
    # cells whose green cover changed MORE or LESS than the city average.
    fe = smf.ols("lst ~ green + C(cell) + C(year)", data=p).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(p["cell"])[0]})
    out["twfe"] = {"coef_lst_per_10pp_green": 10 * fe.params["green"],
                   "se": 10 * fe.bse["green"], "p": fe.pvalues["green"],
                   "ci95": [10 * v for v in fe.conf_int().loc["green"]],
                   "n_cells": p.cell.nunique(), "n_obs": int(fe.nobs)}
    # Pooled cross-section for comparison (confounded by geography - shown to motivate FE)
    pooled = smf.ols("lst ~ green + C(year)", data=p).fit(cov_type="HC1")
    out["pooled"] = {"coef_lst_per_10pp_green": 10 * pooled.params["green"],
                     "se": 10 * pooled.bse["green"], "r2": pooled.rsquared}

    # Long difference: average 2022-23 vs 2025-26 to damp single-year noise.
    # LST is expressed relative to the city mean that period (removes weather).
    p = p.copy()
    p["lst_rel"] = p.lst - p.groupby("year").lst.transform("mean")
    early = p[p.year.isin([2022, 2023])].groupby("cell")[["lst_rel", "green", "built"]].mean()
    late = p[p.year.isin([2025, 2026])].groupby("cell")[["lst_rel", "green"]].mean()
    ld = (late - early[["lst_rel", "green"]]).add_prefix("d_").join(early[["built"]])
    m = smf.ols("d_lst_rel ~ d_green", data=ld).fit(cov_type="HC1")
    out["long_diff"] = {"coef_lst_per_10pp_green": 10 * m.params["d_green"],
                        "se": 10 * m.bse["d_green"], "p": m.pvalues["d_green"], "r2": m.rsquared,
                        "n_cells": len(ld)}
    # Who lost green? Quartiles of green change
    ld["green_change_group"] = pd.qcut(ld.d_green, 4, labels=["Largest loss", "Q2", "Q3", "Gain / least loss"])
    out["quartiles"] = (ld.groupby("green_change_group", observed=True)
                        .agg(d_green_pp=("d_green", "mean"), d_lst_rel_c=("d_lst_rel", "mean"),
                             cells=("d_green", "size")).round(2).reset_index().to_dict("records"))
    out["cells_losing_green_pct"] = 100 * float((ld.d_green < -2).mean())
    out["cells_gaining_green_pct"] = 100 * float((ld.d_green > 2).mean())
    # Robustness: peri-urban cropland greens/browns with rainfall, not development.
    # Re-estimate on dense urban cells only.
    out["robustness"] = {}
    for name, sub in {"cropland_lt_10pct": p[p.cropland < 10], "built_gt_50pct": p[p.built > 50]}.items():
        r = smf.ols("lst ~ green + C(cell) + C(year)", data=sub).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(sub["cell"])[0]})
        out["robustness"][name] = {"coef_lst_per_10pp_green": 10 * r.params["green"],
                                   "se": 10 * r.bse["green"], "n_cells": sub.cell.nunique()}
    return out, ld


def main():
    cfg.OUT.mkdir(exist_ok=True)
    ds, wc, md = load()
    y = yearly(ds, wc, md)
    y.to_csv(cfg.OUT / "yearly_metrics.csv", index=False)
    print(y.T.to_string())

    p = grid_panel(ds, wc)
    p.to_csv(cfg.OUT / "grid_panel.csv", index=False)
    res, ld = panel_models(p)
    ld.to_csv(cfg.OUT / "grid_long_difference.csv")

    first, last = y.iloc[0], y.iloc[-1]
    res["headline"] = {
        "core_lst_change_c": last.core_lst_c - first.core_lst_c,
        "core_green_cover_change_pp": last.core_green_cover_pct - first.core_green_cover_pct,
        "night_suhi_mean_c": float(y.night_suhi_modis_c.mean()),
        "day_suhi_landsat_mean_c": float(y.day_suhi_landsat_c.mean()),
        "green_cooling_mean_c": float(y.green_cooling_c.mean()),
        "lst_trend_c_per_yr": float(stats.linregress(y.year, y.core_lst_c).slope),
        "lst_trend_p": float(stats.linregress(y.year, y.core_lst_c).pvalue),
    }
    (cfg.OUT / "results.json").write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps(res, indent=2, default=float))


if __name__ == "__main__":
    main()
