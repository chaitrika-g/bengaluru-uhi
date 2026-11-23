"""Build per-year summer composites of Land Surface Temperature (LST) and NDVI from Landsat 8/9.

Source: USGS Landsat Collection 2 Level-2 (surface reflectance + surface temperature),
served free and without an account by Microsoft Planetary Computer.

Output: data/composites.nc with dims (year, y, x) and variables lst_c, ndvi, n_obs,
and data/worldcover.nc (ESA WorldCover 2021, used as a fixed land-cover mask).
"""
import numpy as np
import planetary_computer as pc
import pystac_client
import stackstac
import xarray as xr
from pyproj import Transformer

import config as C

# Collection 2 Level-2 scale factors (USGS)
SR_SCALE, SR_OFFSET = 0.0000275, -0.2
ST_SCALE, ST_OFFSET = 0.00341802, 149.0  # -> Kelvin

# QA_PIXEL bits to reject: 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow
QA_REJECT = sum(1 << b for b in (0, 1, 2, 3, 4))


def utm_bounds():
    t = Transformer.from_crs(4326, C.EPSG, always_xy=True)
    x0, y0 = t.transform(C.BBOX[0], C.BBOX[1])
    x1, y1 = t.transform(C.BBOX[2], C.BBOX[3])
    snap = lambda v, f: f(v / C.RES) * C.RES
    return (snap(x0, np.floor), snap(y0, np.floor), snap(x1, np.ceil), snap(y1, np.ceil))


def catalog():
    return pystac_client.Client.open(C.STAC_URL, modifier=pc.sign_inplace)


def year_composite(cat, year, bounds):
    items = list(cat.search(
        collections=["landsat-c2-l2"], bbox=C.BBOX,
        datetime=f"{year}-{C.SEASON[0]}/{year}-{C.SEASON[1]}",
        query={"eo:cloud_cover": {"lt": C.MAX_SCENE_CLOUD},
               "platform": {"in": ["landsat-8", "landsat-9"]}},
    ).items())
    print(f"{year}: {len(items)} scenes")
    stack = stackstac.stack(
        items, assets=["red", "nir08", "lwir11", "qa_pixel"], epsg=C.EPSG,
        resolution=C.RES, bounds=bounds, rescale=False, fill_value=np.uint16(0),
        dtype="uint16", resampling=__import__("rasterio").enums.Resampling.nearest,
    ).compute()
    qa = stack.sel(band="qa_pixel")
    st = stack.sel(band="lwir11")
    clear = ((qa & QA_REJECT) == 0) & (qa > 0) & (st > 0)

    red = stack.sel(band="red").astype("float32") * SR_SCALE + SR_OFFSET
    nir = stack.sel(band="nir08").astype("float32") * SR_SCALE + SR_OFFSET
    lst = st.astype("float32") * ST_SCALE + ST_OFFSET - 273.15
    ndvi = (nir - red) / (nir + red)

    lst = lst.where(clear & (lst > 5) & (lst < 75))
    ndvi = ndvi.where(clear & ndvi.notnull() & (abs(ndvi) <= 1))

    out = xr.Dataset({
        "lst_c": lst.median("time", skipna=True).reset_coords(drop=True),
        "ndvi": ndvi.median("time", skipna=True).reset_coords(drop=True),
        "n_obs": clear.sum("time").astype("int16").reset_coords(drop=True),
    })
    out = out.drop_vars([v for v in out.coords if v not in ("x", "y")])
    out["scenes"] = len(items)
    return out.expand_dims(year=[year])


def worldcover(cat, bounds):
    """ESA WorldCover 2021 (10 m), mode-resampled to the analysis grid. Used as a FIXED mask."""
    items = list(cat.search(collections=["esa-worldcover"], bbox=C.BBOX).items())
    items = [i for i in items if "2021" in i.id] or items
    import rasterio
    wc = stackstac.stack(items, assets=["map"], epsg=C.EPSG, resolution=C.RES, bounds=bounds,
                         rescale=False, fill_value=np.uint8(0), dtype="uint8",
                         resampling=rasterio.enums.Resampling.mode).max("time").squeeze().compute()
    return wc.drop_vars([v for v in wc.coords if v not in ("x", "y")]).rename("landcover")


def main():
    C.DATA.mkdir(exist_ok=True)
    cat, bounds = catalog(), utm_bounds()
    ds = xr.concat([year_composite(cat, y, bounds) for y in C.YEARS], dim="year")
    for v in ds.variables:
        ds[v].attrs = {}
    ds.to_netcdf(C.DATA / "composites.nc")
    wc = worldcover(cat, bounds)
    wc.attrs = {}
    for v in wc.coords:
        wc[v].attrs = {}
    wc.to_netcdf(C.DATA / "worldcover.nc")
    print(ds)


if __name__ == "__main__":
    main()
