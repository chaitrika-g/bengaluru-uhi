"""Step 5a - Ward-level econometrics on the validated panel.

Models (all on in-sample ward-seasons, SE clustered by ward):
  M1  LST ~ NDVI          + ward FE + period FE      (period = year x season)
  M2  LST ~ green cover % + ward FE + period FE
  M3  LST ~ NDVI          + ward FE + year FE, summer only
  M4  LST ~ NDVI          + ward FE + year FE, winter only
  M5  LST ~ NDVI + PM2.5  + ward FE + period FE      (sensitivity only - see note)
  A1  PM2.5 ~ NDVI        + ward FE + period FE      (air quality as an OUTCOME)
Plus: long-difference ward change table, top-10 heat-island wards, equity correlations.

Why PM2.5 is not in the headline model: it does not plausibly drive surface temperature, it is
itself an outcome of urbanisation, and the IDW surface is smooth (largely absorbed by the fixed
effects). Including it risks a "bad control". It is reported as a sensitivity check and an outcome.
"""
import json
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

import config as cfg

log = logging.getLogger("ward_models")


def fe(formula, df, cluster="ward_id"):
    m = smf.ols(formula, data=df).fit(cov_type="cluster",
                                      cov_kwds={"groups": pd.factorize(df[cluster])[0]})
    return m


def summarise(m, var, scale, label, n_wards):
    lo, hi = m.conf_int().loc[var] * scale
    return {"model": label, "effect": m.params[var] * scale, "se": m.bse[var] * abs(scale),
            "ci95_low": min(lo, hi), "ci95_high": max(lo, hi), "p": m.pvalues[var],
            "n_obs": int(m.nobs), "n_wards": n_wards}


def models(p):
    out = []
    nw = p.ward_id.nunique()
    # scale = -0.1: report the effect of a 0.1 DROP in NDVI on LST
    out.append(summarise(fe("mean_lst_c ~ mean_ndvi + C(ward_id) + C(period)", p),
                         "mean_ndvi", -0.1, "M1 Two-way FE (all dry seasons): 0.1 NDVI drop -> °C", nw))
    out.append(summarise(fe("mean_lst_c ~ green_cover_pct + C(ward_id) + C(period)", p),
                         "green_cover_pct", -10, "M2 Two-way FE: 10 pp green-cover loss -> °C", nw))
    for s in cfg.SEASONS:
        q = p[p.season == s]
        out.append(summarise(fe("mean_lst_c ~ mean_ndvi + C(ward_id) + C(year)", q),
                             "mean_ndvi", -0.1, f"M3/4 {s} only: 0.1 NDVI drop -> °C", q.ward_id.nunique()))
    q = p[p.season == "summer"]
    out.append(summarise(fe("mean_lst_c ~ green_cover_pct + C(ward_id) + C(year)", q),
                         "green_cover_pct", -10, "M2s summer only: 10 pp green-cover loss -> °C", q.ward_id.nunique()))
    pooled = smf.ols("mean_lst_c ~ mean_ndvi + C(period)", data=p).fit(cov_type="HC1")
    out.append(summarise(pooled, "mean_ndvi", -0.1, "Pooled OLS, no ward FE (for comparison)", nw))

    aq = p.dropna(subset=["est_pm25"])
    if len(aq) > 50:
        out.append(summarise(fe("mean_lst_c ~ mean_ndvi + est_pm25 + C(ward_id) + C(period)", aq),
                             "mean_ndvi", -0.1, "M5 Sensitivity: + PM2.5 control", aq.ward_id.nunique()))
        out.append(summarise(fe("est_pm25 ~ mean_ndvi + C(ward_id) + C(period)", aq),
                             "mean_ndvi", -0.1, "A1 Air quality outcome: 0.1 NDVI drop -> ug/m3 PM2.5",
                             aq.ward_id.nunique()))
        # Robustness of A1
        if "est_pm25_fixed" in p and p.est_pm25_fixed.notna().sum() > 50:
            af = p.dropna(subset=["est_pm25_fixed"])
            out.append(summarise(fe("est_pm25_fixed ~ mean_ndvi + C(ward_id) + C(period)", af),
                                 "mean_ndvi", -0.1, "A2 Robustness: fixed station set only", af.ward_id.nunique()))
        near = aq[aq.nearest_station_km < 3]
        if near.ward_id.nunique() >= 20:
            out.append(summarise(fe("est_pm25 ~ mean_ndvi + C(ward_id) + C(period)", near),
                                 "mean_ndvi", -0.1, "A3 Robustness: wards within 3 km of a station",
                                 near.ward_id.nunique()))
        else:
            log.info("Fewer than 20 wards within 3 km of a station - skipping A3")
    else:
        log.info("PM2.5 not available - skipping M5 and A1-A3")
    return pd.DataFrame(out)


