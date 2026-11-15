"""Climate yield adjustment, calibrated on Essex County yields. Owner: Ved. (P2, Sun Nov 15)

Question: does growing-season weather explain how far Essex yields fall above or
below their long-run trend, on years the model has not seen?

Method, rule for rule:
- Yields: Essex County, OMAFA county estimates, 1981-2025 (data/seed/essex_yields.csv).
- Weather: NASA POWER monthly at the field cell. Corn and soybean use May-Sep;
  winter wheat uses Apr-Jul because it is harvested in July.
- Inputs: window rain total (mm) and degree days above 10 C from monthly means
  (the NEX projections are monthly, so training and projection use the same form).
- Remove the long-run trend (linear in year), then fit the yield anomaly
  (percent of trend) on rain and degree days by least squares.
- Test: leave one year out and leave 5-year blocks out. The trend is refit
  without the held-out years each time. Skill = 1 - error(model) / error(no change).
- Only a crop whose skill beats "no change" in both tests gets an adjustment.
  Otherwise the climate adjustment stays 1.
- Projection: apply the full-period fit to each NEX-GDDP-CMIP6 model's 2026-2040
  May-Sep (or Apr-Jul) values, giving a low-to-high range across the models. The
  range multiplies the historical trial yield. Everything here is DERIVED.
"""
import calendar
import csv
import functools
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
YEARS = list(range(1981, 2026))
WINDOW = {"corn": (5, 6, 7, 8, 9), "soybean": (5, 6, 7, 8, 9), "wheat": (4, 5, 6, 7)}
WINDOW_LABEL = {"corn": "May-Sep", "soybean": "May-Sep", "wheat": "Apr-Jul"}


