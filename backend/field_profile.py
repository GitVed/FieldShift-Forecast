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
SEASON_LABEL = "May-Sep (corn and soybean window)"
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
    "source": ("OMAFRA Publication 811, Agronomy Guide for Field Crops (the 2017 guide the team called OMAFRA 2017), "
               "chapters 1, 2 and 4; OMAFRA Field Crop Report, 14 Sept 2017"),
    "corn": {"seeded": "late April and the first half of May (Pub 811 ch. 1)",
             "harvested": "not found as a month in Pub 811"},
    "soybean": {"seeded": "best before the middle of May (Pub 811 ch. 2)",
                "harvested": "3 to 10 days after physiological maturity, mid September to early October in Pub 811 Table 2-5"},
    "wheat": {"seeded": "optimum mid-October in southwestern Ontario (OMAFRA Field Crop Report, 14 Sept 2017); "
                        "often set by when soybeans are harvested (Pub 811 ch. 4)",
              "harvested": "not found as a month in Pub 811"},
    "urls": ["https://www.ontario.ca/files/2022-10/omafra-agronomy-guide-for-field-crops-chapter-1-en-2022-10-13.pdf",
             "https://www.ontario.ca/files/2022-10/omafra-agronomy-guide-for-field-crops-chapter-2-en-2022-10-13.pdf",
             "https://www.ontario.ca/files/2022-10/omafra-agronomy-guide-for-field-crops-chapter-4-en-2022-10-13.pdf",
             "https://fieldcropnews.com/?p=14180"],
    "note": ("May to September is the corn and soybean window only. Winter wheat is sown in the fall after soybeans and "
             "harvested the next summer, which is why it fits a rotation and leaves time for red clover. The wording "
             "'late August to mid October' and 'late June to mid July' that the team supplied was not found in these sources."),
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


SOIL_VARS = ("ph", "sand", "silt", "clay")
SOILGRIDS_FIELD = "soilgrids_field.csv"   # WCS pre-fetch at the cropland field point, 0-30 cm


def soil():
    """Topsoil texture and pH. SoilGrids (250 m, modelled) at the cropland field
    point, depth-weighted 0-30 cm. Falls back to HWSD2 (1 km, regional estimate)
    if that file is missing. Organic carbon and nitrogen are not used here;
    soil carbon comes from the trial (SOIL_CARBON)."""
    out = {}
    path = SEED / SOILGRIDS_FIELD
    if path.exists():
        acc = {}
        for r in _rows(SOILGRIDS_FIELD):
            if r["variable"] in SOIL_VARS and r["quality_flag"] == "valid" and r["value"]:
                w = int(r["depth_bottom_cm"]) - int(r["depth_top_cm"])
                a = acc.setdefault(r["variable"], [0.0, 0, r["unit"], r["cell_id"]])
                a[0] += float(r["value"]) * w; a[1] += w
        for var, (total, weight, unit, cell) in acc.items():
            if weight == 30:
                out[var] = _item(total / weight, unit, "soilgrids_wcs", "0-30 cm, depth-weighted",
                                 f"ISRIC SoilGrids 250 m at the field point ({cell}). Modelled, not a lab test.",
                                 label="CACHED (modelled)")
    if len(out) == len(SOIL_VARS):
        return out
    return soil_hwsd2()


def soil_hwsd2():
    """HWSD2 topsoil (0-20 cm), regional mapping unit. Cross-check only."""
    out = {}
    for r in _rows("hwsd_soil_harrow.csv"):
        if (r["depth_top_cm"] == "0" and r["quality_flag"] == "regional_estimate" and r["value"]
                and r["variable"] in SOIL_VARS):
            out[r["variable"]] = _item(float(r["value"]), r["unit"], r["source_id"], "0-20 cm",
                                       "FAO HWSD2 regional mapping unit, not a field soil test",
                                       label="CACHED (regional estimate)")
    return out


# ---------- daily NASA data: POWER and IMERG ----------

IMERG_BASELINE_YEARS = range(2001, 2021)   # IMERG file starts mid-1998
DRY_DAY_MM = 1.0       # ETCCDI dry day: precipitation below 1 mm
HEAVY_RAIN_MM = 10.0   # ETCCDI R10mm: days with at least 10 mm
GDD_BASE_C = 10.0      # degree days above 10 C from the daily mean


def _daily(path, column):
    import datetime as dt
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    start = lines.index("-END HEADER-") + 1
    out = {}
    for r in csv.DictReader(lines[start:]):
        v = float(r[column])
        if v > -900:
            out[dt.date(int(r["YEAR"]), 1, 1) + dt.timedelta(days=int(r["DOY"]) - 1)] = v
    return out


_DAILY = {}


def daily(name):
    if name not in _DAILY:
        _DAILY[name] = {
            "power_rain": lambda: _daily("data/seed/power_harrow_daily_1981_2025.csv", "PRECTOTCORR"),
            "power_temp": lambda: _daily("data/seed/power_harrow_daily_1981_2025.csv", "T2M"),
            "imerg_rain": lambda: _daily("data/source/imerg_harrow_daily_19980601_20251231.csv", "IMERG_PRECTOT"),
        }[name]()
    return _DAILY[name]