def placebo_a1(p, n_perm=200, seed=42):
    """Permutation (placebo) test for A1. Within each period, shuffle which station had which
    reading, re-interpolate to wards, re-run A1. Shuffling destroys any real station-greenery link,
    so the shuffled coefficients show what interpolation artefacts alone can produce.
    Returns the real coefficient's permutation p-value and the placebo distribution."""
    from air_quality import idw
    st_path = cfg.OUT / "aq_station_seasonal_means.csv"
    if not st_path.exists():
        return None
    st = pd.read_csv(st_path)
    wards = gpd.read_parquet(cfg.DATA / "wards.parquet").to_crs(cfg.EPSG)
    cent = np.c_[wards.representative_point().x, wards.representative_point().y]
    base = p.dropna(subset=["est_pm25"])[["ward_id", "year", "season", "period", "mean_ndvi"]]
    groups = []
    for (year, season), g in st.groupby(["year", "season"]):
        pts = gpd.GeoSeries(gpd.points_from_xy(g.lon, g.lat), crs=4326).to_crs(cfg.EPSG)
        groups.append((year, season, np.c_[pts.x, pts.y], g.pm25.values))

    def coef(df):
        m = smf.ols("pm ~ mean_ndvi + C(ward_id) + C(period)", data=df).fit()
        return -0.1 * m.params["mean_ndvi"]

    def surface(values_by_group):
        rows = [pd.DataFrame({"ward_id": wards.ward_id.values, "year": y, "season": s,
                              "pm": idw(xy, v, cent)[0]}) for (y, s, xy, _), v in zip(groups, values_by_group)]
        return base.merge(pd.concat(rows), on=["ward_id", "year", "season"])

    actual = coef(surface([v for *_, v in groups]))
    rng = np.random.default_rng(seed)
    placebo = np.array([coef(surface([rng.permutation(v) for *_, v in groups])) for _ in range(n_perm)])
    p_perm = (1 + np.sum(np.abs(placebo) >= abs(actual))) / (n_perm + 1)
    log.info("A1 placebo test: actual %.2f, placebo 95%% range [%.2f, %.2f], permutation p = %.3f",
             actual, *np.percentile(placebo, [2.5, 97.5]), p_perm)
    return {"actual_effect": actual, "permutation_p": p_perm, "n_permutations": n_perm,
            "placebo_p2_5": float(np.percentile(placebo, 2.5)),
            "placebo_p97_5": float(np.percentile(placebo, 97.5)),
            "placebo_abs_max": float(np.abs(placebo).max())}


def ward_change(p, wards):
    """Summer change: average of 2022-23 vs 2025-26. LST relative to the city mean that year."""
    s = p[p.season == "summer"].copy()
    s["lst_rel"] = s.mean_lst_c - s.groupby("year").mean_lst_c.transform("mean")
    early = s[s.year.isin([2022, 2023])].groupby("ward_id")[["lst_rel", "mean_lst_c", "mean_ndvi", "green_cover_pct", "night_lst_c"]].mean()
    late = s[s.year.isin([2025, 2026])].groupby("ward_id")[["lst_rel", "mean_lst_c", "mean_ndvi", "green_cover_pct", "night_lst_c"]].mean()
    ch = late.add_suffix("_late").join(early.add_suffix("_early"))
    for c in ["lst_rel", "mean_lst_c", "mean_ndvi", "green_cover_pct", "night_lst_c"]:
        ch[f"d_{c}"] = ch[f"{c}_late"] - ch[f"{c}_early"]
    attrs = wards.drop(columns="geometry").set_index("ward_id")[
        ["ward_name", "assembly_constituency", "population", "area_km2", "pop_density_per_km2", "sc_st_share_pct"]]
    return attrs.join(ch).reset_index()


