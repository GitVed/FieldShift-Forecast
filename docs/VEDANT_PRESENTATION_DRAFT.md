# Vedant pitch and submission drafts

Draft only, 2026-11-14. Do not claim the full app is integrated. Replace bracketed prompts with actual results after integration. Remove any sentence whose feature is not demonstrable.

## 30-second pitch

FieldShift Forecast helps an Ontario farmer compare crop rotations using climate history and long-term trial evidence. Our Harrow-area prototype connects NASA climate data with crop suitability and a transparent rotation scorer. Each number has a source, and each missing value stays visible. We are building toward a dry-year stress test so farmers can understand both the evidence and the uncertainty behind a planting decision.

## 90-second demo script

This farmer has to decide what to plant next. Last year's harvest alone cannot show whether a rotation is suited to changing conditions.

[Open the pilot map. Confirm the field location and data badges before presenting.]

Detect shows the climate history for the selected location. [If integrated, point to the actual trend result, slope, period and confidence. Otherwise say this screen is still a prototype.]

Predict compares scenarios. [Demonstrate only implemented scenarios.] The 2035 view is a stress test, not a weather forecast. We do not claim a completed drought backtest until the replay actually runs.

Plan separates crop suitability from rotation evidence. Model 2 can already run independently on SAMPLE crop scores. It keeps continuous cropping visible and shows why a rotation can or cannot be scored. Missing crop yields remain unavailable rather than becoming invented bushels.

[Show a source link and one missing-data state.] Historical soybean trial references are available, but they are not a yield promise for this field. Revenue uses dated prices and requires evidence for every crop year. Costs are not verified, so revenue is not profit.

We are not replacing a farmer's experience. We are making the evidence and its limits easier to inspect. The next step is to connect verified field data and test the complete workflow.

## Submission draft

FieldShift Forecast is a Harrow-area Ontario prototype for comparing crop rotations under changing growing conditions. Its intended workflow is Detect, Predict and Plan: inspect historical climate change, explore stress scenarios, then compare rotations using crop suitability and local trial evidence.

Completed Model 2 work includes an independent Python rotation module, a stable dictionary interface for crop suitability, verified historical soybean reference yields, dated commodity price references, source metadata, a SAMPLE ranking fixture and automated validation. The scorer exposes missing crop scores and yields. Its evidence-only mode withholds unsupported overall rankings; an opt-in SAMPLE policy supports interface development without claiming validated scoring weights.

Planned NASA integration uses cached POWER climate series and a trend engine. Do not mark these features completed until Dev's implementation has been integrated and checked. Real crop suitability comes from Ved's Model 1 and is also pending integration.

The prototype distinguishes observed trial references from scenario predictions. It does not apply a second rotation uplift to already rotation-specific yields. Gross revenue is computed only when every crop year has a supported yield and compatible dated price. Net profit is not claimed.

The pilot point still needs reconciliation with the Woodslee trial location. Corn and wheat reference yields and calibrated rotation-score weights remain incomplete. These limits are explicit in the output and documentation.

## Assumptions and limitations slide copy

- SAMPLE rankings are prototype indices, not validated success probabilities.
- Harrow pilot and Woodslee trial coordinates differ. Site correspondence needs checking.
- Trial references reflect historical management and periods; they are not field forecasts.
- Corn and wheat reference yields are not verified for these exact treatments.
- Climate yield adjustment is 1 by assumption. A real drought replay is not yet validated.
- Water needs are not rainfall thresholds. Crop period, soil storage and irrigation matter.
- Prices are historical regional averages. Standard bushel mass conversions are assumptions.
- Revenue excludes costs and is not profit. Incomplete rotations have no revenue total.

## Future work slide copy

The prototype demonstrates a method for one Ontario pilot. Farmer soil tests, crop history and yield-monitor records could support field-specific calibration. Other regions would need their own local trials, climate checks and prices. Harrow yield references do not transfer automatically.

## AI disclosure draft

AI tools helped research sources, implement Model 2, prepare tests and draft presentation text. Team members remain responsible for validating claims, selecting the final method and submitting the project. Do not claim AI helped produce measured field data.

## Before presenting

Confirm the actual location, integrate Model 1 and NASA scenarios, verify all visible results, test the offline demo, replace conditional prompts, rehearse once, and use the event's submission form to confirm required fields. Event dates and eligibility rules have not been independently checked in this implementation task.