def _season_days(series, year):
    vals = [v for d, v in sorted(series.items()) if d.year == year and d.month in SEASON_MONTHS]
    return vals if len(vals) == 153 else None   # May 1 to Sep 30, complete only


def season_stats(series, year):
    vals = _season_days(series, year)
    if vals is None:
        return None
    longest = run = 0
    for v in vals:
        run = run + 1 if v < DRY_DAY_MM else 0
        longest = max(longest, run)
    return {"rain_mm": sum(vals), "dry_spell_days": longest, "heavy_rain_days": sum(v >= HEAVY_RAIN_MM for v in vals)}


def degree_days(year):
    vals = _season_days(daily("power_temp"), year)
    return None if vals is None else sum(max(t - GDD_BASE_C, 0.0) for t in vals)


def stress_facts(years, label):
    """May-Sep stress facts from both NASA daily sources, as plain measured facts."""
    def mean(xs):
        xs = [x for x in xs if x is not None]
        return round(statistics.mean(xs), 1) if xs else None
    out = {"label": label, "window": "May 1 to Sep 30",
           "method": ("Dry spell: longest run of days with under 1 mm (ETCCDI dry-day threshold). Heavy rain: "
                      "days with at least 10 mm (ETCCDI R10mm). Degree days: sum of daily mean temperature "
                      "above 10 C."), "sources": {}}
    for src, series, yrs in (("power", daily("power_rain"), years),
                             ("imerg", daily("imerg_rain"), [y for y in years if y >= 1999] or years)):
        if src == "imerg" and len(years) > 1:
            yrs = list(IMERG_BASELINE_YEARS)
        stats = [season_stats(series, y) for y in yrs]
        out["sources"][src] = {
            "years": f"{yrs[0]}-{yrs[-1]}" if len(yrs) > 1 else str(yrs[0]),
            "rain_mm": mean(s and s["rain_mm"] for s in stats),
            "dry_spell_days": mean(s and s["dry_spell_days"] for s in stats),
            "heavy_rain_days": mean(s and s["heavy_rain_days"] for s in stats),
        }
    out["degree_days_above_10c"] = mean(degree_days(y) for y in years)
    return out


def imerg_monthly():
    out = {}
    for r in _rows("imerg_precip_harrow.csv"):
        if r["variable"] == "precipitation" and r["quality_flag"] == "valid" and r["value"]:
            out[(int(r["date"][:4]), int(r["date"][5:7]))] = float(r["value"])
    return out


def gldas_july_layers(years):
    """July volumetric soil moisture for the root-zone layers, mean over years."""
    out = {}
    for depth in (("0", "10"), ("10", "40"), ("40", "100")):
        sm = gldas_july(depth)
        vals = [sm[y] for y in years if y in sm]
        out[f"{depth[0]}-{depth[1]} cm"] = round(statistics.mean(vals), 3) if vals else None
    return out


def data_quality():
    """Valid-row counts from Dev's quality report, for the files the model uses."""
    import json
    used = ("power_t2m_harrow_1981_2025.csv", "power_precip_harrow_1981_2025.csv",
            "power_humidity_harrow_1981_2025.csv", "imerg_precip_harrow.csv", "gldas_soil_moisture_harrow.csv")
    rows = {r["section"]: r["metadata"] for r in _rows("quality_report_all.csv")}
    datasets = json.loads(json.loads(rows["datasets"])) if rows["datasets"].startswith('"') else json.loads(rows["datasets"])
    return {name: {"rows": d.get("rows"), "usable_rows": d.get("usable_rows"), "verdict": d.get("verdict")}
            for name, d in datasets.items() if name in used}


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
        "rain_mm_imerg": _item(_over_years(imerg_monthly(), years if len(years) == 1 else list(IMERG_BASELINE_YEARS),
                                           SEASON_MONTHS, "sum"), "mm", "imerg_daily",
                               f"{SEASON_LABEL} total, " + (label_years if len(years) == 1 else "2001-2020 mean"),
                               "GPM IMERG, 0.1 degree. Second NASA rain source, cross-checks POWER."),
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
    for key in ("rain_mm", "rain_annual_mm", "rain_mm_imerg"):
        future[key]["note"] = rain_note
    future["soil_moisture_july"]["note"] = f"Not projected. Uses the {DRY_YEAR} value."

    stress = {"normal": stress_facts(base_years, "1991-2020 mean (IMERG 2001-2020)"),
              "dry": stress_facts([DRY_YEAR], str(DRY_YEAR))}
    stress["2035_dry"] = {**stress["dry"], "label": f"{DRY_YEAR} values, not projected"}
    root = {"normal": {"years": "2000-2020 mean", **gldas_july_layers(GLDAS_BASELINE_YEARS)},
            "dry": {"years": str(DRY_YEAR), **gldas_july_layers([DRY_YEAR])}}
    root["2035_dry"] = {**root["dry"], "years": f"{DRY_YEAR}, not projected"}
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
            "rain_mm_imerg": clim["rain_mm_imerg"]["value"],
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
            "stress": stress[sid],
            "root_zone_july_m3m3": root[sid],
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
