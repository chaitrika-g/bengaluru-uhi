# From Degrees to Rupees: The Economics Questions This Raises

The satellite analysis answers a physical question: losing 10 percentage points of green cover makes a neighbourhood about 0.7 °C hotter. The economic questions are the ones I want to study at the Masters level.

> **Citation note.** References below are starting points to read and verify before citing in any application or paper. No monetary figure is estimated here, deliberately. Each needs a properly sourced dose-response parameter.

## 1. Urban green as an unpriced public good

A tree on private land cools the street, the neighbours and the night-time city. The owner who fells it to build captures the full private gain and bears almost none of the social cost of the extra heat. That is a textbook **negative externality**. It is also why green cover is under-provided in fast-growing cities.

**Question:** What is the *shadow price* of a unit of green cover in Bengaluru? The cooling coefficient estimated here (°C per pp of green) is the physical half of that price.

## 2. The cost channels

| Channel | Mechanism | Approach | Where to start |
|---|---|---|---|
| **Labour productivity** | Heat lowers output per worker, especially outdoors and in non-air-conditioned factories | Combine local °C changes with a temperature–productivity dose-response | Somanathan, Somanathan, Sudarshan & Tewari (2021), *Journal of Political Economy*, on Indian manufacturing; ILO (2019), *Working on a Warmer Planet* |
| **Electricity demand** | Cooling load rises with temperature, especially at night | Ward-level BESCOM consumption vs LST, if data can be obtained | Indian Cooling Action Plan (MoEFCC, 2019) for context |
| **Health** | Heat-related mortality and morbidity; warm nights block physiological recovery | Mortality–temperature response functions | Carleton et al. (2022), *Quarterly Journal of Economics*, on the global mortality costs of climate change |
| **Property values** | People pay a premium to live near parks and trees (a hedonic price) | Hedonic regression of rents/prices on green cover and LST | Hedonic valuation literature |

## 3. Distribution: who bears the heat?

Air-conditioning is an adaptation the rich can buy. The households most exposed (outdoor workers, informal settlements, delivery riders) are the least able to adapt.

**Question:** Is green loss in Bengaluru concentrated in lower-income wards? Ward-level census or socioeconomic data overlaid on the `grid_long_difference.csv` output would show this.

## 4. Policy instruments worth evaluating

- **Tree-felling compensation.** Karnataka's tree-protection law requires compensatory planting. Does replanting elsewhere actually offset *local* heat? The spatial results suggest location matters.
- **Green building / cool-roof mandates** versus direct public investment in parks and lake restoration.
- **Pigouvian levies** on canopy removal, priced at the externality estimated above.
- **Cost-benefit analysis** of urban afforestation, using a social discount rate. The choice of rate is a central debate in climate economics (Stern vs Nordhaus).

## 4b. What has been done (src/economics.py)

The first two economic steps are now implemented using only this project's estimates:
- **Distribution of the burden:** attributable warming per ward (green-cover change × summer cooling rate), weighted by population. 3.2 million people live in wards that warmed about +0.24 °C on average from green loss, and the least dense quarter of wards bears 73 % of the burden.
- **Restoration requirement:** the 10 hottest wards would need about +21 pp of green cover (17–29), about 3.6× today, ~450 ha, to reach the city-average temperature. This is an extrapolation beyond the observed ±11 pp ward changes.

### Why there is no rupee figure yet, and how to get one
1. **The missing link is surface vs air temperature.** Damage functions are estimated per degree of *air* temperature. One example is "annual plant output falls by about 2 % per degree Celsius" in Indian manufacturing, from the abstract of [Somanathan, Somanathan, Sudarshan & Tewari (2021), *JPE* 129(6)](https://epic.uchicago.edu/research/the-impact-of-temperature-on-productivity-and-labor-supply-evidence-from-indian-manufacturing/). Read the paper's methods section to confirm exactly which temperature measure it uses. This project measures *surface* temperature. The next step is to estimate the surface-to-air relationship for Bengaluru by pairing LST with IMD station air temperatures.
2. **Exposure data:** ward-level employment or output (for example, from the Economic Census or ASI factory locations) is needed to turn "% productivity" into rupees.
3. **Costs of the fix:** cost per hectare of urban greening, and land values in the hottest wards, for a cost-benefit comparison with alternatives such as cool roofs.

## 5. A concrete next-step research design

1. Validate the LST results against IMD air-temperature stations.
2. Move from NDVI to tree canopy (Sentinel-2, 10 m).
3. Link to BBMP ward boundaries and socioeconomic indicators.
4. Translate °C into costs using peer-reviewed dose-response functions, reporting sensitivity ranges rather than point estimates.
5. Compare the social value of green cover with the private value of the land use that replaces it.
