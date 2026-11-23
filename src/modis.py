"""Night-time and daytime LST from MODIS (Terra MOD11A2 + Aqua MYD11A2, 8-day, 1 km), Mar-May each year.

Why: Landsat only passes over at ~10:30 am. Urban heat islands are typically strongest at NIGHT,
when concrete and asphalt release stored heat - this is the heat residents actually feel as
"nights that never cool down". MODIS gives ~1:30 am / 10:30 pm overpasses.

Output: data/modis.nc with dims (year, y, x), variables lst_day_c, lst_night_c.
"""
import numpy as np
import planetary_computer as pc
import pystac_client
import rasterio
import stackstac
import xarray as xr

import config as C
from composites import utm_bounds

SCALE = 0.02  # Kelvin per DN
RES = 1000


def season(cat, year, bounds):
    items = list(cat.search(collections=["modis-11A2-061"], bbox=C.BBOX,
                            datetime=f"{year}-{C.SEASON[0]}/{year}-{C.SEASON[1]}").items())
    stack = stackstac.stack(items, assets=["LST_Day_1km", "LST_Night_1km"], epsg=C.EPSG,
                            resolution=RES, bounds=bounds, rescale=False,
                            fill_value=np.uint16(0), dtype="uint16",
                            resampling=rasterio.enums.Resampling.bilinear).compute()
    k = stack.astype("float32").where(stack > 7500) * SCALE - 273.15  # 7500 DN = 150 K, valid min
    out = xr.Dataset({
        "lst_day_c": k.sel(band="LST_Day_1km").mean("time", skipna=True).reset_coords(drop=True),
        "lst_night_c": k.sel(band="LST_Night_1km").mean("time", skipna=True).reset_coords(drop=True),
    })
    print(f"{year}: {len(items)} MODIS 8-day composites")
    return out.expand_dims(year=[year])


def main():
    cat = pystac_client.Client.open(C.STAC_URL, modifier=pc.sign_inplace)
    b = utm_bounds()
    b = tuple(np.floor(v / RES) * RES if i < 2 else np.ceil(v / RES) * RES for i, v in enumerate(b))
    ds = xr.concat([season(cat, y, b) for y in C.YEARS], dim="year")
    for v in ds.variables:
        ds[v].attrs = {}
    ds.to_netcdf(C.DATA / "modis.nc")
    print(ds)


if __name__ == "__main__":
    main()