def equity(ch):
    """Descriptive only. SC/ST share is used as a rough proxy for social disadvantage."""
    res = {}
    for x in ["sc_st_share_pct", "pop_density_per_km2"]:
        for y in ["lst_rel_late", "green_cover_pct_late", "d_green_cover_pct", "d_lst_rel"]:
            d = ch[[x, y]].dropna()
            r, pv = stats.spearmanr(d[x], d[y])
            res[f"{y} vs {x}"] = {"spearman_rho": r, "p": pv, "n": len(d)}
    q = ch.assign(sc_st_quartile=pd.qcut(ch.sc_st_share_pct, 4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"]))
    tab = (q.groupby("sc_st_quartile", observed=True)
            .agg(wards=("ward_id", "size"), sc_st_share_pct=("sc_st_share_pct", "mean"),
                 summer_lst_c=("mean_lst_c_late", "mean"), green_cover_pct=("green_cover_pct_late", "mean"),
                 d_green_cover_pp=("d_green_cover_pct", "mean"), d_lst_rel_c=("d_lst_rel", "mean"))
            .round(2).reset_index())
    return res, tab


def main():
    p_all = pd.read_parquet(cfg.OUT / "ward_panel.parquet")
    p = p_all[p_all.in_sample].copy()
    log.info("Panel: %d in-sample ward-seasons of %d (%d wards)", len(p), len(p_all), p.ward_id.nunique())
    wards = gpd.read_parquet(cfg.DATA / "wards.parquet")

    res = models(p)
    res.round(4).to_csv(cfg.OUT / "ward_model_results.csv", index=False)
    print(res.round(3).to_string(index=False))

    ch = ward_change(p_all, wards)
    ch.round(4).to_csv(cfg.OUT / "ward_change_2022_2026.csv", index=False)
    top = (ch.sort_values("lst_rel_late", ascending=False).head(10)
             [["ward_id", "ward_name", "assembly_constituency", "mean_lst_c_late", "lst_rel_late",
               "green_cover_pct_late", "d_green_cover_pct", "d_lst_rel"]].round(2))
    top.to_csv(cfg.OUT / "top10_heat_wards.csv", index=False)
    print("\nTop 10 heat-island wards (summer 2025-26):\n", top.to_string(index=False))

    eq, eq_tab = equity(ch)
    eq_tab.to_csv(cfg.OUT / "equity_by_scst_quartile.csv", index=False)
    print("\nBy SC/ST-share quartile:\n", eq_tab.to_string(index=False))

    s = p_all[p_all.season == "summer"].groupby("year").agg(
        lst=("mean_lst_c", "mean"), green=("green_cover_pct", "mean"), ndvi=("mean_ndvi", "mean"))
    placebo = placebo_a1(p) if p.est_pm25.notna().sum() > 50 else None
    if placebo:
        pd.DataFrame([placebo]).round(4).to_csv(cfg.OUT / "aq_placebo_test.csv", index=False)
        print("\nA1 placebo (permutation) test:\n", pd.DataFrame([placebo]).round(3).to_string(index=False))

    summary = {
        "panel": {"ward_seasons_total": len(p_all), "in_sample": len(p), "wards": int(p.ward_id.nunique())},
        "models": res.to_dict("records"),
        "city_summer_by_year": s.round(3).reset_index().to_dict("records"),
        "wards_losing_green_gt2pp_pct": float(100 * (ch.d_green_cover_pct < -2).mean()),
        "wards_gaining_green_gt2pp_pct": float(100 * (ch.d_green_cover_pct > 2).mean()),
        "longdiff_ward": {k: float(v) for k, v in zip(
            ["slope_c_per_10pp", "se"],
            (lambda m: (m.params["d_green_cover_pct"] * -10, m.bse["d_green_cover_pct"] * 10))(
                smf.ols("d_lst_rel ~ d_green_cover_pct", data=ch.dropna(subset=["d_lst_rel", "d_green_cover_pct"])).fit(cov_type="HC1")))},
        "equity_spearman": eq,
        "a1_placebo_test": placebo,
    }
    (cfg.OUT / "ward_results.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps({k: summary[k] for k in ["panel", "city_summer_by_year", "wards_losing_green_gt2pp_pct",
                                             "wards_gaining_green_gt2pp_pct", "longdiff_ward"]}, indent=1, default=float))
    print(json.dumps(eq, indent=1, default=float))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    main()
