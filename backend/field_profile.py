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

Window assumption (UNVERIFIED, Vedant to confirm against a crop calendar):
SEASON_MONTHS = May to September is used as the growing season for temperature,
rain and humidity. Annual values are reported too, so nothing is hidden.
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


def _item(value, unit, source_id, window, note="", label="CACHED"):
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


def soil():
    """Topsoil (0-20 cm) from HWSD2. SoilGrids rows are all invalid at this
    point (Dev's quality flags), so they are not used."""
    out = {}
    for r in _rows("hwsd_soil_harrow.csv"):
        if r["depth_top_cm"] == "0" and r["quality_flag"] == "regional_estimate" and r["value"]:
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
        prov = {**clim, **{f"soil_{k}": v for k, v in soil_items.items()}}
        profile = {
            "label": "CACHED",
            "scenario": sid,
            "title": title,
            "temp_c": clim["temp_c"]["value"],
            "rain_mm": clim["rain_mm"]["value"],
            "humidity_pct": clim["humidity_pct"]["value"],
            "soil_moisture": clim["soil_moisture_july"]["value"],
            "ph": soil_items.get("ph", {}).get("value"),
            "nitrogen": soil_items.get("total_nitrogen", {}).get("value"),
            "soil_organic_carbon": soil_items.get("organic_carbon", {}).get("value"),
            "sand": soil_items.get("sand", {}).get("value"),
            "silt": soil_items.get("silt", {}).get("value"),
            "clay": soil_items.get("clay", {}).get("value"),
            "provenance": prov,
        }
        out[sid] = profile
    return out


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
