# Using This Project in Your LSE Application

> Check the exact programme name and requirements on the LSE website. The closest match to "sustainable economics and climate change" is likely the **MSc Environmental Economics and Climate Change** (Department of Geography and Environment). Tailor the wording below to whichever programme you apply to.

## The story this project tells

Your gap is not "no environment background". It is "no *formal* environment background". This project turns that around in three steps:

1. **Lived motivation.** You felt Bengaluru's summers getting harsher, and that is credible and personal.
2. **Rigour you already have.** You built a reproducible pipeline over 4+ years of public satellite data and used a panel-econometrics design that goes beyond a naive correlation.
3. **Intellectual honesty.** You report a result that contradicts the naive story: by day the city is *cooler* than the countryside. You report that the city-wide trend is not yet statistically significant. And you say why the fixed-effects estimate is what you trust. Admissions readers value this more than a dramatic headline.

The project also ends with the questions you *cannot yet answer*: costs, distribution and policy. Those are exactly what the Masters teaches. That ending is your "why this degree".

## Statement of purpose: draft paragraphs

*Rewrite in your own voice. Admissions readers can tell when text is not yours.*

> When I moved to Bengaluru in 2022, the city's reputation as a "garden city" still felt deserved. By the summer of 2024, the year of the city's severe water crisis, that reputation felt like history. As a data engineer, I wanted to know whether my experience was real, so I built an open, reproducible pipeline over five years of Landsat and MODIS satellite data.
>
> The data confirmed my experience, and complicated it. Over 2022–2026 the core city lost about a fifth of its green cover, and its summer surface temperature rose by 2.7 °C. Using a two-way fixed-effects panel of 624 neighbourhood cells, which separates local land-use change from city-wide weather, I estimate that each 10 percentage points of green cover lost raised local surface temperature by about 0.7 °C. The most surprising finding was that, by day, the city is cooler than its dry rural surroundings. Bengaluru's heat island is a night-time phenomenon, which is when residents without air-conditioning have no way to escape it.
>
> This project showed me the limits of what I can do as an engineer. I can measure a degree of warming; I cannot yet say what it costs, who pays, or which policy would correct a market that treats a tree's cooling as worthless. That is why I am applying to [programme]: to learn the tools of environmental valuation, welfare economics and policy evaluation, so that the next time I build a pipeline it answers the question that matters to decision-makers.

## CV / résumé line

> **Independent research: Green Cover Loss and Urban Heat in Bengaluru (2022–2026)** · github.com/[you]/bengaluru-uhi
> Built a reproducible, validated geospatial pipeline (Python, STAC, xarray, DuckDB) over Landsat 8/9, Sentinel-2 and MODIS imagery for 225 BBMP wards, 2022–2026. Two-way fixed-effects panels show that each 10 pp of green cover lost raises summer surface temperature by about 0.7–1.0 °C, robust across 1 km grid and ward-level specifications. Published an interactive ward heat map.

## Interview questions to prepare

| Likely question | Your answer, in brief |
|---|---|
| "Why should we believe this is causal?" | Cell fixed effects remove permanent geography; year fixed effects remove weather. What remains is time-varying local confounding. Say honestly that β includes the effect of what replaced the trees. |
| "Surface vs air temperature?" | LST is not air temperature. The next step is validating against IMD stations. |
| "Why is daytime UHI negative?" | Dry pre-monsoon farmland heats faster than a city with trees and lakes. The heat island shows up at night. |
| "Why not just plant trees elsewhere?" | The spatial results show cooling is local, so compensatory planting far away does not help the neighbourhood that lost the trees. This is an equity and policy-design point. |
| "What would you do with more time?" | See `economics_extension.md`: valuation, distribution by income, policy evaluation. |
| "How does data engineering help in climate economics?" | Most climate-economics evidence now comes from large spatial and administrative datasets. Building, cleaning and scaling those is a bottleneck you can already handle. |

## Before you submit: checklist

- [ ] Put the repo on your personal GitHub (public), with your name in the README.
- [ ] Rerun `run_all.sh` yourself so you understand every step and can defend every number.
- [ ] Read the papers listed in `economics_extension.md` and verify each citation.
- [ ] Optional: a two-page PDF summary or a short blog post (Medium or LinkedIn) with figures 1 and 4.
- [ ] Optional, and high value: validate against IMD air temperature, and add BBMP ward boundaries.
- [ ] Keep the project separate from employer work. Use only personal accounts and open data, and no employer systems or data.
