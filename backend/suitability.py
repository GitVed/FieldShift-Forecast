"""Model 1 stub: suitability percent per crop for the Harrow field.

STATUS: stub. Runs on a SAMPLE profile. No Random Forest yet.

Rules (SUMMARY-README section 3b, CLAUDE.md):
- GAEZ is the primary source for wheat, soybean and maize. It is a fixed
  baseline per crop. It is NOT used as the dry-year or 2035 scenario score.
- Range fit (OMAFRA ranges, UNVERIFIED) drives the scenarios, because it uses
  temperature and rainfall, so it changes when the climate inputs change.
- Kaggle is only for maize and general rules. Never wheat or soy. Not built yet.
- If a crop has no usable source, it is NOT scored. Nothing is invented.
- No P or K. Inputs: temperature, rainfall, humidity, pH, nitrogen,
  soil moisture, soil organic carbon, sand, silt, clay.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GAEZ_CSV = os.path.join(HERE, "..", "data", "seed", "gaez_harrow.csv")

CROPS = ["wheat", "soybean", "maize"]

# OMAFRA ranges supplied by Ved. UNVERIFIED until Vedant checks the source.
# Open questions: which period the mm values cover, and which temperature
# (growing season mean?) the C range applies to.
# Maize has no range supplied, so it cannot be scored by this fallback.
RANGES = {
    "wheat": {"ph": (6.0, 7.5), "rain_mm": (350, 650), "temp_c": (10, 25)},
    "soybean": {"ph": (6.0, 7.0), "rain_mm": (450, 700), "temp_c": (20, 30)},
}

# SAMPLE profile. Placeholder values for testing the code. Not Harrow data.
# Replace with Dev's cached POWER and SoilGrids values when they exist.
SAMPLE_PROFILE = {
    "label": "SAMPLE",
    "temp_c": 18.0,
    "rain_mm": 500.0,
    "humidity_pct": 70.0,
    "ph": 6.5,
    "nitrogen": None,
    "soil_moisture": None,
    "soil_organic_carbon": None,
    "sand": None,
    "silt": None,
    "clay": None,
}


# The GAEZ csv has one row per crop per period. The baseline uses one period.
# Chosen by Claude as the latest historical period. Ved to confirm.
# The 2021-2040 SSP370 rows are NOT used as the scenario score. Range fit
# drives the dry and 2035 scenarios (decision, Sat Nov 14).
GAEZ_BASELINE_SCENARIO = "2001-2020 rain-fed high input"


def load_gaez(path=GAEZ_CSV, scenario=GAEZ_BASELINE_SCENARIO):
    """Return {crop: suitability} for the baseline period only.
    UNVERIFIED rows are skipped. The value is the GAEZ suitability index (SI),
    treated here as a 0 to 100 percent. The csv also has a suitability_class."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("scenario") != scenario:
                continue
            try:
                out[row["crop"]] = float(row["suitability"])
            except (ValueError, KeyError):
                pass
    return out


def range_fit(crop, profile):
    """Share of checked variables inside the crop's range, as a percent.
    This is a range check, not model output. Returns None if not scorable."""
    rng = RANGES.get(crop)
    if rng is None:
        return None
    checks = []
    for key, (lo, hi) in rng.items():
        val = profile.get(key)
        if val is not None:
            checks.append(lo <= val <= hi)
    if not checks:
        return None
    return 100.0 * sum(checks) / len(checks)


def score_crops(profile, scenario="normal", gaez=None):
    """Return {crop: dict(percent, source, gaez_baseline, note)}.

    normal: GAEZ if available, else range fit, else not scored.
    dry / 2035_dry: range fit only. GAEZ is shown as baseline, not the score.
    """
    gaez = load_gaez() if gaez is None else gaez
    result = {}
    for crop in CROPS:
        fit = range_fit(crop, profile)
        base = gaez.get(crop)
        if scenario == "normal" and base is not None:
            pct, src = base, "GAEZ"
        elif fit is not None:
            pct, src = fit, "range fallback (UNVERIFIED OMAFRA ranges)"
        else:
            pct, src = None, None
        note = ""
        if pct is None:
            note = "NOT SCORED. No GAEZ value and no range."
            if crop == "maize":
                note += " Kaggle maize path not built yet."
        result[crop] = {"percent": pct, "source": src, "gaez_baseline": base, "note": note}
    return result


def main():
    profile = SAMPLE_PROFILE
    print(f"Model 1 suitability stub. Profile: {profile['label']}")
    print("Inputs used: temp_c, rain_mm, ph (others not wired yet). No P or K.\n")
    res = score_crops(profile, "normal")
    for crop in CROPS:
        r = res[crop]
        base = "n/a" if r["gaez_baseline"] is None else f"{r['gaez_baseline']:.0f}"
        if r["percent"] is None:
            print(f"{crop:8} NOT SCORED   GAEZ baseline: {base}   {r['note']}")
        else:
            print(f"{crop:8} {r['percent']:5.0f} %      GAEZ baseline: {base}   source: {r['source']}   [{profile['label']}]")
    not_scored = [c for c in CROPS if res[c]["percent"] is None]
    print()
    if not_scored:
        print("Not scored:", ", ".join(not_scored))
    else:
        print("All crops scored.")
    print("Any rotation containing a not-scored crop must be shown as 'not scored'.")


if __name__ == "__main__":
    main()
