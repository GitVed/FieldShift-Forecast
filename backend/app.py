"""FastAPI skeleton (V4). Owner is Ved.

STATUS: serves SAMPLE data in the shape of frontend/sample_data.json (Shlok).
  GET /api/pilot                 -> the "pilot" object
  GET /api/rotation/{field_id}   -> the "plan" object (query: scenario)

The profile is a placeholder until Dev's cached POWER and SoilGrids CSVs
exist. The demo reads cache and never calls an API.

Run from the repo root:  uvicorn backend.app:app --reload
Dev adds /api/trend and /api/series later (D5).
"""
import csv
import json
import os
import sys

from fastapi import FastAPI, HTTPException, Query

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotation  # noqa: E402  (Vedant's file)
import suitability  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FIXTURE = os.path.join(ROOT, "frontend", "sample_data.json")
SCENARIOS = ("normal", "dry", "2035_dry")

app = FastAPI(title="FieldShift Forecast API")


def load_field():
    with open(os.path.join(HERE, "field_config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_fixture_pilot():
    """Geometry, cell_id, region and layer notes come from Shlok's SAMPLE
    fixture. There is no confirmed field polygon yet (Vedant confirms)."""
    try:
        with open(FIXTURE, encoding="utf-8") as f:
            return json.load(f)["pilot"]
    except (OSError, KeyError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"frontend/sample_data.json not usable: {e}")


@app.get("/api/pilot")
def pilot():
    field = load_field()
    fx = load_fixture_pilot()
    return {
        "field_id": field["field_id"],
        "cell_id": fx["cell_id"],
        "name": field["name"],
        "region": fx["region"],
        "soil": field["soil_type"],
        "center": {"lat": field["lat"], "lon": field["lon"]},
        "coordinate_status": field["coordinates_status"] + " Polygon is SAMPLE geometry.",
        "polygon": fx["polygon"],
        "layers": fx["layers"],
    }


# Display names for the Plan screen. Same style as sample_data.json.
ROTATION_DISPLAY = {
    "corn-soy-wheat plus red clover": ("corn-soy-wheat-clover", "Corn → Soy → Winter wheat + red clover",
                                       ["Corn", "Soy", "Winter wheat + red clover"]),
    "corn-soy-wheat": ("corn-soy-wheat", "Corn → Soy → Winter wheat", ["Corn", "Soy", "Winter wheat"]),
    "corn-soy": ("corn-soy", "Corn → Soy", ["Corn", "Soy"]),
    "soy-soy-wheat": ("soy-soy-wheat", "Soy → Soy → Wheat", ["Soy", "Soy", "Wheat"]),
}
BASELINE_ROTATIONS = ("continuous soybean", "continuous corn")
CROP_DISPLAY = {"corn": "Corn", "soybean": "Soy", "wheat": "Wheat"}


def trial_yields(rotation_names):
    """bu/ac rows from the trial CSV for the named rotations.
    Interim: Vedant's rotation.py will supply yields later.
    The crop comes from the CSV. If the CSV says UNVERIFIED, we say so."""
    path = os.path.join(ROOT, load_field()["trial_file"])
    out = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["rotation"] in rotation_names and row["unit"] == "bu/ac":
                crop = CROP_DISPLAY.get(row["crop"], "Crop not stated (UNVERIFIED)")
                out.append({
                    "crop": crop,
                    "bu_ac": float(row["value"]) if "." in row["value"] else int(row["value"]),
                    "status": "UNVERIFIED",
                    "source": f"{row['source']}. Not yet verified. {row['note']}".strip(),
                })
    return out


def reason_text(result):
    avg = result["breakdown"]["average_suitability"]
    if avg is None:
        return "Not scored. A crop in this rotation has no suitability value."
    text = (f"Average crop suitability {avg:.0f} on a SAMPLE profile. "
            "Rotation benefit and soil penalty are not defined yet.")
    return text


@app.get("/api/rotation/{field_id}")
def rotation_scores(field_id: str, scenario: str = Query("normal")):
    field = load_field()
    if field_id != field["field_id"]:
        raise HTTPException(status_code=404, detail=f"Unknown field_id {field_id}")
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=422, detail=f"scenario must be one of {SCENARIOS}")

    # SAMPLE profile. Scenario changes to temperature and rain will come from
    # Dev's trend.py. Until then the profile is the same for every scenario.
    suit = suitability.score_crops(suitability.SAMPLE_PROFILE, scenario)
    results = {r["name"]: r for r in rotation.rank_rotations(suit, scenario=scenario, label="SAMPLE")}
    baseline_crops = [c for c, v in suit.items() if v["percent"] is not None and not v["scenario_applied"]]

    rotations = []
    for name, (rid, display, crops) in ROTATION_DISPLAY.items():
        res = results[name]
        reason = reason_text(res)
        if "corn" in res["crops"] and "maize" in baseline_crops:
            reason += " Corn is the GAEZ baseline, dry scenario not applied."
        rotations.append({
            "id": rid,
            "name": display,
            "crops": crops,
            "rank": None,               # ranking waits for the Model 2 rules
            "score": res["overall_percent"],
            "soil_score": None,
            "water_score": None,
            "revenue": None,            # no price source chosen
            "profit": None,
            "yields": trial_yields((name,)),
            "reason": reason,
        })

    return {
        "status": "SAMPLE",
        "prices_verified": False,
        "method": (f"Scenario: {scenario}. SAMPLE profile, not Harrow data. Trial yields are UNVERIFIED. "
                   "Rank, score and revenue are withheld until the Model 2 rules and a price source exist."),
        "rotations": rotations,
        "baseline": {
            "id": "continuous",
            "name": "Continuous cropping comparator",
            "yields": trial_yields(BASELINE_ROTATIONS),
        },
    }
