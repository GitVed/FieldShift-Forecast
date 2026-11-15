"""Model 1, field profile and API tests (Ved). Run: python -m pytest tests"""
import csv
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend import field_profile, suitability
from backend.app import app

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "frontend" / "sample_data.json").read_text(encoding="utf-8"))


class Model1Tests(unittest.TestCase):
    def test_gaez_periods_are_read_separately(self):
        base = suitability.load_gaez()
        future = suitability.load_gaez(scenario=suitability.GAEZ_PERIODS["future"])
        self.assertEqual(base, {"wheat": 97.91, "soybean": 53.71, "maize": 97.91})
        self.assertEqual(future, {"wheat": 97.91, "soybean": 62.55, "maize": 93.49})

    def test_scenario_sources(self):
        p = suitability.SAMPLE_PROFILE
        normal = suitability.score_crops(p, "normal")
        dry = suitability.score_crops(p, "dry")
        future = suitability.score_crops(p, "2035_dry")
        self.assertEqual(normal["soybean"]["percent"], 53.71)
        self.assertTrue(all(v["scenario_applied"] for v in normal.values()))
        # Dry year: no sourced response, so baseline shown and flagged.
        self.assertTrue(all(not v["scenario_applied"] for v in dry.values()))
        self.assertTrue(all(v["source"] == suitability.DRY_BASELINE_LABEL for v in dry.values()))
        # 2035: GAEZ future period.
        self.assertEqual(future["soybean"]["percent"], 62.55)
        self.assertEqual(future["maize"]["percent"], 93.49)

    def test_missing_gaez_is_not_scored_never_invented(self):
        r = suitability.score_crops(suitability.SAMPLE_PROFILE, "normal", gaez={}, gaez_future={})
        for v in r.values():
            self.assertIsNone(v["percent"])
            self.assertEqual(v["label"], "UNVERIFIED")

    def test_unknown_scenario_rejected(self):
        with self.assertRaises(ValueError):
            suitability.score_crops(suitability.SAMPLE_PROFILE, "wet")

    def test_water_check(self):
        w = suitability.water_check("maize", {"rain_mm": 400})
        self.assertEqual(w["covers_pct"], [50, 80])           # 400/800, 400/500
        self.assertEqual(w["status"], "rain below need")
        self.assertIsNone(suitability.water_check("wheat", {"rain_mm": 400})["covers_pct"])

    def test_no_unsourced_ranges_left(self):
        self.assertFalse(hasattr(suitability, "RANGES"))
        self.assertFalse(hasattr(suitability, "range_fit"))


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = field_profile.build_scenarios()

    def test_all_cached_with_provenance(self):
        for p in self.s.values():
            self.assertEqual(p["label"], "CACHED")
            for item in p["provenance"].values():
                self.assertTrue(item["source_id"])
                self.assertTrue(item["window"])

    def test_dry_year_is_drier_than_normal(self):
        self.assertLess(self.s["dry"]["rain_mm"], self.s["normal"]["rain_mm"])

    def test_2035_applies_only_the_temperature_trend(self):
        trend = field_profile.temperature_trend()
        shift = trend["slope_per_decade"] * (field_profile.TARGET_YEAR - field_profile.DRY_YEAR) / 10
        self.assertAlmostEqual(self.s["2035_dry"]["temp_c"], round(self.s["dry"]["temp_c"] + shift, 3), places=2)
        self.assertEqual(self.s["2035_dry"]["rain_mm"], self.s["dry"]["rain_mm"])

    def test_soil_is_hwsd_regional_estimate(self):
        self.assertEqual(self.s["normal"]["ph"], 6.7)
        self.assertIn("regional", self.s["normal"]["provenance"]["soil_ph"]["label"])


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(app)   # no context manager: lifespan seeding not needed here

    def test_pilot_has_fixture_keys(self):
        j = self.c.get("/api/pilot").json()
        self.assertTrue(set(FIXTURE["pilot"]) <= set(j))
        self.assertEqual(j["center"], {"lat": 42.0356, "lon": -82.9183})

    def test_detect_shape_and_real_verdict(self):
        j = self.c.get("/api/detect/harrow-power").json()
        self.assertTrue(set(FIXTURE["detect"]) <= set(j))
        self.assertEqual(j["status"], "CACHED")
        self.assertIn("Temperature increasing", j["verdict"])

    def test_predict_ids_match_frontend(self):
        j = self.c.get("/api/predict/harrow").json()
        self.assertEqual([s["id"] for s in j["scenarios"]], [s["id"] for s in FIXTURE["predict"]["scenarios"]])
        normal = j["scenarios"][0]
        self.assertEqual((normal["temp"], normal["rainfall"]), (0.0, 0.0))

    def test_plan_shape_every_scenario(self):
        for scenario in ("normal", "dry", "2035_dry", "future"):
            r = self.c.get(f"/api/rotation/harrow?scenario={scenario}")
            self.assertEqual(r.status_code, 200, scenario)
            j = r.json()
            self.assertTrue(set(FIXTURE["plan"]) <= set(j))
            fx_rot = FIXTURE["plan"]["rotations"][0]
            for rot in j["rotations"]:
                self.assertTrue(set(fx_rot) <= set(rot))

    def test_only_verified_yields_shown(self):
        with open(ROOT / "data" / "seed" / "harrow_trial_yields.csv", encoding="utf-8-sig", newline="") as f:
            verified = {float(r["value"]) for r in csv.DictReader(f)
                        if r.get("verification") == "VERIFIED" and r["unit"] == "bu/ac"}
        j = self.c.get("/api/rotation/harrow").json()
        shown = [y["bu_ac"] for rot in j["rotations"] for y in rot["yields"]] + \
                [y["bu_ac"] for y in j["baseline"]["yields"]]
        for v in shown:
            if v is not None:
                self.assertIn(v, verified)

    def test_bad_inputs(self):
        self.assertEqual(self.c.get("/api/rotation/nope").status_code, 404)
        self.assertEqual(self.c.get("/api/rotation/harrow?scenario=wet").status_code, 422)
        self.assertEqual(self.c.get("/api/detect/elsewhere").status_code, 404)


if __name__ == "__main__":
    unittest.main()
