"""Step 6 - Economics layer: who bears the heat, and what it would take to undo it.

Built ONLY from this project's own estimates (no external cost figures):

  1. Attributable heat: extra summer surface warming in each ward caused by its change in green cover
     since 2022-23, = green-cover loss (pp) x the summer fixed-effects coefficient (M2s, °C per pp).
     Weighted by population, it gives "person-°C": how much heat burden, borne by how many people.
  2. Distribution: who bears it, by population-density and SC/ST-share quartiles.
  3. Restoration requirement: for wards hotter than the city average, the green cover (pp, and
     hectares) needed to cool them back to the average, at the estimated cooling rate.

The coefficient's 95% CI is carried through every number (low / central / high).

Why no rupee figure: published damage functions (e.g. ~2% lower annual factory output per +1 °C,
Somanathan et al. 2021, JPE) are per degree of AIR temperature. This project measures SURFACE
temperature, and no established conversion exists for Indian cities. A rupee number would rest on an
invented conversion, so it is left as an explicit next step (see docs/economics_extension.md).
"""
import json
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
from figures import BLUE, GRID, INK, INK2, MUTED, RED, SURF  # shared palette + rcParams

log = logging.getLogger("economics")
MODEL = "M2s summer only: 10 pp green-cover loss -> °C"


def coefficient():
    """°C of summer surface warming per 1 pp of green cover lost: (central, low, high)."""
    m = pd.read_csv(cfg.OUT / "ward_model_results.csv").set_index("model")
    if MODEL not in m.index:
        raise RuntimeError(f"Model row '{MODEL}' not found - run ward_models.py first")
    r = m.loc[MODEL]
    return r.effect / 10, r.ci95_low / 10, r.ci95_high / 10


def attributable_heat(ch, b):
    """Positive = warming from green LOSS; negative = cooling from green GAIN."""
    out = ch.copy()
    for name, beta in zip(["", "_low", "_high"], b):
        out[f"attrib_heat_c{name}"] = -out.d_green_cover_pct * beta
        out[f"person_degc{name}"] = out[f"attrib_heat_c{name}"] * out.population
    return out


def distribution(e):
    rows = {}
    for col, label in [("pop_density_per_km2", "density"), ("sc_st_share_pct", "sc_st_share")]:
        q = pd.qcut(e[col], 4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"])
        t = (e.assign(q=q).groupby("q", observed=True)
               .apply(lambda g: pd.Series({
                   "wards": len(g),
                   "population": g.population.sum(),
                   "pop_weighted_attrib_heat_c": np.average(g.attrib_heat_c, weights=g.population),
                   "share_of_total_warming_burden_pct": np.nan,  # filled below
                   "net_person_degc": g.person_degc.sum()}), include_groups=False)
               .reset_index().rename(columns={"q": f"{label}_quartile"}))
        pos = e.person_degc.clip(lower=0)
        t["share_of_total_warming_burden_pct"] = [
            100 * pos[pd.qcut(e[col], 4, labels=False) == i].sum() / pos.sum() for i in range(4)]
        rows[label] = t
    return rows


def restoration(e, b):
    """Green cover needed to bring each hotter-than-average ward back to the city average."""
    hot = e[e.lst_rel_late > 0].copy()
    for name, beta in zip(["", "_lowcool", "_highcool"], b):
        hot[f"green_needed_pp{name}"] = hot.lst_rel_late / beta
    # 1 percentage point of a ward's area = area_km2 hectares (1 km2 = 100 ha)
    hot["green_needed_ha"] = hot.green_needed_pp * hot.area_km2
    hot["green_now_ha"] = hot.green_cover_pct_late * hot.area_km2
    hot["green_after_pct"] = hot.green_cover_pct_late + hot.green_needed_pp
    hot["multiple_of_current_green"] = hot.green_after_pct / hot.green_cover_pct_late
    return hot.sort_values("lst_rel_late", ascending=False)


def figure(dist, top):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4), gridspec_kw={"width_ratios": [1, 1.25]})
    fig.subplots_adjust(wspace=0.55)
    d = dist["density"]
    ax = axes[0]
    ax.set_axisbelow(True)
    ax.bar(range(4), d.pop_weighted_attrib_heat_c, width=0.6,
           color=[RED if v > 0 else BLUE for v in d.pop_weighted_attrib_heat_c])
    for i, v in enumerate(d.pop_weighted_attrib_heat_c):
        ax.text(i, v + (0.005 if v >= 0 else -0.005), f"{v:+.2f} °C", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=9, color=INK)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(range(4), ["Least dense", "Q2", "Q3", "Most dense"])
    ax.set_title("Warming (+) or cooling (−) from green change,\nby ward density (population-weighted, summer)", fontsize=10)
    ax.grid(axis="x", visible=False)
    ax.margins(y=0.25)

    ax = axes[1]
    ax.set_axisbelow(True)
    t = top.head(10).iloc[::-1]
    y = np.arange(len(t))
    ax.barh(y, t.green_now_ha, color=GRID, height=0.6, label="Green cover today")
    ax.barh(y, t.green_needed_ha, left=t.green_now_ha, color=BLUE, height=0.6,
            label="Extra green needed to reach city-average heat")
    for i, r in enumerate(t.itertuples()):
        ax.text(r.green_now_ha + r.green_needed_ha, i, f"  {r.multiple_of_current_green:.1f}× today",
                va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y, t.ward_name, fontsize=9)
    ax.set_xlabel("Hectares of green cover")
    ax.set_title("What it would take to cool the 10 hottest wards", fontsize=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.17), ncol=2, fontsize=8, frameon=False)
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.22)
    fig.suptitle("The economics of green cover: who bears the heat, and the scale of the fix",
                 x=0.02, ha="left", fontweight="bold", fontsize=13, y=1.04)
    fig.text(0.02, -0.1, "Based on the summer fixed-effects estimate (≈1.0 °C per 10 pp of green cover). "
             "Surface temperature, not air temperature. Central estimates; ranges in outputs/economics_*.",
             color=MUTED, fontsize=8)
    fig.savefig(cfg.FIG / "fig6_economics.png")


