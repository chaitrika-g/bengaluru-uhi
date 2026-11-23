"""Publication figures -> outputs/figures/*.png"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

import config as cfg
from analysis import load, zones

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
BLUE, ORANGE, RED, MID = "#2a78d6", "#eb6834", "#e34948", "#f0efec"
HEAT = LinearSegmentedColormap.from_list("heat", ["#fdeee6", "#f6b896", "#eb6834", "#b8461c", "#6e2508"])
DIVERGE = LinearSegmentedColormap.from_list("div", [BLUE, MID, RED])
DIVERGE_R = LinearSegmentedColormap.from_list("div_r", [RED, MID, BLUE])

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titlecolor": INK, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "figure.facecolor": SURF,
    "axes.facecolor": SURF, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def crop(da, km=cfg.CORE_RADIUS_KM + 2):
    from pyproj import Transformer
    cx, cy = Transformer.from_crs(4326, cfg.EPSG, always_xy=True).transform(*cfg.CENTER)
    return da.sel(x=slice(cx - km * 1e3, cx + km * 1e3), y=slice(cy + km * 1e3, cy - km * 1e3))


def km_extent(da):
    from pyproj import Transformer
    cx, cy = Transformer.from_crs(4326, cfg.EPSG, always_xy=True).transform(*cfg.CENTER)
    return [(da.x.min() - cx) / 1e3, (da.x.max() - cx) / 1e3, (da.y.min() - cy) / 1e3, (da.y.max() - cy) / 1e3]


def map_axes(ax):
    ax.grid(False)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    circle = plt.Circle((0, 0), cfg.CORE_RADIUS_KM, fill=False, ls="--", lw=0.8, color=INK2)
    ax.add_patch(circle)


def fig_lst_maps(ds, wc):
    core, _, _ = zones(ds, wc)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1, 1, 1]})
    a, b = crop(ds.lst_c.sel(year=2022)), crop(ds.lst_c.sel(year=2026))
    vmin, vmax = np.nanpercentile(np.r_[a.values.ravel(), b.values.ravel()], [2, 98])
    for ax, da, yr in [(axes[0], a, 2022), (axes[1], b, 2026)]:
        im = ax.imshow(da, cmap=HEAT, vmin=vmin, vmax=vmax, extent=km_extent(da))
        ax.set_title(f"Summer {yr}")
        map_axes(ax)
    fig.colorbar(im, ax=axes[:2], shrink=0.8, label="Land surface temperature, daytime (°C)")
    # Relative change: each pixel vs its year's core mean, removes city-wide weather
    rel = lambda y: ds.lst_c.sel(year=y) - float(ds.lst_c.sel(year=y).where(core).mean())
    d = crop(rel(2026) - rel(2022)).where(crop(wc) != 80)
    im2 = axes[2].imshow(d, cmap=DIVERGE, norm=TwoSlopeNorm(0, -3, 3), extent=km_extent(d))
    axes[2].set_title("Relative change, 2022→26")
    map_axes(axes[2])
    fig.colorbar(im2, ax=axes[2], shrink=0.8, label="Change vs city average (°C)")
    fig.suptitle("Bengaluru got hotter, and unevenly so", x=0.02, ha="left", fontweight="bold", fontsize=13)
    fig.text(0.02, -0.02, "Daytime LST, Mar–May median of all cloud-free scenes. Dashed circle: 15 km 'core city' study zone. Source: Landsat 8/9 Collection 2 L2 (USGS) via Microsoft Planetary Computer.",
             color=MUTED, fontsize=8)
    fig.savefig(cfg.FIG / "fig1_lst_maps.png")


def fig_green_maps(ds, wc):
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6))
    g = lambda y: (crop(ds.ndvi.sel(year=y)) > cfg.GREEN_NDVI).astype(float)
    early = (g(2022) + g(2023)) / 2
    late = (g(2025) + g(2026)) / 2
    green_cmap = LinearSegmentedColormap.from_list("g", [SURF, "#7fc97f", "#006400"])
    im = axes[0].imshow(early.where(crop(wc) != 80), cmap=green_cmap, vmin=0, vmax=1, extent=km_extent(early))
    axes[0].set_title("Green cover, 2022–23 (NDVI > 0.4)")
    map_axes(axes[0])
    # Change at ~1 km resolution for legibility
    f = 17
    dchg = (late - early).coarsen(x=f, y=f, boundary="trim").mean() * 100
    im2 = axes[1].imshow(dchg, cmap=DIVERGE_R, norm=TwoSlopeNorm(0, -25, 25), extent=km_extent(dchg))
    axes[1].set_title("Change in green cover, → 2025–26")
    map_axes(axes[1])
    fig.colorbar(im2, ax=axes[1], shrink=0.8, label="Percentage points (~1 km cells)")
    fig.suptitle("Where the green went", x=0.02, ha="left", fontweight="bold", fontsize=13)
    fig.text(0.02, -0.02, "Two-year averages damp single-year rainfall effects. Red = loss, blue = gain.", color=MUTED, fontsize=8)
    fig.savefig(cfg.FIG / "fig2_green_change.png")


def fig_timeseries(y):
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    panels = [
        ("core_lst_c", "Daytime surface temp., core city (°C)", ORANGE),
        ("core_green_cover_pct", "Green cover, core city (%)", "#008300"),
        ("night_suhi_modis_c", "Night-time heat island (°C, urban − rural)", BLUE),
    ]
    for ax, (col, title, c) in zip(axes, panels):
        ax.plot(y.year, y[col], color=c, lw=2, marker="o", ms=8, mec=SURF, mew=2)
        for yr, v in zip(y.year, y[col]):
            if yr in (2022, 2024, 2026):
                ax.annotate(f"{v:.1f}", (yr, v), textcoords="offset points", xytext=(0, 9), ha="center", color=INK, fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.set_xticks(y.year)
        ax.margins(y=0.25)
    axes[0].axvspan(2023.6, 2024.4, color=GRID, alpha=0.6, lw=0)
    axes[0].text(2024, axes[0].get_ylim()[0], "2024\ndrought", ha="center", va="bottom", color=INK2, fontsize=8)
    fig.suptitle("Five summers, 2022–2026", x=0.02, ha="left", fontweight="bold", fontsize=13, y=1.04)
    fig.savefig(cfg.FIG / "fig3_timeseries.png")


def fig_scatter(ld, res):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axes[0]
    ax.scatter(ld.d_green, ld.d_lst_rel, s=14, color=BLUE, alpha=0.45, lw=0)
    b = res["long_diff"]["coef_lst_per_10pp_green"] / 10
    xs = np.linspace(ld.d_green.min(), ld.d_green.max(), 50)
    a = ld.d_lst_rel.mean() - b * ld.d_green.mean()
    ax.plot(xs, a + b * xs, color=INK, lw=2)
    ax.axhline(0, color=MUTED, lw=0.8); ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("Change in green cover (percentage points)")
    ax.set_ylabel("Relative change in surface temp. (°C)")
    ax.set_title(f"Each ~1 km cell (n={len(ld)}): lose 10 pp green → +{-b*10:.2f} °C")
    q = pd.DataFrame(res["quartiles"])
    ax2 = axes[1]
    colors = [RED if v > 0 else BLUE for v in q.d_lst_rel_c]
    bars = ax2.bar(range(4), q.d_lst_rel_c, color=colors, width=0.6)
    ax2.axhline(0, color=INK2, lw=0.8)
    ax2.set_xticks(range(4), [f"{g}\n({d:+.1f} pp)" for g, d in zip(q.green_change_group, q.d_green_pp)], fontsize=8)
    for i, v in enumerate(q.d_lst_rel_c):
        ax2.text(i, v + (0.04 if v >= 0 else -0.04), f"{v:+.2f} °C", ha="center", va="bottom" if v >= 0 else "top", fontsize=9, color=INK)
    ax2.set_title("Cells grouped by green-cover change")
    ax2.grid(axis="x", visible=False)
    ax2.margins(y=0.2)
    fig.suptitle("Neighbourhoods that lost the most greenery warmed the most", x=0.02, ha="left", fontweight="bold", fontsize=13, y=1.03)
    fig.text(0.02, -0.04, "Change from 2022–23 to 2025–26 average. Temperature is relative to each year's city mean, so city-wide weather is removed.",
             color=MUTED, fontsize=8)
    fig.savefig(cfg.FIG / "fig4_green_vs_heat.png")


def main():
    cfg.FIG.mkdir(parents=True, exist_ok=True)
    ds, wc, _ = load()
    y = pd.read_csv(cfg.OUT / "yearly_metrics.csv")
    ld = pd.read_csv(cfg.OUT / "grid_long_difference.csv")
    res = json.loads((cfg.OUT / "results.json").read_text())
    fig_lst_maps(ds, wc)
    fig_green_maps(ds, wc)
    fig_timeseries(y)
    fig_scatter(ld, res)
    print("figures written to", cfg.FIG)


if __name__ == "__main__":
    main()
