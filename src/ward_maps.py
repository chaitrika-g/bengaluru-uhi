"""Step 5b - Ward maps.

  outputs/maps/ward_explorer.html   interactive choropleth (Plotly SVG geo: no WebGL, no map tiles,
                                    works offline and on GitHub Pages):
                                    layer switcher, hover details, top-10 heat-island wards outlined
  outputs/figures/fig5_ward_maps.png static version for the README
"""
import json

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

import config as cfg
from figures import BLUE, INK, INK2, MID, MUTED, RED, SURF  # shared palette + rcParams

HEAT = [[0, "#fdeee6"], [0.25, "#f6b896"], [0.5, "#eb6834"], [0.75, "#b8461c"], [1, "#6e2508"]]
GREEN = [[0, "#f3f1ea"], [0.5, "#7fc97f"], [1, "#006400"]]
DIV_WARM_BAD = [[0, BLUE], [0.5, MID], [1, RED]]   # positive = hotter = red
DIV_LOSS_BAD = [[0, RED], [0.5, MID], [1, BLUE]]   # negative = green loss = red

LAYERS = [  # column, title, colorscale, symmetric-around-zero, unit
    ("mean_lst_c_late", "Summer surface temperature, 2025–26 (°C)", HEAT, False, "°C"),
    ("lst_rel_late", "Hotter (+) or cooler (−) than city average, summer 2025–26", DIV_WARM_BAD, True, "°C"),
    ("green_cover_pct_late", "Green cover, summer 2025–26 (%)", GREEN, False, "%"),
    ("d_green_cover_pct", "Change in green cover, 2022–23 → 2025–26 (pp)", DIV_LOSS_BAD, True, "pp"),
    ("d_lst_rel", "Relative warming, 2022–23 → 2025–26 (°C)", DIV_WARM_BAD, True, "°C"),
    ("night_lst_c_late", "Night surface temperature, summer 2025–26 (°C, MODIS 1 km)", HEAT, False, "°C"),
]


def load():
    wards = gpd.read_file(cfg.DATA / "wards_web.geojson")[["ward_id", "geometry"]]
    ch = pd.read_csv(cfg.OUT / "ward_change_2022_2026.csv")
    top = pd.read_csv(cfg.OUT / "top10_heat_wards.csv")
    return wards.merge(ch, on="ward_id"), top


