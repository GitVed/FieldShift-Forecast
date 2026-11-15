"""FieldShift Forecast API (V4). Owner: Ved.

Reads cached files only. Never calls an external API.

Endpoints, shaped like frontend/sample_data.json (Shlok):
  GET /api/pilot                     -> "pilot"
  GET /api/detect/{cell_id}          -> "detect"   (from Dev's trend_results.csv)
  GET /api/predict/{field_id}        -> "predict"
  GET /api/rotation/{field_id}       -> "plan"     (query: scenario)
Dev's cached-data router is mounted too:
  GET /api/series/{cell_id}, GET /api/trend/{cell_id}

Run from the repo root:  uvicorn backend.app:app
The SQLite cache for Dev's router is built on startup if it is missing.
"""
import csv
import functools
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend import field_profile, rotation, stress, suitability
from backend.provenance import load_manifest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
FIELD_ID = "harrow"
SCENARIOS = ("normal", "dry", "2035_dry")
SCENARIO_ALIASES = {"future": "2035_dry"}          # Shlok's predict id
PREDICT_IDS = {"normal": "normal", "dry": "dry", "2035_dry": "future"}
TRIAL_SITE = {"lat": 42.2167, "lon": -82.7333, "dms": "42 deg 13 min N, 82 deg 44 min W", "kind": "point",
              "source": "https://acsess.onlinelibrary.wiley.com/doi/10.1002/saj2.20000",
              "note": "Woodslee trial site, in a different NASA POWER cell from the field."}
POWER_CELL_SIZE = (0.5, 0.625)  # degrees lat, lon; POWER file header "0.5 x 0.625 degree lat/lon region"


def _db_ready():
    from sqlalchemy import func, select
    from backend import db
    try:
        with db.get_engine().connect() as conn:
            return conn.execute(select(func.count()).select_from(db.trend_runs)).scalar() > 0
    except Exception:
        return False


@asynccontextmanager
async def lifespan(_app):
    if not _db_ready():
        from backend.seed import seed
        seed()
    yield


app = FastAPI(title="FieldShift Forecast API", lifespan=lifespan)

try:
    from backend.data_api import make_router
    app.include_router(make_router())
except Exception as exc:  # Dev's router needs SQLAlchemy; the rest of the API does not
    print(f"Dev's data router not mounted: {exc}")


def _scenario(name):
    name = SCENARIO_ALIASES.get(name, name)
    if name not in SCENARIOS:
        raise HTTPException(status_code=422, detail=f"scenario must be one of {SCENARIOS}")
    return name


def _field(field_id):
    if field_id != FIELD_ID:
        raise HTTPException(status_code=404, detail=f"Unknown field_id {field_id}")


@functools.lru_cache(maxsize=1)
def profiles():
    return field_profile.build_scenarios()


@functools.lru_cache(maxsize=1)
def field_config():
    import json
    return json.loads((ROOT / "backend" / "field_config.json").read_text(encoding="utf-8"))


def _fixture_pilot():
    import json
    return json.loads((ROOT / "frontend" / "sample_data.json").read_text(encoding="utf-8"))["pilot"]


def _cell_bounds(cell_id):
    cell = load_manifest(ROOT)["resolved_cells"][cell_id]
    lat, lon = cell["center_latitude"], cell["center_longitude"]
    dlat, dlon = POWER_CELL_SIZE[0] / 2, POWER_CELL_SIZE[1] / 2
    return [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]], (lat, lon)


# ---------- pilot ----------

def _km(a, b):
    import math
    dlat = math.radians(b[0] - a[0]); dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


