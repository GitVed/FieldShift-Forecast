"""Dry-year stress, crop filter, quantity check and dry ranking. Owner: Ved.

Used by app.py for the "you pick the crop, we stress-test it" view.
General logic only: any crop name, any rotation list. The frontend picker just
passes query parameters; all filtering and ranking happens here.

Nothing here predicts a dry-year yield. No source gives one for this field.
The dry view uses two sourced things:
- Measured 2012 stress: May-Sep rain against FAO crop water need (Model 1).
- Bowles et al. 2020: in drought years, diverse rotations reduced maize yield
  LOSSES by 14 to 90 percent versus simple rotations (11 North American
  trials, not Harrow). We use the low end, 14. The numbers are read from the
  trial CSV, not typed here.
"Diverse" here means corn plus at least two other crop species. That cutoff is
our reading of the study and is UNVERIFIED.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAL_CSV = ROOT / "data" / "seed" / "harrow_trial_yields.csv"

API_NAMES = {"maize": "corn", "corn": "corn", "soybean": "soybean", "soy": "soybean", "wheat": "wheat"}
MODEL2_TO_API = {"corn": "maize", "soybean": "soybean", "wheat": "wheat"}


def normalise_crop(name):
    """Map an API or UI crop name to Model 2's name. Unknown names return None."""
    return API_NAMES.get((name or "").strip().lower())


def drought_evidence(path=TRIAL_CSV):
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["period"] == "drought years" and row.get("verification") == "VERIFIED":
                low, high = (float(x) for x in re.findall(r"\d+(?:\.\d+)?", row["value"])[:2])
                return {"low_pct": low, "high_pct": high, "source": row["source"], "note": row["note"]}
    return None


def drought_line(crops, evidence):
    species = set(crops)
    if evidence is None:
        return {"applies": False, "loss_reduction_low_pct": None, "text": "not available"}
    if "corn" not in species:
        return {"applies": False, "loss_reduction_low_pct": None,
                "text": "Not applicable: the drought study measured maize yields."}
    if len(species) < 3:
        return {"applies": False, "loss_reduction_low_pct": 0.0,
                "text": "Simple rotation: no drought-year evidence of smaller losses."}
    return {"applies": True, "loss_reduction_low_pct": evidence["low_pct"],
            "range_pct": [evidence["low_pct"], evidence["high_pct"]],
            "text": (f"Diverse rotation: drought-year maize losses {evidence['low_pct']:.0f} to "
                     f"{evidence['high_pct']:.0f} percent smaller than simple rotations. We use the low end, "
                     f"{evidence['low_pct']:.0f} percent. 11 North American trials, not Harrow."),
            "source": evidence["source"]}


def water_range(crops, suit):
    """Low-to-high share of FAO crop water need that May-Sep rain covers, over
    the rotation's crops that have a water check (not winter wheat)."""
    lows, highs, by_crop = [], [], {}
    for crop in dict.fromkeys(crops):
        model1 = suit.get("maize" if crop == "corn" else crop) or {}
        cover = ((model1.get("checks") or {}).get("water") or {}).get("covers_pct")
        if cover:
            lows.append(cover[0]); highs.append(cover[1]); by_crop[MODEL2_TO_API[crop]] = cover
    if not lows:
        return {"low_pct": None, "high_pct": None, "by_crop": {}, "text": "not available"}
    return {"low_pct": min(lows), "high_pct": max(highs), "by_crop": by_crop,
            "text": f"Rain covers {min(lows)} to {max(highs)} percent of FAO crop water need"}


def quantity(crop, need_bu, refs):
    """Compare a farmer's bu/ac target to the trial yield for that crop."""
    if need_bu is None or crop is None:
        return None
    ref = (refs or {}).get(crop)
    if not ref:
        return {"crop": MODEL2_TO_API[crop], "need_bu_ac": need_bu, "trial_bu_ac": None,
                "meets": None, "shortfall_bu_ac": None,
                "text": "not available: no verified trial yield for this crop in this rotation"}
    y = ref["value"]
    meets = y >= need_bu
    return {"crop": MODEL2_TO_API[crop], "need_bu_ac": need_bu, "trial_bu_ac": y, "meets": meets,
            "shortfall_bu_ac": None if meets else round(need_bu - y, 1),
            "verification": ref.get("verification"),
            "text": (f"Yes: trial yield {y:g} bu/ac meets {need_bu:g}" if meets
                     else f"No: trial yield {y:g} bu/ac, short by {need_bu - y:g} bu/ac"),
            "note": "Trial yield per acre in a year that crop is grown. Historical, not a forecast."}


def dry_rank(rows):
    """Rank rows (dicts with dry.drought and dry.water and score) for the dry year:
    drought evidence first (low end), then the dry-year water-cover low, then the
    trial yield index. Returns {id: rank}."""
    def key(r):
        d = r["dry"]
        return (-(d["drought"]["loss_reduction_low_pct"] or 0),
                -(d["water"]["low_pct"] if d["water"]["low_pct"] is not None else -1),
                -(r["score"] if r["score"] is not None else -1))
    ordered = sorted(rows, key=key)
    return {r["id"]: i for i, r in enumerate(ordered, 1)}
