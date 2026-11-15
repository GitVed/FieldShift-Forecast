"""Model 1: crop suitability for the Harrow field. Owner: Ved.

Method, decided Sat Nov 14 ("sourced only"). Every number has a source.

Score per crop (0 to 100, GAEZ Suitability Index, not a percent):
- normal:   GAEZ v5, 2001-2020, rain-fed high input.
- 2035_dry: GAEZ v5, 2021-2040 SSP370 ensemble, rain-fed high input. This is
            FAO/IIASA's own future-climate suitability; 2035 falls inside it.
            It reflects average future climate, not a dry year, so the dry-year
            facts are shown beside it.
- dry:      the 2012 replay has no sourced crop response for a single season,
            so the score is NOT recomputed. The GAEZ baseline is shown with
            scenario_applied False, next to the measured stress facts.

Checks shown beside the score (not blended into it):
- water: May-Sep rain against FAO whole-growing-period crop water need
  (FAO Irrigation Water Management, Crop Water Needs, Table 5). Rain only,
  ignores soil storage. Not computed for winter wheat, which grows Oct-Jul.
- pH: HWSD2 topsoil pH against OMAFRA target pH for fine-textured soils
  (OMAFRA Soil Fertility Handbook, Table 3-1). HWSD2 is a regional estimate.

The earlier OMAFRA temperature and rain ranges were removed: Vedant's evidence
audit (docs/EVIDENCE.md) found no source for them.
Kaggle and SF24 are not used yet (maize and general rules only, later).
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GAEZ_CSV = os.path.join(HERE, "..", "data", "seed", "gaez_harrow.csv")

CROPS = ["wheat", "soybean", "maize"]

GAEZ_PERIODS = {
    "baseline": "2001-2020 rain-fed high input",
    "future": "2021-2040 rain-fed high input SSP370 ENSEMBLE",
    "history": "1981-2000 rain-fed high input",
}
GAEZ_BASELINE_SCENARIO = GAEZ_PERIODS["baseline"]
GAEZ_LABEL = "GAEZ v5 SI 0-100, rain-fed high input, 2001-2020"
GAEZ_FUTURE_LABEL = "GAEZ v5 SI 0-100, rain-fed high input, 2021-2040 SSP370 ensemble"
DRY_BASELINE_LABEL = "GAEZ baseline, dry scenario not applied"

FAO_WATER_SOURCE = "https://www.fao.org/4/s2022e/s2022e02.htm"
FAO_WATER_NEED_MM = {"wheat": (450, 650), "soybean": (450, 700), "maize": (500, 800)}
OMAFRA_PH_SOURCE = "https://files.ontario.ca/omafra-soil-fertility-handbook-en-2022-10-13.pdf"
OMAFRA_TARGET_PH_FINE = {"wheat": 6.0, "soybean": 6.0, "maize": 5.5}

SCENARIOS = ("normal", "dry", "2035_dry")

# SAMPLE profile for tests and offline fallback only. Not Harrow data.
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


def load_gaez(path=GAEZ_CSV, scenario=GAEZ_BASELINE_SCENARIO):
    """Return {crop: suitability index} for one GAEZ period. UNVERIFIED rows skipped."""
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


def water_check(crop, profile):
    """May-Sep rain as a share of the FAO crop water need range.
    Uses every rain source in the profile (POWER, and IMERG when present), so the
    result is a low-to-high range across sources and across the FAO need range."""
    rains = {k: profile.get(k) for k in ("rain_mm", "rain_mm_imerg") if profile.get(k) is not None}
    lo, hi = FAO_WATER_NEED_MM[crop]
    base = {"need_mm": [lo, hi], "source": FAO_WATER_SOURCE,
            "rain_by_source_mm": {("POWER" if k == "rain_mm" else "IMERG"): round(v, 1) for k, v in rains.items()},
            "note": "Rain only. Ignores soil water storage. FAO need is crop evapotranspiration "
                    "over the whole growing period."}
    if crop == "wheat":
        return {**base, "rain_mm": profile.get("rain_mm"), "covers_pct": None,
                "status": "not computed",
                "note": ("Winter wheat is seeded late Aug to mid Oct and harvested late June to mid July "
                         "(OMAFRA 2017, as supplied), so the May-Sep corn and soybean window does not fit it.")}
    if not rains:
        return {**base, "rain_mm": None, "covers_pct": None, "status": "no rain data"}
    low_rain, high_rain = min(rains.values()), max(rains.values())
    return {**base, "rain_mm": round(low_rain, 1),
            "covers_pct": [round(100 * low_rain / hi), round(100 * high_rain / lo)],
            "calc": (f"low = {low_rain:.0f} mm / {hi} mm need = {100 * low_rain / hi:.0f}%; "
                     f"high = {high_rain:.0f} mm / {lo} mm need = {100 * high_rain / lo:.0f}%"),
            "status": "rain covers need" if low_rain >= lo else "rain below need in at least one source"}


def ph_check(crop, profile):
    ph = profile.get("ph")
    target = OMAFRA_TARGET_PH_FINE[crop]
    out = {"ph": ph, "target_ph": target, "source": OMAFRA_PH_SOURCE,
           "note": "Target for fine-textured soils. Soil pH is an HWSD2 regional estimate."}
    out["status"] = "no pH data" if ph is None else ("at or above target" if ph >= target else "below target")
    return out


def score_crops(profile, scenario="normal", gaez=None, gaez_future=None):
    """Return {crop: dict(percent, source, label, gaez_baseline, scenario_applied,
    note, checks)}. Contract with Model 2 (TASKS.md V3) is unchanged."""
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    gaez = load_gaez() if gaez is None else gaez
    gaez_future = load_gaez(scenario=GAEZ_PERIODS["future"]) if gaez_future is None else gaez_future
    result = {}
    for crop in CROPS:
        base = gaez.get(crop)
        future = gaez_future.get(crop)
        applied, note = True, ""
        if scenario == "normal":
            pct, src = base, GAEZ_LABEL
        elif scenario == "2035_dry":
            if future is not None:
                pct, src = future, GAEZ_FUTURE_LABEL
                note = "Average 2021-2040 climate, not a dry year. See the dry-year facts."
            else:
                pct, src, applied = base, DRY_BASELINE_LABEL, False
                note = "No GAEZ future value for this crop."
        else:  # dry
            pct, src, applied = base, DRY_BASELINE_LABEL, False
            note = "No sourced crop response for a single dry season. See the dry-year facts."
        if pct is None:
            src, note = None, "NOT SCORED. No GAEZ value for this crop."
        result[crop] = {
            "percent": pct, "source": src,
            "label": "CACHED" if pct is not None else "UNVERIFIED",
            "gaez_baseline": base, "scenario_applied": applied, "note": note,
            "checks": {"water": water_check(crop, profile), "ph": ph_check(crop, profile)},
        }
    return result


def main():
    try:
        from field_profile import build_scenarios
    except ImportError:
        from backend.field_profile import build_scenarios
    profiles = build_scenarios()
    print("Model 1 suitability. Scores are the GAEZ Suitability Index (0-100), not a percent.")
    for scenario in SCENARIOS:
        p = profiles[scenario]
        print(f"\n{p['title']} [{p['label']}]  May-Sep rain {p['rain_mm']:.0f} mm, "
              f"May-Sep temp {p['temp_c']:.1f} C")
        for crop, r in score_crops(p, scenario).items():
            score = "NOT SCORED" if r["percent"] is None else f"{r['percent']:5.1f}"
            w, ph = r["checks"]["water"], r["checks"]["ph"]
            water = (f"rain covers {w['covers_pct'][0]}-{w['covers_pct'][1]}% of FAO need"
                     if w["covers_pct"] else w["status"])
            print(f"  {crop:8} {score}  {r['source']}{' | ' + r['note'] if r['note'] else ''}")
            print(f"           water: {water} | pH {ph['ph']} vs target {ph['target_ph']}: {ph['status']}")


if __name__ == "__main__":
    main()