@app.get("/api/pilot")
def pilot():
    field = field_config()
    fx = _fixture_pilot()
    layers = {k: dict(v) for k, v in fx["layers"].items()}
    for key, cell in (("trend-grid-cell", "power_harrow_point"), ("north-comparison-grid-cell", "power_north_point")):
        bounds, (lat, lon) = _cell_bounds(cell)
        layers[key] = {"status": "CACHED", "bounds": bounds,
                       "description": f"NASA POWER cell centred {lat}, {lon} (0.5 x 0.625 degrees), {cell}"}
    layers["harrow-field"] = {"status": "SAMPLE", "description": field["polygon_note"]}
    km = _km((field["lat"], field["lon"]), (TRIAL_SITE["lat"], TRIAL_SITE["lon"]))
    soil = profiles()["normal"]["provenance"]
    tex = ", ".join(f"{k} {soil['soil_' + k]['value']:.1f}%" for k in ("sand", "silt", "clay") if "soil_" + k in soil)
    return {
        "field_id": field["field_id"],
        "cell_id": "harrow-power",
        "name": field["name"],
        "region": fx["region"],
        "soil": (f"{field['soil_type']}. Model uses SoilGrids 250 m at the field, 0-30 cm: pH "
                 f"{soil['soil_ph']['value']:.1f}, {tex} (modelled)."),
        "center": {"lat": field["lat"], "lon": field["lon"]},
        "coordinate_status": field["coordinates_status"] + " Field polygon is SAMPLE geometry.",
        "polygon": field["polygon"],
        "layers": layers,
        "trial_site": {**TRIAL_SITE, "distance_km": round(km, 1),
                       "note": f"Woodslee trial site, about {km:.0f} km from the field, in a different NASA POWER cell."},
        "polygon_status": field["polygon_status"],
        "polygon_note": field["polygon_note"],
        "data_point_note": field["data_point_note"],
        "previous_point": field["previous_point"],
    }


# ---------- detect ----------

def _trend_rows():
    with open(SEED / "trend_results.csv", encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["cell_id"] == "power_harrow_point" and r["start_year"] == "1981"]


def _soil_moisture_trend():
    t = field_profile.july_soil_moisture_trend()
    return {"id": "soil_moisture", "name": "July topsoil moisture trend (0-10 cm)",
            "value": round(t["slope_per_decade"], 4), "unit": "m³/m³ / decade",
            "p_value": f"{t['p_value']:.2g}", "status": "CACHED",
            "verdict": f"{t['direction']}, {t['verdict']}",
            "source": (f"GLDAS Noah 0.25 degree, July {t['start_year']}-{t['end_year']} ({t['n']} years), "
                       f"{t['method']}. No buddy cell, so not confirmed.")}


@app.get("/api/detect/{cell_id}")
def detect(cell_id: str):
    if cell_id not in ("harrow", "harrow-power", "power_harrow_point"):
        raise HTTPException(status_code=404, detail="Unknown cell")
    rows = {r["variable"]: r for r in _trend_rows()}
    t, p = rows["temperature"], rows["precipitation"]
    src = "NASA POWER monthly 1981-2025, Hamed-Rao modified Mann-Kendall and Sen slope (data/seed/trend_results.csv)"

    def trend(row, tid, name, unit):
        return {"id": tid, "name": name, "value": round(float(row["slope_per_decade"]), 2), "unit": unit,
                "p_value": f"{float(row['p_value']):.2g}", "status": "CACHED",
                "verdict": row["verdict"], "source": src}

    return {
        "status": "CACHED",
        "confidence": f"Temperature: {t['confidence']}. Rainfall: {p['confidence']}.",
        "buddy_check": f"Temperature {t['buddy_check']}, rainfall {p['buddy_check']} (cell 0.5 degrees north)",
        "verdict": (f"Temperature {t['verdict']}, {float(t['slope_per_decade']):+.2f} °C per decade since 1981. "
                    f"Rainfall {p['verdict']}."),
        "trends": [
            trend(t, "temperature", "Temperature trend (all months, deseasonalised)", "°C / decade"),
            trend(p, "rainfall", "Rainfall trend (monthly totals)", "mm/month / decade"),
            _soil_moisture_trend(),
        ],
        "series": [],
        "source": src,
        "note": "Trend verdicts need significance plus the north-cell and 1991-start checks. Not a forecast.",
        "data_quality": {"files": field_profile.data_quality(),
                         "text": "; ".join(f"{k}: {v['usable_rows']} of {v['rows']} rows valid"
                                           for k, v in field_profile.data_quality().items()),
                         "source": "data/seed/quality_report_all.csv (Dev's validation)"},
    }