def interactive(g, top):
    gj = json.loads(g[["ward_id", "geometry"]].to_json())
    for f in gj["features"]:
        f["id"] = f["properties"]["ward_id"]
    hover = ("<b>%{customdata[0]}</b> (ward %{location})<br>%{customdata[1]}<br>"
             "Summer LST 2025–26: %{customdata[2]:.1f} °C (%{customdata[3]:+.1f} vs city)<br>"
             "Green cover: %{customdata[4]:.0f}% (%{customdata[5]:+.1f} pp since 2022–23)<br>"
             "SC/ST share: %{customdata[6]:.0f}%<extra></extra>")
    cd = g[["ward_name", "assembly_constituency", "mean_lst_c_late", "lst_rel_late",
            "green_cover_pct_late", "d_green_cover_pct", "sc_st_share_pct"]].values
    fig = go.Figure()
    for i, (col, title, cs, sym, unit) in enumerate(LAYERS):
        v = g[col]
        lim = float(np.nanpercentile(v.abs(), 98)) if sym else None
        fig.add_trace(go.Choropleth(
            geojson=gj, locations=g.ward_id, z=v, colorscale=cs,
            zmin=-lim if sym else float(np.nanpercentile(v, 2)), zmax=lim if sym else float(np.nanpercentile(v, 98)),
            marker_line_width=0.4, marker_line_color="#ffffff", marker_opacity=0.85,
            customdata=cd, hovertemplate=hover, visible=(i == 0), name=title,
            colorbar=dict(title=dict(text=unit), thickness=12, len=0.6)))
    tg = g[g.ward_id.isin(top.ward_id)]
    fig.add_trace(go.Choropleth(  # top-10 outline
        geojson=gj, locations=tg.ward_id, z=np.zeros(len(tg)), showscale=False,
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        marker_line_width=2.5, marker_line_color=INK, hoverinfo="skip", name="Top 10 heat wards"))
    tg = tg.set_index("ward_id").loc[top.ward_id].reset_index()  # keep rank order
    c = tg.to_crs(cfg.EPSG).representative_point().to_crs(4326)
    fig.add_trace(go.Scattergeo(lat=c.y, lon=c.x, mode="markers+text", text=[str(i) for i in range(1, 11)],
                                marker=dict(size=15, color="#ffffff", line=dict(width=1.5, color=INK)),
                                textfont=dict(size=9, color=INK), hoverinfo="skip", name="rank"))
    key = "<b>10 hottest wards</b> (vs city avg, summer 2025–26)<br>" + "<br>".join(
        f"{i}. {r.ward_name}  +{r.lst_rel_late:.1f} °C" for i, r in enumerate(top.itertuples(), 1))
    n = len(LAYERS)
    buttons = [dict(label=t.split(",")[0].split("(")[0].strip()[:38], method="update",
                    args=[{"visible": [j == i for j in range(n)] + [True, True]}, {"title.text": t}])
               for i, (_, t, *_r) in enumerate(LAYERS)]
    fig.update_layout(
        title=dict(text=LAYERS[0][1], x=0.01, font=dict(size=16)),
        geo=dict(fitbounds="locations", visible=False, projection_type="mercator", bgcolor=SURF),
        height=760,
        updatemenus=[dict(buttons=buttons, direction="down", x=0.01, y=0.99, xanchor="left", yanchor="top",
                          bgcolor="#ffffff", bordercolor="#cccccc")],
        margin=dict(l=0, r=0, t=48, b=28), showlegend=False, paper_bgcolor=SURF,
        annotations=[dict(text=key, x=0.01, y=0.9, xref="paper", yref="paper", showarrow=False, align="left",
                          xanchor="left", yanchor="top", font=dict(size=11, color=INK),
                          bgcolor="rgba(255,255,255,0.85)", bordercolor="#dddddd", borderpad=6),
                     dict(text="Bold outline = 10 hottest wards relative to city average (summer 2025–26). "
                               "Sources: Landsat 8/9, Sentinel-2, MODIS via Microsoft Planetary Computer; "
                               "BBMP 225-ward boundaries via OpenCity.",
                          x=0.01, y=0.005, xref="paper", yref="paper", showarrow=False,
                          font=dict(size=10, color=MUTED), xanchor="left", bgcolor="rgba(255,255,255,0.8)")])
    out = cfg.OUT / "maps"
    out.mkdir(exist_ok=True)
    fig.write_html(out / "ward_explorer.html", include_plotlyjs="cdn", full_html=True,
                   config={"scrollZoom": True, "displaylogo": False})


def static(g, top):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    heat = LinearSegmentedColormap.from_list("h", [c for _, c in DIV_WARM_BAD])
    loss = LinearSegmentedColormap.from_list("l", [c for _, c in DIV_LOSS_BAD])
    a = float(np.nanpercentile(g.lst_rel_late.abs(), 98))
    b = float(np.nanpercentile(g.d_green_cover_pct.abs(), 98))
    for ax, col, cmap, lim, title, lab in [
        (axes[0], "lst_rel_late", heat, a, "Summer heat vs city average, 2025–26", "°C"),
        (axes[1], "d_green_cover_pct", loss, b, "Green cover change, 2022–23 → 2025–26", "percentage points")]:
        g.plot(col, ax=ax, cmap=cmap, norm=TwoSlopeNorm(0, -lim, lim), edgecolor="white", linewidth=0.3,
               legend=True, legend_kwds={"shrink": 0.6, "label": lab}, missing_kwds={"color": "#dddddd"})
        g[g.ward_id.isin(top.ward_id)].boundary.plot(ax=ax, color=INK, linewidth=1.6)
        ax.set_title(title)
        ax.set_axis_off()
    fig.suptitle("225 BBMP wards: where it is hottest, and where the green went", x=0.02, ha="left",
                 fontweight="bold", fontsize=13)
    fig.text(0.02, 0.02, "Black outline: 10 hottest wards relative to the city average. Landsat 8/9 (LST), Sentinel-2 (NDVI > 0.4 = green).",
             color=MUTED, fontsize=8)
    fig.savefig(cfg.FIG / "fig5_ward_maps.png")


def main():
    g, top = load()
    interactive(g, top)
    static(g, top)
    print("wrote outputs/maps/ward_explorer.html and outputs/figures/fig5_ward_maps.png")


if __name__ == "__main__":
    main()
