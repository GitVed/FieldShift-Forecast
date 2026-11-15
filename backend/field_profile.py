"""Harrow field profile and climate scenarios from Dev's cached CSVs. Owner: Ved.

Reads only local files in data/seed. Never calls an API. Uses rows whose
quality_flag is "valid" (climate) or "regional_estimate" (HWSD2 soil).

Every value carries: value, unit, label (CACHED), source_id, window, note.

Scenario rules
- normal:   1991-2020 baseline (README 3.2, "Normal year, based on 1991 to 2020").
- dry:      the actual 2012 season (README 3.2 names 2012 as a real dry year).
            2021 is also named there, but in this POWER cell its May-Sep rain is
            above the baseline, so it is reported as a check, not used as "dry".
- 2035_dry: 2012 with the temperature trend applied (README 3.2, "trend applied
            to the dry year"). Slope comes from Dev's trend_results.csv, only if
            its verdict is "increasing" or "decreasing". Rain is NOT extrapolated,
            because Dev's rain trend verdict is "inconclusive".

Growing window: SEASON_MONTHS = May to September, for corn and soybean only,
from the crop calendar below. It is not used for winter wheat.

Soil: HWSD2 is used for texture and pH only. Soil organic carbon comes from the
local trial measurement, not HWSD2 (see SOIL_CARBON).
"""
import csv
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"

CELL = "power_harrow_point"
SEASON_MONTHS = (5, 6, 7, 8, 9)
SEASON_LABEL = "May-Sep (window UNVERIFIED)"
BASELINE_YEARS = range(1991, 2021)
DRY_YEAR = 2012
CHECK_DRY_YEAR = 2021
TARGET_YEAR = 2035
GLDAS_BASELINE_YEARS = range(2000, 2021)  # GLDAS file starts in 2000
JULY = 7

FILES = {
    "temperature": "power_t2m_harrow_1981_2025.csv",
    "precipitation": "power_precip_harrow_1981_2025.csv",
    "humidity": "power_humidity_harrow_1981_2025.csv",
}