# ---------- predict ----------

def _stress_lines(p, n):
    """Plain-language stress facts for one scenario against the normal year."""
    st, ns = p["stress"], n["stress"]
    out = []
    for src, name in (("power", "POWER"), ("imerg", "IMERG")):
        a, b = st["sources"][src], ns["sources"][src]
        out.append({"source": name, "years": a["years"], "normal_years": b["years"],
                    "rain_mm": a["rain_mm"], "normal_rain_mm": b["rain_mm"],
                    "rain_change_mm": None if a["rain_mm"] is None else round(a["rain_mm"] - b["rain_mm"], 1),
                    "dry_spell_days": a["dry_spell_days"], "normal_dry_spell_days": b["dry_spell_days"],
                    "heavy_rain_days": a["heavy_rain_days"], "normal_heavy_rain_days": b["heavy_rain_days"]})
    return out


@app.get("/api/predict/{field_id}")
def predict(field_id: str):
    _field(field_id)
    ps = profiles()
    n = ps["normal"]
    out = []
    for sid in SCENARIOS:
        p = ps[sid]
        prov = p["provenance"]
        sm = prov["soil_moisture_july"]["value"]
        nsm = n["provenance"]["soil_moisture_july"]["value"]
        crops = suitability.score_crops(p, sid)
        lines = _stress_lines(p, n)
        rain_changes = [l["rain_change_mm"] for l in lines if l["rain_change_mm"] is not None]
        gdd, ngdd = p["stress"]["degree_days_above_10c"], n["stress"]["degree_days_above_10c"]
        summary = (f"May-Sep {p['temp_c']:.1f} °C. Rain {min(rain_changes):+.0f} to {max(rain_changes):+.0f} mm vs normal "
                   f"across POWER and IMERG. Degree days above 10 °C {gdd:.0f} vs {ngdd:.0f} normal. "
                   f"Longest dry spell {lines[0]['dry_spell_days']:g} days (POWER) and {lines[1]['dry_spell_days']:g} "
                   f"(IMERG) vs about {lines[0]['normal_dry_spell_days']:g} normally")
        out.append({
            "id": PREDICT_IDS[sid],
            "name": p["title"],
            "period": prov["temp_c"]["window"],
            "summary": summary if sid != "normal" else (
                f"May-Sep {p['temp_c']:.1f} °C, {p['rain_mm']:.0f} mm rain (POWER) and "
                f"{p['rain_mm_imerg']:.0f} mm (IMERG 2001-2020)"),
            "temp": round(p["temp_c"] - n["temp_c"], 2),
            "rainfall": round(p["rain_mm"] - n["rain_mm"], 1),
            "soil_moisture": None if sm is None or nsm is None else round(sm - nsm, 3),
            "status": "CACHED",
            "source": "NASA POWER (temperature, rain), GPM IMERG (rain cross-check), GLDAS (soil moisture), change vs normal",
            "notes": [prov[k]["note"] for k in ("temp_c", "rain_mm", "soil_moisture_july") if prov[k]["note"]],
            "crops": {c: {"score": v["percent"], "source": v["source"], "scenario_applied": v["scenario_applied"],
                          "water": v["checks"]["water"]} for c, v in crops.items()},
            # New fields (additive):
            "rainfall_range_mm": [min(rain_changes), max(rain_changes)],
            "stress_by_source": lines,
            "degree_days_above_10c": {"value": gdd, "normal": ngdd, "source": "NASA POWER daily mean temperature"},
            "root_zone_july_m3m3": {"value": p["root_zone_july_m3m3"], "normal": n["root_zone_july_m3m3"],
                                    "source": "GLDAS Noah 0.25 degree"},
            "stress_method": p["stress"]["method"],
        })
    return {
        "status": "CACHED",
        "note": ("Adjustments are changes from the normal year (POWER 1991-2020, IMERG 2001-2020). The 2035 view is a "
                 "stress test, not a forecast. May-Sep is the corn and soybean window."),
        "scenarios": out,
        "dry_year_check": field_profile.dry_year_check(),
    }


