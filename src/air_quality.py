"""Step 3 - Air quality: station PM2.5 -> seasonal means -> IDW estimate per ward centroid.

Sources (first one available wins):
  1. data/raw/air_quality.csv  - e.g. a CPCB CCR export, columns: station, lat, lon, date, pm25
  2. OpenAQ v3 API              - key given at RUNTIME only: OPENAQ_API_KEY env var for the run,
                                  or a hidden prompt (free key: https://explore.openaq.org/register)
If neither is available the step is skipped and the panel is built without PM2.5.

Caveat (also in docs/methodology.md): Bengaluru has roughly a dozen regulatory monitors for 225
wards. IDW produces a smooth surface; between-station variation is not observed. The output
carries the distance to the nearest station and a leave-one-out cross-validation error so that
downstream users can see how uncertain each estimate is.
"""
import getpass
import logging
import os
import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

import config as cfg

log = logging.getLogger("air_quality")
OPENAQ = "https://api.openaq.org/v3"
PM25_PARAMETER_ID = 2
LOCAL_CSV = cfg.DATA / "raw" / "air_quality.csv"
IDW_POWER = 2
MIN_DAYS_PER_SEASON = 20  # a station-season needs >= 20 valid daily means


# ---------------------------------------------------------------- ingestion
def _get(session, path, params, tries=4):
    for i in range(tries):
        r = session.get(f"{OPENAQ}{path}", params=params, timeout=60)
        if r.status_code == 429:  # rate limited: 60 req/min on the free tier
            wait = int(r.headers.get("x-ratelimit-reset", 30))
            log.warning("Rate limited; sleeping %ss", wait)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"OpenAQ request kept failing: {path}")


def from_openaq(api_key) -> pd.DataFrame:
    s = requests.Session()
    s.headers["X-API-Key"] = api_key  # never logged
    lon, lat = cfg.CENTER
    locs = _get(s, "/locations", {"coordinates": f"{lat},{lon}", "radius": 25000,
                                  "parameters_id": PM25_PARAMETER_ID, "limit": 1000})["results"]
    log.info("OpenAQ: %d PM2.5 locations within 25 km", len(locs))
    rows = []
    for loc in locs:
        for sensor in loc.get("sensors", []):
            if sensor["parameter"]["id"] != PM25_PARAMETER_ID:
                continue
            page = 1
            while True:
                res = _get(s, f"/sensors/{sensor['id']}/days",
                           {"datetime_from": f"{cfg.YEARS[0]}-01-01",
                            "datetime_to": f"{cfg.YEARS[-1]}-06-01", "limit": 1000, "page": page})["results"]
                rows += [{"station": loc["name"], "lat": loc["coordinates"]["latitude"],
                          "lon": loc["coordinates"]["longitude"],
                          "date": d["period"]["datetimeFrom"]["utc"][:10], "pm25": d["value"]}
                         for d in res]
                if len(res) < 1000:
                    break
                page += 1
    return pd.DataFrame(rows)


