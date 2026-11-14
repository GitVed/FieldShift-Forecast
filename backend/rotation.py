"""Model 2 skeleton: rotation scorer. Owner is Vedant.

STATUS: skeleton. It fixes the input and output shape (see TASKS.md V3) so
Ved's app.py and Shlok's screens can build against it. Scoring rules are NOT
defined yet, so overall_percent is None and status is "pending rules".

Rules (CLAUDE.md): rule based, no ML. Every term must trace to a dataset or
paper. Do not invent numbers. Mark anything missing UNVERIFIED.

Formula from the docs:
  overall = average crop suitability + rotation benefit - soil penalty
  yield   = Harrow trial baseline x rotation multiplier x climate adjustment
  revenue = yield x price (price and date stated)
"""

CROP_ALIASES = {"maize": "corn", "soy": "soybean"}

# Rotations that have Harrow trial numbers (SUMMARY-README section 5).
# Crops are listed per year, so repeats count in the average.
# Red clover has no suitability source, so it is not in the average.
# Whether that is right is an open question for Vedant (TASKS V3).
ROTATIONS = {
    "continuous soybean": ["soybean"],
    "soy-soy-wheat": ["soybean", "soybean", "wheat"],
    "corn-soy-wheat": ["corn", "soybean", "wheat"],
    "corn-soy-wheat plus red clover": ["corn", "soybean", "wheat"],
    "continuous corn": ["corn"],
    "corn-soy": ["corn", "soybean"],
}


def _normalise(suitability):
    return {CROP_ALIASES.get(c, c): v for c, v in suitability.items()}


def rank_rotations(suitability, scenario="normal", label="SAMPLE"):
    """Return a list of rotation dicts. See the contract in TASKS.md V3.

    suitability: dict from suitability.score_crops(). Each value has
    "percent" (number or None) and "source".
    """
    suit = _normalise(suitability)
    out = []
    for name, crops in ROTATIONS.items():
        percents = [(suit.get(c) or {}).get("percent") for c in crops]
        missing = sorted({c for c, p in zip(crops, percents) if p is None})
        if missing:
            status, avg = "not scored", None
        else:
            status, avg = "pending rules", sum(percents) / len(percents)
        out.append({
            "name": name,
            "crops": crops,
            "status": status,
            "not_scored_crops": missing,
            "overall_percent": None,
            "breakdown": {
                "average_suitability": avg,
                "rotation_benefit": "UNVERIFIED (rule not defined)",
                "soil_penalty": "UNVERIFIED (rule not defined)",
            },
            "yield_bu_ac": {c: "UNVERIFIED" for c in dict.fromkeys(crops)},
            "revenue_per_ac": "price not chosen",
            "scenario": scenario,
            "label": label,
        })
    return out


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import suitability

    suit = suitability.score_crops(suitability.SAMPLE_PROFILE, "normal")
    print("Model 2 skeleton on SAMPLE suitability. No scoring rules yet.\n")
    for r in rank_rotations(suit):
        avg = r["breakdown"]["average_suitability"]
        avg = "n/a" if avg is None else f"{avg:.0f}"
        extra = f" (missing: {', '.join(r['not_scored_crops'])})" if r["not_scored_crops"] else ""
        print(f"{r['name']:34} {r['status']:14} avg suitability: {avg:>3}{extra}")