def _rows(name):
    with open(SEED / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def monthly(variable):
    """{(year, month): value} for valid rows of one POWER variable."""
    out = {}
    for r in _rows(FILES[variable]):
        if r["variable"] == variable and r["quality_flag"] == "valid" and r["value"]:
            out[(int(r["date"][:4]), int(r["date"][5:7]))] = float(r["value"])
    return out


def _season(series, year, months, how):
    vals = [series[(year, m)] for m in months if (year, m) in series]
    if len(vals) != len(months):
        raise ValueError(f"Missing months for {year}: cannot build a complete window")
    return sum(vals) if how == "sum" else sum(vals) / len(vals)


def _over_years(series, years, months, how):
    return statistics.mean(_season(series, y, months, how) for y in years)


# Crop calendar. Source: OMAFRA 2017, citation as supplied by the team.
# The document link was not recorded, so it has not been checked here.
CROP_CALENDAR = {
    "source": "OMAFRA 2017 (citation as supplied; link not recorded, not checked)",
    "corn": {"seeded": "May", "harvested": "late September to early November"},
    "soybean": {"seeded": "May", "harvested": "late September to early November"},
    "wheat": {"seeded": "late August to mid October, previous year",
              "harvested": "late June to mid July"},
    "note": ("May to September is the corn and soybean growing window only. Winter wheat is in the "
             "ground over winter and out by July, which is why it fits a rotation and frees the "
             "field for red clover."),
}

# Soil organic carbon. HWSD2 is a global model value; the trial is a local measurement.
SOIL_CARBON = {
    "value": "2.0 to 2.25", "unit": "%",
    "source": "https://www.topcropmanager.com/the-benefits-of-crop-rotation-and-diversification/",
    "note": ("Local trial measurement after 17 years: just under 2 percent in continuous soybean, "
             "just over 2.25 percent in soybean-winter wheat-corn (Drury, 2021). Sampling depth is "
             "not stated in the source (0 to 20 cm is UNVERIFIED). HWSD2 global model shows about "
             "6.6 percent for this point. We use the local measurement and do not average them. "
             "The claim that 6.6 percent is close to uncropped woodlot Brookston soil is UNVERIFIED."),
    "hwsd2_modelled_pct": 6.6,
}


def _item(value, unit, source_id, window, note="", label="CACHED"):
    if value is not None and not isinstance(value, (int, float)):
        return {"value": value, "unit": unit, "label": label, "source_id": source_id,
                "window": window, "note": note}
    return {"value": None if value is None else round(value, 3), "unit": unit,
            "label": label, "source_id": source_id, "window": window, "note": note}


def gldas_july(depth=("0", "10")):
    """{year: July volumetric soil moisture} for one GLDAS layer."""
    out = {}
    for r in _rows("gldas_soil_moisture_harrow.csv"):
        if (r["quality_flag"] == "valid" and (r["depth_top_cm"], r["depth_bottom_cm"]) == depth
                and int(r["date"][5:7]) == JULY):
            out[int(r["date"][:4])] = float(r["value"])
    return out


SOIL_FROM_HWSD2 = ("ph", "sand", "silt", "clay")


def soil():
    """Topsoil (0-20 cm) texture and pH from HWSD2. SoilGrids rows are all
    invalid at this point (Dev's quality flags). HWSD2 organic carbon and
    nitrogen are not used; soil carbon comes from the trial (SOIL_CARBON)."""
    out = {}
    for r in _rows("hwsd_soil_harrow.csv"):
        if (r["depth_top_cm"] == "0" and r["quality_flag"] == "regional_estimate" and r["value"]
                and r["variable"] in SOIL_FROM_HWSD2):
            out[r["variable"]] = _item(float(r["value"]), r["unit"], r["source_id"], "0-20 cm",
                                       "FAO HWSD2 regional mapping unit, not a field soil test",
                                       label="CACHED (regional estimate)")
    return out


def temperature_trend():
    """Dev's 1981-2025 temperature trend for this cell, or None if not directional."""
    for r in _rows("trend_results.csv"):
        if (r["cell_id"] == CELL and r["variable"] == "temperature" and r["start_year"] == "1981"
                and r["verdict"] in ("increasing", "decreasing")):
            return {"slope_per_decade": float(r["slope_per_decade"]), "unit": r["slope_unit"],
                    "verdict": r["verdict"], "p_value": float(r["p_value"]),
                    "buddy_check": r["buddy_check"], "sensitivity_check": r["sensitivity_check"]}
    return None


def rain_trend_verdict():
    for r in _rows("trend_results.csv"):
        if r["cell_id"] == CELL and r["variable"] == "precipitation" and r["start_year"] == "1981":
            return r["verdict"]
    return "missing"


def _climate(years, label_years):
    T, P, H = monthly("temperature"), monthly("precipitation"), monthly("humidity")
    sm = gldas_july()
    sm_years = [y for y in years if y in sm]
    return {
        "temp_c": _item(_over_years(T, years, SEASON_MONTHS, "mean"), "degC", "power_monthly",
                        f"{SEASON_LABEL}, {label_years}"),
        "temp_annual_c": _item(_over_years(T, years, range(1, 13), "mean"), "degC", "power_monthly",
                               f"annual, {label_years}"),
        "rain_mm": _item(_over_years(P, years, SEASON_MONTHS, "sum"), "mm", "power_monthly",
                         f"{SEASON_LABEL} total, {label_years}"),
        "rain_annual_mm": _item(_over_years(P, years, range(1, 13), "sum"), "mm", "power_monthly",
                                f"annual total, {label_years}"),
        "humidity_pct": _item(_over_years(H, years, SEASON_MONTHS, "mean"), "%", "power_monthly",
                              f"{SEASON_LABEL}, {label_years}"),
        "soil_moisture_july": _item(statistics.mean(sm[y] for y in sm_years) if sm_years else None,
                                    "m3/m3", "gldas_noah025", "July, 0-10 cm",
                                    "" if sm_years else "No GLDAS data for these years"),
    }


def build_scenarios():
    """Return {scenario_id: profile}. Profile keys match suitability.score_crops,
    plus a "provenance" dict holding the full value records."""
    base_years = list(BASELINE_YEARS)
    soil_items = soil()
    normal = _climate(base_years, "1991-2020 mean")
    sm = gldas_july()
    normal["soil_moisture_july"] = _item(statistics.mean(sm[y] for y in GLDAS_BASELINE_YEARS if y in sm),
                                         "m3/m3", "gldas_noah025", "July, 0-10 cm, 2000-2020 mean",
                                         "GLDAS starts in 2000, so its baseline is shorter")
    dry = _climate([DRY_YEAR], str(DRY_YEAR))
    future = {k: dict(v) for k, v in dry.items()}
    trend = temperature_trend()
    years_ahead = (TARGET_YEAR - DRY_YEAR) / 10.0
    if trend:
        shift = trend["slope_per_decade"] * years_ahead
        for key in ("temp_c", "temp_annual_c"):
            future[key] = _item(dry[key]["value"] + shift, "degC", "power_monthly + trend_results",
                                f"{dry[key]['window']} + trend to {TARGET_YEAR}",
                                f"{DRY_YEAR} value plus {trend['slope_per_decade']:.3f} degC/decade "
                                f"x {years_ahead:.1f} decades (Dev's 1981-2025 trend, verdict {trend['verdict']}). "
                                "Stress test, not a forecast.")
    else:
        for key in ("temp_c", "temp_annual_c"):
            future[key]["note"] = "No directional temperature trend, so no shift applied."
    rain_note = (f"Rain not extrapolated: Dev's rain trend verdict is {rain_trend_verdict()}. "
                 f"Uses the {DRY_YEAR} value.")
    for key in ("rain_mm", "rain_annual_mm"):
        future[key]["note"] = rain_note
    future["soil_moisture_july"]["note"] = f"Not projected. Uses the {DRY_YEAR} value."

    out = {}
    for sid, clim, title in (("normal", normal, "Normal year"), ("dry", dry, f"Dry year ({DRY_YEAR} replay)"),
                             ("2035_dry", future, f"{TARGET_YEAR} dry-year stress test")):
        prov = {**clim, **{f"soil_{k}": v for k, v in soil_items.items()},
                "soil_organic_carbon": _item(SOIL_CARBON["value"], "%", "trial_topcropmanager_2021",
                                             "after 17 years", SOIL_CARBON["note"])}
        profile = {
            "label": "CACHED",
            "scenario": sid,
            "title": title,
            "temp_c": clim["temp_c"]["value"],
            "rain_mm": clim["rain_mm"]["value"],
            "humidity_pct": clim["humidity_pct"]["value"],
            "soil_moisture": clim["soil_moisture_july"]["value"],
            "ph": soil_items.get("ph", {}).get("value"),
            "nitrogen": None,              # HWSD2 nitrogen not used
            "soil_organic_carbon": None,   # range from the trial, see provenance
            "soil_organic_carbon_text": SOIL_CARBON["value"] + " %",
            "sand": soil_items.get("sand", {}).get("value"),
            "silt": soil_items.get("silt", {}).get("value"),
            "clay": soil_items.get("clay", {}).get("value"),
            "provenance": prov,
        }
        out[sid] = profile
    return out


def july_soil_moisture_trend(depth=("0", "10")):
    """Mann-Kendall test and Sen slope on July GLDAS topsoil moisture, one value
    per year (no deseasonalising needed). Same libraries as Dev's trend.py.
    There is no GLDAS buddy cell, so the verdict can never be "confirmed"."""
    import pymannkendall as mk
    from scipy.stats import theilslopes
    sm = gldas_july(depth)
    years = sorted(sm)
    values = [sm[y] for y in years]
    test = mk.original_test(values)
    slope = float(theilslopes(values, years)[0] * 10)
    significant = bool(test.h)
    return {"slope_per_decade": slope, "unit": "m3/m3 per decade", "p_value": float(test.p),
            "n": len(values), "start_year": years[0], "end_year": years[-1],
            "direction": ("increasing" if slope > 0 else "decreasing") if significant else "no significant trend",
            "verdict": "not confirmed (no buddy cell, short record)" if significant else "inconclusive",
            "method": "Mann-Kendall (original), Sen slope, July values only",
            "source_id": "gldas_noah025", "label": "CACHED"}


def dry_year_check():
    """May-Sep rain for the two years README calls dry, against the baseline."""
    P = monthly("precipitation")
    base = _over_years(P, list(BASELINE_YEARS), SEASON_MONTHS, "sum")
    return {str(y): {"rain_mm": round(_season(P, y, SEASON_MONTHS, "sum"), 1),
                     "vs_baseline_mm": round(_season(P, y, SEASON_MONTHS, "sum") - base, 1)}
            for y in (DRY_YEAR, CHECK_DRY_YEAR)} | {"baseline_rain_mm": round(base, 1)}


if __name__ == "__main__":
    for sid, p in build_scenarios().items():
        print(f"\n{p['title']} [{p['label']}]")
        for k in ("temp_c", "temp_annual_c", "rain_mm", "rain_annual_mm", "humidity_pct", "soil_moisture_july"):
            v = p["provenance"][k]
            print(f"  {k:19} {v['value']!s:>9} {v['unit']:6} {v['window']}" + (f"  | {v['note']}" if v["note"] else ""))
    print("\nSoil (HWSD2 0-20 cm, regional estimate):",
          {k: p[k] for k in ("ph", "nitrogen", "soil_organic_carbon", "sand", "silt", "clay")})
    print("Dry-year check:", dry_year_check())