def runtime_api_key() -> str | None:
    """OpenAQ key, supplied at RUNTIME only - never read from or written to any file.

    1. OPENAQ_API_KEY in the environment of this process, e.g. for a single command:
           OPENAQ_API_KEY=<your-key> python air_quality.py
    2. Otherwise, if running in a terminal, a hidden prompt (input is not echoed; Enter skips).
    The key lives only in memory for this run. It is never logged, saved, or put in a URL.
    """
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if key:
        log.info("Using OpenAQ key from the runtime environment")
        return key
    if sys.stdin.isatty():
        try:
            key = getpass.getpass("OpenAQ API key (hidden; press Enter to skip air quality): ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl-D / Ctrl-C: skip, don't crash the pipeline
            print()
            return None
        return key or None
    return None


def load_readings() -> pd.DataFrame | None:
    if LOCAL_CSV.exists():
        log.info("Using local file %s", LOCAL_CSV)
        df = pd.read_csv(LOCAL_CSV)
    elif key := runtime_api_key():
        df = from_openaq(key)
        del key
    else:
        log.warning("No air-quality source (no %s, no OpenAQ key given at runtime) - skipping step",
                    LOCAL_CSV.name)
        return None
    missing = {"station", "lat", "lon", "date", "pm25"} - set(df.columns)
    if missing:
        raise ValueError(f"Air-quality data missing columns: {missing}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    n0 = len(df)
    df = df[df.date.notna() & df.pm25.between(0, 999)]  # drop sentinel / impossible values
    log.info("Readings: %d kept of %d, %d stations", len(df), n0, df.station.nunique())
    return df


def seasonal_station_means(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(year=df.date.dt.year, md=df.date.dt.strftime("%m-%d"))
    df["season"] = None
    for name, (s0, s1) in cfg.SEASONS.items():
        df.loc[(df.md >= s0) & (df.md <= s1), "season"] = name
    df = df[df.season.notna() & df.year.isin(cfg.YEARS)]
    g = (df.groupby(["station", "year", "season"])
           .agg(lat=("lat", "first"), lon=("lon", "first"), pm25=("pm25", "mean"), days=("date", "nunique"))
           .reset_index())
    return g[g.days >= MIN_DAYS_PER_SEASON]


# ---------------------------------------------------------------- interpolation
def idw(xy_known, values, xy_target, power=IDW_POWER):
    d = np.linalg.norm(xy_target[:, None, :] - xy_known[None, :, :], axis=2)
    d = np.maximum(d, 1.0)  # a station inside a ward centroid: avoid divide-by-zero
    w = 1 / d ** power
    return (w * values).sum(1) / w.sum(1), d.min(1)


def loo_rmse(xy, v):
    """Leave-one-out cross-validation: predict each station from the others."""
    if len(v) < 3:
        return np.nan
    errs = [idw(np.delete(xy, i, 0), np.delete(v, i), xy[i:i + 1])[0][0] - v[i] for i in range(len(v))]
    return float(np.sqrt(np.mean(np.square(errs))))


def main():
    df = load_readings()
    if df is None:
        return
    st = seasonal_station_means(df)
    wards = gpd.read_parquet(cfg.DATA / "wards.parquet").to_crs(cfg.EPSG)
    cent = np.c_[wards.representative_point().x, wards.representative_point().y]

    # Robustness: a FIXED station set = stations reporting in every period that has data.
    # With a changing network, interpolated values can shift just because stations come and go.
    n_periods = st.groupby(["year", "season"]).ngroups
    per_station = st.groupby("station").size()
    fixed = set(per_station[per_station == n_periods].index)
    log.info("Stations: %d total, %d report in all %d periods (fixed set)", len(per_station), len(fixed), n_periods)
    if len(fixed) < 3:
        log.warning("Fewer than 3 stations in every period - fixed-set estimates will be empty")

    out, diag = [], []
    for (year, season), g in st.groupby(["year", "season"]):
        def interp(sub):
            pts = gpd.GeoSeries(gpd.points_from_xy(sub.lon, sub.lat), crs=4326).to_crs(cfg.EPSG)
            xy = np.c_[pts.x, pts.y]
            est, dmin = idw(xy, sub.pm25.values, cent)
            return est, dmin, loo_rmse(xy, sub.pm25.values)

        est, dmin, rmse = interp(g)
        gf = g[g.station.isin(fixed)]
        est_f = interp(gf)[0] if len(gf) >= 3 else np.full(len(cent), np.nan)
        log.info("%d %s: %d stations, LOO-CV RMSE %.1f ug/m3", year, season, len(g), rmse)
        out.append(pd.DataFrame({"ward_id": wards.ward_id, "year": year, "season": season,
                                 "est_pm25": est, "est_pm25_fixed": est_f,
                                 "nearest_station_km": dmin / 1000,
                                 "n_stations": len(g), "idw_loo_rmse": rmse}))
        diag.append({"year": year, "season": season, "stations": len(g), "fixed_set_stations": len(gf),
                     "station_mean_pm25": g.pm25.mean(), "loo_cv_rmse": rmse,
                     "median_ward_km_to_station": float(np.median(dmin) / 1000),
                     "wards_within_3km_pct": float(100 * np.mean(dmin < 3000))})
    if not out:
        log.warning("No station-season met the coverage threshold; nothing written")
        return
    pd.concat(out).to_parquet(cfg.DATA / "ward_pm25.parquet", index=False)
    st.to_csv(cfg.OUT / "aq_station_seasonal_means.csv", index=False)
    d = pd.DataFrame(diag).round(2)
    d.to_csv(cfg.OUT / "aq_diagnostics.csv", index=False)
    print("\nAir-quality diagnostics per period:\n", d.to_string(index=False))
    log.info("Wrote ward_pm25.parquet and outputs/aq_diagnostics.csv")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    main()
