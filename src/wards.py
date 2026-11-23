"""Step 1 - Spatial ingestion: BBMP ward boundaries (KML) -> validated GeoParquet + GeoJSON.

Input : data/raw/bbmp_wards_225.kml  (BBMP 225-ward delimitation, via OpenCity)
Output: data/wards.parquet          full-precision geometries + attributes (EPSG:4326)
        data/wards_web.geojson      simplified geometries for interactive maps

Validation (fails loudly rather than silently producing a bad panel):
  * expected ward count, unique ward ids, non-empty polygons
  * invalid geometries repaired with make_valid and logged
  * computed area (EPSG:32643, metric) reconciled against the file's own ward_area field
"""
import logging

import geopandas as gpd
import pandas as pd

import config as cfg

log = logging.getLogger("wards")
EXPECTED_WARDS = 225
KEEP = ["ward_id", "ward_name", "assembly_constituency", "population",
        "sc_population", "st_population", "ward_area_src_km2", "geometry"]


class WardValidationError(Exception):
    pass


def read_kml(path=cfg.WARDS_KML) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Ward boundary file not found: {path}")
    gdf = gpd.read_file(path)  # GDAL KML driver. Note: schema field "id" arrives as "id2"
    if "id2" not in gdf.columns:
        raise WardValidationError("Ward id field (SchemaData \"id\") not found in KML")
    log.info("Read %d features, %d columns from %s", len(gdf), gdf.shape[1], path.name)
    log.info("Schema: %s", ", ".join(f"{c}:{t}" for c, t in gdf.dtypes.astype(str).items()))
    return gdf


def standardise(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        log.warning("No CRS in file; KML is WGS84 by specification - assigning EPSG:4326")
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    gdf = gdf.drop(columns=["id"], errors="ignore").rename(columns={"id2": "ward_id", "name_en": "ward_name",
                              "assembly_constituency_name_en": "assembly_constituency",
                              "ward_area": "ward_area_src_km2"})
    gdf["ward_id"] = pd.to_numeric(gdf["ward_id"], errors="raise").astype(int)
    for c in ["population", "sc_population", "st_population", "ward_area_src_km2"]:
        gdf[c] = pd.to_numeric(gdf[c], errors="coerce")
    gdf.geometry = gdf.geometry.force_2d()
    return gdf[KEEP].sort_values("ward_id").reset_index(drop=True)


def validate(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if len(gdf) != EXPECTED_WARDS:
        raise WardValidationError(f"Expected {EXPECTED_WARDS} wards, found {len(gdf)}")
    dupes = gdf.ward_id[gdf.ward_id.duplicated()].tolist()
    if dupes:
        raise WardValidationError(f"Duplicate ward ids: {dupes}")
    if gdf.geometry.is_empty.any() or gdf.geometry.isna().any():
        raise WardValidationError("Empty or missing geometries present")

    invalid = ~gdf.geometry.is_valid
    if invalid.any():
        log.warning("Repairing %d invalid geometries: ward ids %s", invalid.sum(),
                    gdf.ward_id[invalid].tolist())
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid].geometry.make_valid()
    bad_types = ~gdf.geom_type.isin(["Polygon", "MultiPolygon"])
    if bad_types.any():  # make_valid can return GeometryCollections; keep polygonal parts
        gdf.loc[bad_types, "geometry"] = gdf.loc[bad_types].geometry.apply(
            lambda g: g.buffer(0))
        log.warning("Coerced %d non-polygon geometries", bad_types.sum())

    gdf["area_km2"] = gdf.to_crs(cfg.EPSG).area / 1e6
    diff = (gdf.area_km2 - gdf.ward_area_src_km2).abs() / gdf.ward_area_src_km2
    log.info("Area reconciliation vs source field: median diff %.2f%%, max %.2f%%",
             100 * diff.median(), 100 * diff.max())
    if diff.median() > 0.05:
        raise WardValidationError("Computed areas disagree with source ward_area by >5% (median)")
    gdf["pop_density_per_km2"] = gdf.population / gdf.area_km2
    gdf["sc_st_share_pct"] = 100 * (gdf.sc_population + gdf.st_population) / gdf.population

    total = gdf.to_crs(cfg.EPSG).union_all()
    log.info("Total city area %.0f km2, population %s, bounds %s",
             total.area / 1e6, f"{int(gdf.population.sum()):,}", gdf.total_bounds.round(3))
    return gdf


def main():
    gdf = validate(standardise(read_kml()))
    gdf.to_parquet(cfg.DATA / "wards.parquet")
    web = gdf.copy()
    web["geometry"] = web.to_crs(cfg.EPSG).simplify(25).to_crs(4326)  # ~25 m tolerance
    web.to_file(cfg.DATA / "wards_web.geojson", driver="GeoJSON")
    log.info("Wrote wards.parquet and wards_web.geojson (%d wards)", len(gdf))
    print(gdf.drop(columns="geometry").describe().round(1).T.to_string())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    main()
