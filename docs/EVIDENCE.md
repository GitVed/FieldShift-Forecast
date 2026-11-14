# Model 2 evidence audit

Checked 2026-11-14. These checks validate reference claims, not a prediction for the pilot field. The trial CSV retains all original claims and adds verification and cache labels. Only VERIFIED bu/ac rows enter numeric output.

## Soybean references and percentage mismatch

[Craig Drury's firsthand interview, April 21, 2021](https://www.realagriculture.com/2021/04/soybean-school-should-you-plant-more-soybeans) identifies soybean yields of 41 bu/ac for continuous soybean, 53 for soybean-soybean-wheat, and 64 for corn-soybean-wheat. The five calendar years are unspecified. It also reports the soil carbon comparison, under 2% versus 2.25% after 17 years, and an approximate 16% increase. These are historical comparisons, not future trajectories.

Calculated from the rounded yields: 53/41 - 1 = 29.27%; 64/41 - 1 = 56.10%. Keep those calculations distinct from the interview's approximate 30% and 50% descriptions. Do not force the numbers to match.

[Agomoh et al., 2021, DOI 10.1002/saj2.20241](https://acsess.onlinelibrary.wiley.com/doi/full/10.1002/saj2.20241) reports a different aggregation: soybean yields measured during 2002-2018, with 48-52% improvements in three-year rotations. This does not verify the planning document's exact 51-54% claim. That CSV row remains UNVERIFIED.

## Corn and wheat

The 118, 154, 169, 112, 188 and 17 bu/ac corn claims and their specific periods/treatments remain UNVERIFIED. They are retained for audit and excluded from numeric output. The 38-42%, 43% and 68% claims cannot safely be combined across unknown periods and management systems.

[Agomoh et al., DOI 10.1002/saj2.20000, methods and Table 1](https://acsess.onlinelibrary.wiley.com/doi/10.1002/saj2.20000) is not a clean winter wheat yield replacement: winterkill led to spring wheat replanting in 2018. Its wheat rotation results are also averaged across cover treatments. No wheat yield was inserted into the scorer.

## Location

The same paper locates the Woodslee experiment at 42 degrees 13 minutes N, 82 degrees 44 minutes W, approximately 42.2167, -82.7333. This differs from the configured pilot point 42.0356, -82.9183. The trial location is verified at the paper's coarse precision; the pilot field polygon and trial equivalence are not. Ved and Dev must choose which site their cached data represents before integration. No field config or teammate cache was changed.

## Crop ranges

[FAO, Crop Water Needs, Table 5](https://www.fao.org/4/s2022e/s2022e02.htm) gives approximate whole-growing-period water needs: wheat 450-650 mm, soybean 450-700 mm, maize 500-800 mm. These describe crop evapotranspiration, not acceptable rainfall bands. Soil storage and irrigation matter. The supplied wheat 350-650 mm range is not verified by this table. Do not feed annual or monthly rainfall directly into these bands.

[OMAFRA Soil Fertility Handbook, Table 3-1](https://files.ontario.ca/omafra-soil-fertility-handbook-en-2022-10-13.pdf) provides soil-specific liming thresholds and targets, not a universal ideal pH interval. For fine-textured soils, wheat/soybean target pH is 6.0 and corn target is 5.5; rotation guidance uses the higher crop requirement. This does not verify the supplied upper bounds or temperature ranges. Model 1's existing fallback ranges therefore remain UNVERIFIED. Ved owns changes to suitability.py.

## Drought wording

[Bowles et al., 2020](https://www.sciencedirect.com/science/article/pii/S2590332220300889) synthesizes 347 site-years at 11 experiments. It reports mean maize gains of 28.1% and drought yield-loss reductions of 14.0-89.9%. A reduction in loss is not the same as that percent more yield. These results are contextual evidence, not Harrow-specific climate multipliers or a 2012 replay.

## Price cache

[Grain Farmers of Ontario monthly weighted prices](https://gfo.ca/average-commodity-prices/) is the selected source. September 2026 references: corn CAD 275.38/t, soybean CAD 604.86/t, wheat CAD 315.44/t. These are historical Ontario aggregates, not local delivery bids, future prices or profit.

[Government of Saskatchewan, April 2013, page 16](https://pubsaskdev.blob.core.windows.net/pubsask-prod/83604/83604-agv1304-pdf.pdf) supplies standard mass conversions: corn 39.368 bu/t; soybean/wheat 36.744 bu/t. Using these rather than measured test weights is an explicit revenue assumption. Wheat pricing is not grade-specific. The price JSON preserves original units, conversion factors, period, retrieval date and links.