def _monthly(name, variable):
    out = {}
    with open(SEED / name, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["variable"] == variable and r["quality_flag"] == "valid" and r["value"]:
                out[(int(r["date"][:4]), int(r["date"][5:7]))] = float(r["value"])
    return out


@functools.lru_cache(maxsize=1)
def essex_yields():
    out = {}
    with open(SEED / "essex_yields.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["crop"], {})[int(r["year"])] = float(r["bu_ac"])
    return out


def _features(year, months, temp, rain):
    r = sum(rain[(year, m)] for m in months)
    dd = sum(max(temp[(year, m)] - 10.0, 0.0) * calendar.monthrange(2001, m)[1] for m in months)
    return [r, dd]


def _fit(train, crop, temp, rain):
    ys = essex_yields()[crop]
    yrs = np.array(train, dtype=float)
    yv = np.array([ys[t] for t in train])
    a, b = np.polyfit(yrs, yv, 1)
    trend = a * yrs + b
    anomaly = (yv - trend) / trend
    X = np.array([[1.0] + _features(t, WINDOW[crop], temp, rain) for t in train])
    coef, *_ = np.linalg.lstsq(X, anomaly, rcond=None)
    return (a, b), coef


def _predict(coef, year, crop, temp, rain):
    return float(np.array([1.0] + _features(year, WINDOW[crop], temp, rain)) @ coef)


def _skill(crop, temp, rain, blocks):
    ys = essex_yields()[crop]
    err_m, err_z, held = [], [], {}
    for block in blocks:
        train = [y for y in YEARS if y not in block]
        (a, b), coef = _fit(train, crop, temp, rain)
        for t in block:
            trend = a * t + b
            actual = (ys[t] - trend) / trend
            pred = _predict(coef, t, crop, temp, rain)
            err_m.append((pred - actual) ** 2)
            err_z.append(actual ** 2)
            held[t] = (pred, actual)
    return 1 - np.mean(err_m) / np.mean(err_z), float(np.sqrt(np.mean(err_m))), float(np.sqrt(np.mean(err_z))), held


@functools.lru_cache(maxsize=1)
def calibration():
    temp = _monthly("power_t2m_harrow_1981_2025.csv", "temperature")
    rain = _monthly("power_precip_harrow_1981_2025.csv", "precipitation")
    out = {}
    for crop in WINDOW:
        loo, rmse_m, rmse_z, held = _skill(crop, temp, rain, [[y] for y in YEARS])
        blocks = [[y for y in range(s, s + 5) if y in YEARS] for s in range(1981, 2026, 5)]
        block, *_ = _skill(crop, temp, rain, blocks)
        _, coef = _fit(YEARS, crop, temp, rain)
        passes = bool(loo > 0 and block > 0)
        out[crop] = {
            "crop": crop, "years": f"{YEARS[0]}-{YEARS[-1]}", "n_years": len(YEARS), "window": WINDOW_LABEL[crop],
            "skill_leave_one_year_out": round(float(loo), 3), "skill_5_year_blocks": round(float(block), 3),
            "rmse_model_pct": round(100 * rmse_m, 1), "rmse_no_change_pct": round(100 * rmse_z, 1),
            "beats_no_change": passes,
            "adjustment": "applied (DERIVED)" if passes else "stays 1, model does not beat no change",
            "per_100mm_rain_pct": round(100 * 100 * float(coef[1]), 2),
            "per_100_degree_days_pct": round(100 * 100 * float(coef[2]), 2),
            "held_out_2012": {"predicted_pct": round(100 * held[2012][0], 1), "actual_pct": round(100 * held[2012][1], 1)},
            "_coef": coef,
        }
    return out


def _projected_monthly():
    """{(model, year): {'temperature': {month: v}, 'precipitation': {month: v}}} from NEX (POWER-aligned)."""
    path = SEED / "nex_adjusted_harrow.csv"
    out = {}
    if not path.exists():
        return out
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["variable"] in ("temperature", "precipitation"):
                y = int(r["date"][:4])
                out.setdefault((r["model"], y), {}).setdefault(r["variable"], {})[int(r["date"][5:7])] = float(r["value"])
    return out


@functools.lru_cache(maxsize=1)
def projections():
    """{crop: {year: {low_pct, median_pct, high_pct, models}}} for crops that pass, 2026 onward."""
    cal = calibration()
    data = _projected_monthly()
    out = {}
    for crop, c in cal.items():
        if not c["beats_no_change"]:
            continue
        by_year = {}
        for (model, year), v in data.items():
            if year < 2026 or len(v.get("temperature", {})) < 12 or len(v.get("precipitation", {})) < 12:
                continue
            temp = {(year, m): t for m, t in v["temperature"].items()}
            rain = {(year, m): p for m, p in v["precipitation"].items()}
            by_year.setdefault(year, []).append(_predict(c["_coef"], year, crop, temp, rain))
        out[crop] = {y: {"low_pct": round(100 * min(v), 1), "median_pct": round(100 * statistics.median(v), 1),
                         "high_pct": round(100 * max(v), 1), "models": len(v)}
                     for y, v in sorted(by_year.items()) if len(v) >= 3}
    return out


def public_calibration():
    return {crop: {k: v for k, v in c.items() if not k.startswith("_")} for crop, c in calibration().items()}


def adjust(crop, year, trial_bu_ac):
    """Climate-adjusted range for a historical trial yield in a projected year, or None."""
    p = projections().get(crop, {}).get(year)
    if p is None or trial_bu_ac is None:
        return None
    lo, hi = trial_bu_ac * (1 + p["low_pct"] / 100), trial_bu_ac * (1 + p["high_pct"] / 100)
    return {"low_bu_ac": round(lo, 1), "high_bu_ac": round(hi, 1), "anomaly_low_pct": p["low_pct"],
            "anomaly_high_pct": p["high_pct"], "models": p["models"], "status": "DERIVED",
            "calc": (f"{trial_bu_ac:g} bu/ac trial yield x (1 {p['low_pct']:+g}% to 1 {p['high_pct']:+g}%) "
                     f"= {lo:.0f} to {hi:.0f} bu/ac, across {p['models']} NASA climate models for {year}")}