def main():
    b = coefficient()
    log.info("Cooling rate: %.3f °C per pp of green cover (95%% CI %.3f-%.3f)", *b)
    ch = pd.read_csv(cfg.OUT / "ward_change_2022_2026.csv").dropna(subset=["d_green_cover_pct", "population"])
    e = attributable_heat(ch, b)
    dist = distribution(e)
    rest = restoration(e, b)

    cols = ["ward_id", "ward_name", "assembly_constituency", "population", "area_km2",
            "green_cover_pct_late", "d_green_cover_pct", "attrib_heat_c", "attrib_heat_c_low",
            "attrib_heat_c_high", "person_degc"]
    e[cols].round(4).to_csv(cfg.OUT / "economics_ward_burden.csv", index=False)
    rcols = ["ward_id", "ward_name", "lst_rel_late", "green_cover_pct_late", "green_needed_pp",
             "green_needed_pp_highcool", "green_needed_pp_lowcool", "green_needed_ha", "green_now_ha",
             "green_after_pct", "multiple_of_current_green"]
    rest[rcols].round(3).to_csv(cfg.OUT / "economics_restoration.csv", index=False)
    for k, t in dist.items():
        t.round(4).to_csv(cfg.OUT / f"economics_by_{k}_quartile.csv", index=False)

    losing = e.attrib_heat_c > 0
    top10 = rest.head(10)
    summary = {
        "cooling_rate_c_per_pp": {"central": b[0], "ci95_low": b[1], "ci95_high": b[2]},
        "wards_with_attributable_warming": int(losing.sum()),
        "people_in_those_wards": int(e.population[losing].sum()),
        "pop_weighted_attrib_heat_c_city": float(np.average(e.attrib_heat_c, weights=e.population)),
        "pop_weighted_attrib_heat_c_losing_wards": float(np.average(e.attrib_heat_c[losing],
                                                                    weights=e.population[losing])),
        "max_ward_attrib_heat_c": float(e.attrib_heat_c.max()),
        "top10_hot_wards": {
            "median_green_now_pct": float(top10.green_cover_pct_late.median()),
            "median_green_needed_pp": float(top10.green_needed_pp.median()),
            "median_green_needed_pp_range": [float(top10.green_needed_pp_highcool.median()),
                                             float(top10.green_needed_pp_lowcool.median())],
            "total_green_needed_ha": float(top10.green_needed_ha.sum()),
            "median_multiple_of_current_green": float(top10.multiple_of_current_green.median()),
        },
    }
    (cfg.OUT / "economics_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    for k, t in dist.items():
        print(f"\nBy {k} quartile:\n", t.round(3).to_string(index=False))
    print("\nRestoration, 10 hottest wards:\n", top10[rcols].round(2).to_string(index=False))
    figure(dist, rest)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    main()
