# Ved branch compatibility review

Reviewed 2026-11-14 after fetching origin/ved/model at df2a0de. Working branch was not switched or merged. Review uses local Model 2 code and data plus an isolated copy of Ved's latest suitability.py and GAEZ CSV.

## Observed result

Actual score_crops output passed into rank_rotations for normal, dry and 2035_dry without errors, six rotations per call. Default evidence_only results remain pending rules; opt-in sample_diversity results are scored and labelled SAMPLE. Crop aliases and scenario_applied flags are preserved inside breakdown.crop_suitability. All 14 Model 2 unit tests pass.

Normal GAEZ scores: wheat 97.91, soybean 53.71, maize 97.91. These are cached source values as present on Ved's branch, not independently reverified in this code review. Dry and 2035 outputs on SAMPLE_PROFILE are identical: wheat 100, soybean 66.6667, maize 97.91 with scenario_applied false. The API supplies the same sample climate profile for all scenarios. A change of scoring method alone is not a climate stress simulation.

## Integration gaps

- Ved app.py calls rank_rotations using the accepted signature. It then rebuilds display rows, keeping rank and revenue hardcoded None. It reads trial CSV rows directly and labels all yields UNVERIFIED instead of consuming yield_bu_ac and yield_references. It drops most component metadata. Update the adapter to use Model 2 results, source links, labels and missing states.
- app.py retains stale prices_verified false, no-price wording, and field_config.json price_file none chosen. Model 2 already has model2_prices.json. Metadata needs reconciliation, without treating missing rotation yields as resolved.
- Model 1 has GAEZ lookup scores for all three crops. A trained Random Forest is not required merely to call Model 2. Model 1 remains a stub and does not use the actual NASA/soil profile yet.
- Dev supplies real cached profiles and scenario transformations. Ved connects them. Maize needs verified scenario handling; currently dry maize is unchanged baseline. Range validation is Vedant's VS1 evidence responsibility, implemented by Ved in suitability.py.
- Normal GAEZ SI and fallback fraction-of-range-check scores have different meanings. They cannot be presented as a validated like-for-like scenario comparison without an agreed method.
- Model 1 crop records have no individual label. Model 2 conservatively returns SAMPLE. Add per-crop provenance for future real-data calls.
- Model 2 still lacks calibrated benefit/penalty weights and verified corn/wheat treatment yields. Ved finishing Model 1 cannot supply these automatically.
- Resolve the documented trial/pilot location mismatch jointly before freezing cached data.
- Integration must retain the local rotation.py, amended verification columns in harrow_trial_yields.csv, and Model 2 price/source files. Ved's old skeleton and CSV do not replace them. Without verification columns the new loader intentionally admits no yield references.

## Verification limit

Direct Model 1-to-Model 2 calls were executed. FastAPI adapter findings are from reading its code; no HTTP server or browser integration was run. No teammate source files were edited. Repro script and detailed results are in ignored .tools/check_ved_compatibility.py and .tools/ved_review/results.json.
