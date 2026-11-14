# Model 2 implementation and handoff

Model 2 runs independently of Model 1. It uses Python's standard library only. No web calls occur at runtime.

## Run

With an installed Python:

```powershell
python backend/rotation.py
python backend/rotation.py --policy sample_diversity --output data/seed/model2_sample_output.json
python -m unittest discover -s tests -v
```

This workspace also has an ignored portable runtime. Replace `python` with `.tools/python/python.exe` to use it. It is a local tool, not a shipped dependency.

Default execution uses a SAMPLE crop dictionary and the evidence_only policy. All six rotations remain visible. Missing crop percents produce `not scored`; otherwise scores remain `pending rules` because the sources do not calibrate the rotation-benefit and soil-penalty weights. Pending results have no numerical rank.

The opt-in sample_diversity policy produces ranked SAMPLE results for UI development. Its arbitrary point weights are documented at the top of rotation.py. It is not validated agronomy and cannot be relabeled CACHED, even with real suitability inputs. The overall index is not a probability or measured rotation benefit. Scores clamp to 0-100; equal scores share rank. Continuous cropping stays in the returned list for comparison.

Repeated crops count per cash-crop year. Red clover is underseeded in the wheat phase; it adds neither a year nor an unsupported bonus. Unknown yields remain UNVERIFIED. No rotation-specific yield is multiplied by an additional rotation benefit. The same historical yield references appear in every scenario with climate adjustment 1, explicitly an assumption.

## Model 1 and API integration

```python
from backend.rotation import rank_rotations

# Ved supplies the scenario-specific dictionary.
suitability = {
    'maize': {'percent': 71, 'source': 'SAMPLE', 'label': 'SAMPLE'},
    'soybean': {'percent': 88, 'source': 'SAMPLE', 'label': 'SAMPLE'},
    'wheat': {'percent': 82, 'source': 'SAMPLE', 'label': 'SAMPLE'},
}
rows = rank_rotations(suitability, scenario='normal')
# Explicit UI-only ranking:
rows = rank_rotations(suitability, scoring_policy='sample_diversity')
```

Existing two-positional-argument calls work. Aliases maize/corn and soy/soybean normalize; duplicate aliases raise an error instead of silently choosing one. Percents must be finite numeric 0-100 values or None; scored crops require a source. Input dictionaries are not mutated.

The V3 required keys are preserved. Additive fields include rank, yield_references, revenue_detail, notes and policy provenance. The top-level label defaults SAMPLE. Per-component CACHED labels identify historical references separately. If callers want CACHED provenance, provide crop labels and the call label explicitly; a label is not proof of validation.

Supported scenario names: normal, dry, 2035_dry, 2012_replay. These are passed through, not computed here. Unsupported names fail clearly. The CLI accepts `--input` for a Model 1 JSON dictionary and `--scenario`. App and UI owners should handle ValueError as a validation error.

## Yield and money rules

Only source-linked VERIFIED bu/ac CSV rows supply numbers. Existing columns stay intact; verification and label columns are additive. Duplicated verified references fail rather than mix studies. Three soybean reference yields are verified. Corn and wheat values remain unavailable.

Gross annual revenue requires a supported yield and dated price for every cash-crop year. It averages the yearly crop revenues over the rotation, counting repeated crop years. Missing prices return `price not chosen`; missing yields return an explicit UNVERIFIED message. No partial sum is presented as a rotation total. Costs, net profit and future price prediction are absent. Historical trial yield times historical regional price is a reference calculation, not expected farm income.

## Handoff for teammates

- Ved: suitability.py, app.py and field_config.json are untouched beyond importing your existing versions. Keep the dictionary contract above. Fallback temperature/rainfall ranges still need validation; see EVIDENCE.md.
- Dev: resolve pilot versus Woodslee trial location before freezing caches. Model 2 has its own model2_sources.json for incorporation into your source registry. No sources.json changes were made.
- Shlok: model2_sample_output.json is a UI fixture. Keep SAMPLE badges, missing-value strings and component source links. Display tied ranks; never convert missing yields to zero. Use evidence_only output for honest pending states.
- Vedant: calibrated scoring weights, verified corn/wheat treatment yields, and trial/pilot correspondence remain open even after Model 1 arrives. No farmer-ready recommendation is claimed.

## Validation

14 stdlib unittest tests cover missing crops, aliases, repeated years, clover, bounds, invalid inputs, provenance, score ties/order, scenario invariance, source gating, duplicate references, annualized revenue and incomplete totals. Both CLI modes and JSON fixtures are checked. Real Model 1, FastAPI and UI integration await their owners' implementations.