# ---------- plan ----------

ROTATION_DISPLAY = {
    "corn-soy-wheat plus red clover": ("corn-soy-wheat-clover", "Corn → Soy → Winter wheat + red clover",
                                       ["Corn", "Soy", "Winter wheat + red clover"]),
    "corn-soy-wheat": ("corn-soy-wheat", "Corn → Soy → Winter wheat", ["Corn", "Soy", "Winter wheat"]),
    "corn-soy": ("corn-soy", "Corn → Soy", ["Corn", "Soy"]),
    "soy-soy-wheat": ("soy-soy-wheat", "Soy → Soy → Wheat", ["Soy", "Soy", "Wheat"]),
}
BASELINE_ROTATIONS = ("continuous soybean", "continuous corn")
CROP_DISPLAY = {"corn": "Corn", "soybean": "Soy", "wheat": "Wheat"}
NOT_AVAILABLE = "not available"
REGIONAL_CSV = SEED / "regional_yields.csv"


def _period(text):
    return "period not stated in source" if "not stated" in (text or "") else text


def regional_yields():
    """Regional (not trial) yields, e.g. Essex or Ontario winter wheat. Used only
    for quantity and revenue, never for the trial yield index."""
    out = {}
    if REGIONAL_CSV.exists():
        with open(REGIONAL_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("verification") == "VERIFIED" and r.get("bu_ac"):
                    out[r["crop"]] = {"value": float(r["bu_ac"]), "geography": r["geography"], "year": r["year"],
                                      "source": r["source"], "note": r.get("note", ""),
                                      "calc": r.get("calc", "")}
    return out


@functools.lru_cache(maxsize=1)
def longterm_yields():
    """Long-term trial averages (Agomoh et al. 2020 and 2021), converted to bu/ac.
    Shown beside the 5-year figures; never mixed into the trial yield index."""
    out = {}
    with open(SEED / "harrow_trial_yields.csv", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("verification") == "LONGTERM" and r.get("unit") == "bu/ac":
                out[(r["rotation"], r["crop"])] = {"value": float(r["value"]), "source": r["source"],
                                                   "period": r["period"], "calc": r["note"]}
    return out


def _evidence(crop, result, regional):
    """Every yield we have for one crop in one rotation, best first:
    5-year trial, long-term trial, then regional average."""
    out = []
    ref = (result.get("yield_references") or {}).get(crop)
    if ref:
        out.append({"value": ref["value"], "kind": "trial", "label": "trial",
                    "status": "DERIVED" if ref.get("verification") == "DERIVED" else "SOURCED",
                    "source": f"{ref['source']} ({_period(ref['period'])})",
                    "calc": ref["note"] if ref.get("verification") == "DERIVED"
                    else f"{ref['value']:g} bu/ac as stated in the source"})
    lt = longterm_yields().get((result["name"], crop))
    if lt:
        out.append({"value": lt["value"], "kind": "trial_longterm", "label": "long-term trial",
                    "status": "SOURCED", "source": f"{lt['source']} ({lt['period']})", "calc": lt["calc"]})
    reg = regional.get(crop)
    if reg:
        out.append({"value": reg["value"], "kind": "regional", "label": "regional average",
                    "status": "REGIONAL", "source": f"{reg['source']} ({reg['geography']}, {reg['year']})",
                    "calc": reg["calc"] or f"{reg['value']:g} bu/ac as published"})
    return out


def _yields(result, regional):
    out = []
    names = {"trial": "", "trial_longterm": " (long-term trial average)", "regional": " (regional average, not trial)"}
    for crop in dict.fromkeys(result["crops"]):
        ev = _evidence(crop, result, regional)
        if not any(e["kind"] != "regional" for e in ev):
            out.append({"crop": CROP_DISPLAY[crop], "bu_ac": None, "status": "MISSING", "storage": "CACHED",
                        "evidence": "none", "source": "No trial yield for this crop in this rotation",
                        "calc": "Not available, not estimated"})
        for e in ev:
            out.append({"crop": CROP_DISPLAY[crop] + names[e["kind"]], "bu_ac": e["value"], "status": e["status"],
                        "storage": "CACHED", "evidence": e["kind"], "source": e["source"], "calc": e["calc"]})
    return out


def _yield_for(crop, result, regional):
    """Best single yield for ranking and revenue: trial, then long-term trial, then regional."""
    ev = _evidence(crop, result, regional)
    return (ev[0]["value"], ev[0]["kind"]) if ev else (None, None)


def _revenue(result, regional, prices):
    """Gross revenue per acre per year over the rotation. Needs a yield and a dated
    price for every crop year. Uses the best available yield for each crop."""
    crops = result["crops"]
    parts, kinds = [], set()
    for crop in crops:
        y, kind = _yield_for(crop, result, regional)
        if y is None or crop not in prices:
            return None, f"not available: no yield for {CROP_DISPLAY[crop].lower()} in this rotation"
        kinds.add(kind)
        parts.append((crop, y, prices[crop]["value"]))
    total = sum(y * p for _, y, p in parts) / len(crops)
    calc = " + ".join(f"{CROP_DISPLAY[c]} {y:g} x {p:.2f}" for c, y, p in parts) + \
        f", divided by {len(crops)} years = {total:.0f} CAD/ac/yr."
    notes = {"trial_longterm": " Uses a long-term trial average for at least one crop.",
             "regional": " Uses a regional average (not a trial yield) for at least one crop."}
    return f"{total:.0f} CAD/ac/yr gross", calc + "".join(notes[k] for k in sorted(kinds) if k in notes)


def _quantity(crop, need_bu, result, regional):
    if crop is None or need_bu is None:
        return None
    name = stress.MODEL2_TO_API[crop]
    ev = _evidence(crop, result, regional)
    trial = [e for e in ev if e["kind"] != "regional"]
    use = trial or ev
    years, total_years = result["crops"].count(crop), len(result["crops"])
    if not use:
        return {"crop": name, "need_bu_ac": need_bu, "trial_bu_ac": None, "meets": None, "shortfall_bu_ac": None,
                "evidence": "none", "text": "not available: no yield for this crop in this rotation",
                "calc": "Not available, not estimated"}
    checks = []
    for e in use:
        ok = e["value"] >= need_bu
        checks.append({"label": e["label"], "bu_ac": e["value"], "meets": ok,
                       "shortfall_bu_ac": None if ok else round(need_bu - e["value"], 1),
                       "per_year_average_bu_ac": round(e["value"] * years / total_years, 1)})
    meets = True if all(c["meets"] for c in checks) else False if not any(c["meets"] for c in checks) else None
    text = "; ".join((f"{c['label']} {c['bu_ac']:g} bu/ac meets {need_bu:g}" if c["meets"]
                      else f"{c['label']} {c['bu_ac']:g} bu/ac, short by {c['shortfall_bu_ac']:g}") for c in checks)
    verdict = "Yes" if meets else "No" if meets is False else "Depends on the figure"
    first = checks[0]
    return {"crop": name, "need_bu_ac": need_bu, "meets": meets, "checks": checks,
            "trial_bu_ac": first["bu_ac"] if trial else None,
            "regional_bu_ac": None if trial else first["bu_ac"],
            "shortfall_bu_ac": first["shortfall_bu_ac"], "evidence": use[0]["kind"],
            "crop_years": f"{years} of {total_years}",
            "per_year_average_bu_ac": first["per_year_average_bu_ac"],
            "text": f"{verdict}: {text}",
            "calc": (" ; ".join(f"{c['bu_ac']:g} {'>=' if c['meets'] else '<'} {need_bu:g}" for c in checks)
                     + f". Per acre in a year you grow {name} ({years} of {total_years} years). Averaged over every "
                     f"year of the rotation: " + ", ".join(f"{c['bu_ac']:g} x {years}/{total_years} = "
                                                          f"{c['per_year_average_bu_ac']:g}" for c in checks)
                     + " bu/ac/yr. Normal-year averages, not drought yields.")}


def _score_calc(result):
    b = result["breakdown"]
    parts = b["trial_index_by_crop"]
    if not parts:
        return "No trial yield for any crop in this rotation, so no index"
    best = b["trial_best_yield"]
    refs = result["yield_references"]
    terms = [f"{CROP_DISPLAY[c]} {refs[c]['value']:g}/{best[c]:g} x 100 = {v:g}" for c, v in parts.items()]
    return f"({'; '.join(terms)}) averaged = {result['overall_percent']:g}" + (
        f". Left out, no trial yield: {', '.join(CROP_DISPLAY[c] for c in b['trial_index_excluded'])}"
        if b["trial_index_excluded"] else "")


def _gain_calc(result):
    gains = result["breakdown"].get("trial_gain_vs_continuous_pct") or {}
    refs = result["yield_references"]
    trial = rotation.load_trial_yields()
    _, cont = rotation.trial_index(trial)
    return "; ".join(f"{CROP_DISPLAY[c]} ({refs[c]['value']:g} - {cont[c]:g}) / {cont[c]:g} = {g:+g}%"
                     for c, g in gains.items())


def _reason(result, scenario):
    b = result["breakdown"]
    parts = []
    if result["overall_percent"] is not None:
        parts.append(f"Trial yield index {result['overall_percent']:g} (100 = best trial yield for that crop).")
        if b["trial_index_excluded"]:
            parts.append("Not in the index, no trial yield: "
                         + ", ".join(CROP_DISPLAY[c] for c in b["trial_index_excluded"]) + ".")
    gains = b.get("trial_gain_vs_continuous_pct") or {}
    if gains:
        parts.append("Trial gain over continuous cropping: "
                     + ", ".join(f"{CROP_DISPLAY[c]} {g:+g} percent" for c, g in gains.items()) + ".")
    if b["average_suitability"] is not None:
        parts.append(f"Average GAEZ suitability {b['average_suitability']:.1f} ({scenario} view).")
    return " ".join(parts)


@app.get("/api/rotation/{field_id}")
def rotation_scores(field_id: str, scenario: str = Query("normal"),
                    must_grow: Optional[str] = Query(None, description="soybean, maize (corn) or wheat"),
                    need_bu: Optional[float] = Query(None, gt=0, description="bu/ac target for the must_grow crop")):
    _field(field_id)
    scenario = _scenario(scenario)
    ps = profiles()
    suit = suitability.score_crops(ps[scenario], scenario)
    suit_normal = suitability.score_crops(ps["normal"], "normal")
    suit_dry = suitability.score_crops(ps["dry"], "dry")
    results = {r["name"]: r for r in rotation.rank_rotations(suit, scenario=scenario, label="CACHED",
                                                              scoring_policy="trial_yield_index")}
    evidence = stress.drought_evidence()
    regional = regional_yields()
    prices = rotation.load_prices()
    crop = stress.normalise_crop(must_grow) if must_grow else None
    changes = [l["rain_change_mm"] for l in _stress_lines(ps["dry"], ps["normal"]) if l["rain_change_mm"] is not None]
    dry_label = (f"2012 dry year: {-max(changes):.0f} to {-min(changes):.0f} mm less May-Sep rain than normal across "
                 f"IMERG and POWER, {ps['dry']['temp_c'] - ps['normal']['temp_c']:.2f} C warmer")

    rotations, message = [], None
    for name, (rid, display, crops) in ROTATION_DISPLAY.items():
        res = results[name]
        if must_grow and (crop is None or crop not in res["crops"]):
            continue
        revenue, revenue_calc = _revenue(res, regional, prices)
        picked = [e for e in _evidence(crop, res, regional) if e["kind"] != "regional"] if crop else []
        picked_yield, picked_kind = (picked[0]["value"], "trial") if picked else (None, None)
        rotations.append({
            "id": rid, "name": display, "crops": crops,
            "rank": None, "score": res["overall_percent"],
            "soil_score": None, "water_score": None,
            "revenue": revenue, "profit": None,
            "yields": _yields(res, regional), "reason": _reason(res, scenario),
            "status": "CACHED",
            # New fields (additive):
            "rank_normal": None, "rank_dry": None, "rank_for_crop": None,
            "score_kind": "trial yield index: trial yield / best trial yield for that crop x 100",
            "score_calc": _score_calc(res),
            "trial_gain_vs_continuous_pct": {stress.MODEL2_TO_API[c]: g for c, g in
                                             res["breakdown"]["trial_gain_vs_continuous_pct"].items()},
            "gain_calc": _gain_calc(res),
            "revenue_calc": revenue_calc,
            "normal": {"water": stress.water_range(res["crops"], suit_normal),
                       "label": "Normal year: POWER 1991-2020 and IMERG 2001-2020"},
            "dry": {"water": stress.water_range(res["crops"], suit_dry),
                    "drought": stress.drought_line(res["crops"], evidence),
                    "label": dry_label},
            "soil": res["soil"]["text"] if res.get("soil") else NOT_AVAILABLE,
            "soil_source": res["soil"]["source"] if res.get("soil") else None,
            "quantity": _quantity(crop, need_bu, res, regional),
            "picked_crop_yield_bu_ac": picked_yield,
            "picked_crop_evidence": picked_kind or ("none" if crop else None),
        })
    if must_grow and crop is None:
        message = f"No rotation in our trial data includes '{must_grow}'. Choose soybean, maize or wheat."
    elif must_grow and not rotations:
        message = f"No rotation in our trial data includes {must_grow}."

    normal_order = sorted(rotations, key=lambda r: (r["score"] is None, -(r["score"] or 0)))
    for i, r in enumerate(normal_order, 1):
        r["rank_normal"] = i if r["score"] is not None else None
    dry_ranks = stress.dry_rank(rotations)
    for r in rotations:
        r["rank_dry"] = dry_ranks[r["id"]]
    if crop:
        # Picked crop first: its trial yield (missing goes last), then the dry-year evidence.
        order = sorted(rotations, key=lambda r: (r["picked_crop_evidence"] != "trial",
                                                 -(r["picked_crop_yield_bu_ac"] or 0) if r["picked_crop_evidence"] == "trial" else 0,
                                                 r["rank_dry"]))
        for i, r in enumerate(order, 1):
            r["rank_for_crop"] = i
            r["rank"] = i
        ranking = (f"rank = rank_for_crop: ordered by the {stress.MODEL2_TO_API[crop]} trial yield in each rotation. "
                   "Rotations with no trial yield for that crop come last. Ties use the dry-year rank.")
    else:
        for r in rotations:
            r["rank"] = r["rank_dry"]
        ranking = ("rank = rank_dry: drought-year evidence first (low end of Bowles et al. 2020), then how much of "
                   "the crop water need 2012 rain covered, then the trial yield index.")
    rotations.sort(key=lambda r: r["rank"])

    baseline_yields = []
    for name in BASELINE_ROTATIONS:
        res = results[name]
        for y in _yields(res, regional):
            baseline_yields.append({**y, "crop": f"Continuous {y['crop'].lower()}",
                                    "soil": res["soil"]["text"] if res.get("soil") else NOT_AVAILABLE,
                                    "quantity": _quantity(crop, need_bu, res, regional)
                                    if crop in res["crops"] else None})
    price_note = ", ".join(f"{c} {p['value']:.2f} CAD/bu" for c, p in prices.items())
    first = next(iter(prices.values()))
    km = _km((field_config()["lat"], field_config()["lon"]), (TRIAL_SITE["lat"], TRIAL_SITE["lon"]))
    return {
        "status": "CACHED",
        "prices_verified": True,
        "method": (f"Scenario: {scenario}. Score is the trial yield index. Trial yields come from the long-term "
                   f"rotation trial at Woodslee, about {km:.0f} km from the field. Prices: {price_note}, "
                   f"{first['period']} Ontario averages ({first['source']}). Revenue is gross and shown only when "
                   "every crop year has a yield. No profit: costs not verified."),
        "rotations": rotations,
        "baseline": {"id": "continuous", "name": "Continuous cropping comparator", "yields": baseline_yields},
        # New fields (additive):
        "scenario": scenario,
        "must_grow": stress.MODEL2_TO_API.get(crop) if crop else (must_grow or None),
        "need_bu": need_bu,
        "message": message,
        "ranking": ranking,
        "regional_yields": regional,
        "crop_calendar": field_profile.CROP_CALENDAR,
        "soil_carbon": field_profile.SOIL_CARBON,
    }


# ---------- other crops (suitability only) ----------

OTHER_CROPS_CSV = SEED / "other_crops.csv"


def _kaggle_envelopes():
    out = {}
    with open(SEED / "kaggle_crop_recommendation.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            e = out.setdefault(r["label"], {"temperature": [], "humidity": [], "ph": []})
            for k in e:
                e[k].append(float(r[k]))
    return {lab: {k: (min(v), max(v)) for k, v in e.items()} for lab, e in out.items()}


def _gaez_extra():
    with open(SEED / "gaez_harrow_extra.csv", encoding="utf-8", newline="") as f:
        return {r["code"]: r for r in csv.DictReader(f)}


@app.get("/api/crops/{field_id}")
def other_crops(field_id: str):
    """Suitability only. No rotation, yield or revenue claims for these crops."""
    _field(field_id)
    p = profiles()["normal"]
    harrow = {"temperature": p["temp_c"], "humidity": p["humidity_pct"], "ph": p["ph"]}
    env = _kaggle_envelopes()
    gaez = _gaez_extra()
    rows = []
    if OTHER_CROPS_CSV.exists():
        with open(OTHER_CROPS_CSV, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        g = gaez.get(r["gaez_code"]) if r.get("gaez_code") else None
        k = env.get(r["kaggle_label"]) if r.get("kaggle_label") else None
        kaggle = None
        if k:
            checks = {v: {"harrow": round(harrow[v], 1), "kaggle_range": [round(k[v][0], 1), round(k[v][1], 1)],
                          "inside": k[v][0] <= harrow[v] <= k[v][1]} for v in harrow}
            kaggle = {"inside_count": sum(c["inside"] for c in checks.values()), "of": len(checks), "checks": checks,
                      "note": ("Harrow May-Sep temperature and humidity and soil pH against the range where this crop "
                               "appears in the Kaggle data (mostly India). Rainfall is not used because its period is unknown.")}
        out.append({
            "crop": r["crop"], "group": r["group"], "kaggle_label": r.get("kaggle_label") or None,
            "gaez": None if not g else {"code": g["code"], "name": g["crop"],
                                         "si_2001_2020": float(g["si_2001_2020"]),
                                         "si_2021_2040_ssp370": float(g["si_2021_2040_ssp370"]),
                                         "source": g["code_list_source"], "note": r.get("gaez_note", "")},
            "kaggle_climate_check": kaggle,
            "ontario_status": r["ontario_status"], "ontario_source": r.get("ontario_source") or None,
            "rotation_crop": r["rotation_crop"],
            "evidence_note": r.get("evidence_note") or None, "evidence_source": r.get("evidence_source") or None,
            "label": "suitability only: no Ontario rotation yield, so no rotation, bushels or revenue",
        })
    return {"status": "CACHED", "field_id": field_id, "crops": out,
            "harrow_profile": {k: round(v, 1) for k, v in harrow.items()},
            "note": ("Suitability only. GAEZ v5 Suitability Index 0-100 (rain-fed, high input) at the field pixel, "
                     "plus a Kaggle climate check. Rotation picks stay limited to corn, soybean and wheat, the crops "
                     "with Ontario rotation trial evidence.")}


# Serve the frontend on the same origin so ?api=1 works: /frontend/
app.mount("/frontend", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
