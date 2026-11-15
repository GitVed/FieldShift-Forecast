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
        self.assertEqual(w["status"], "rain below need in at least one source")
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

    def test_soil_is_soilgrids_at_the_field(self):
        p = self.s["normal"]
        self.assertEqual(p["ph"], 6.6)                       # SoilGrids 0-30 cm at the cropland point
        self.assertIn("modelled", p["provenance"]["soil_ph"]["label"])
        self.assertAlmostEqual(p["sand"] + p["silt"] + p["clay"], 100, delta=0.5)
        self.assertEqual(field_profile.soil_hwsd2()["ph"]["value"], 6.7)   # HWSD2 kept as cross-check

    def test_two_nasa_rain_sources_and_stress_facts(self):
        n, d = self.s["normal"], self.s["dry"]
        self.assertIsNotNone(n["rain_mm_imerg"])
        self.assertLess(d["rain_mm_imerg"], n["rain_mm_imerg"])       # IMERG agrees 2012 was drier
        self.assertGreater(d["stress"]["degree_days_above_10c"], n["stress"]["degree_days_above_10c"])
        self.assertEqual(set(d["stress"]["sources"]), {"power", "imerg"})
        self.assertLess(d["root_zone_july_m3m3"]["40-100 cm"], n["root_zone_july_m3m3"]["40-100 cm"])

    def test_soil_carbon_from_trial_not_hwsd(self):
        p = self.s["normal"]
        self.assertNotIn("soil_organic_carbon", p["provenance"].get("soil_soil_organic_carbon", {}))
        self.assertNotIn("soil_organic_carbon", [k[5:] for k in p["provenance"] if k.startswith("soil_") and k != "soil_organic_carbon"])
        self.assertEqual(p["provenance"]["soil_organic_carbon"]["value"], "2.0 to 2.25")
        self.assertIsNone(p["nitrogen"])

    def test_crop_calendar_window_is_corn_and_soy_only(self):
        self.assertIn("OMAFRA 2017", field_profile.CROP_CALENDAR["source"])
        self.assertIsNone(suitability.water_check("wheat", {"rain_mm": 400})["covers_pct"])


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(app)   # no context manager: lifespan seeding not needed here

    def test_pilot_has_fixture_keys(self):
        j = self.c.get("/api/pilot").json()
        self.assertTrue(set(FIXTURE["pilot"]) <= set(j))
        self.assertEqual(j["center"], {"lat": 42.0337, "lon": -82.9287})   # cropland point (ESA WorldCover)
        self.assertEqual(j["polygon_status"], "SAMPLE")
        self.assertEqual(j["previous_point"]["lat"], 42.0356)

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
                        if r.get("verification") in ("VERIFIED", "DERIVED", "LONGTERM") and r["unit"] == "bu/ac"}
        with open(ROOT / "data" / "seed" / "regional_yields.csv", encoding="utf-8", newline="") as f:
            verified |= {float(r["bu_ac"]) for r in csv.DictReader(f) if r["verification"] == "VERIFIED"}
        j = self.c.get("/api/rotation/harrow").json()
        shown = [y["bu_ac"] for rot in j["rotations"] for y in rot["yields"]] + \
                [y["bu_ac"] for y in j["baseline"]["yields"]]
        for v in shown:
            if v is not None:
                self.assertIn(v, verified)

    def test_pilot_polygon_is_sample_and_trial_is_a_point(self):
        j = self.c.get("/api/pilot").json()
        self.assertEqual(j["polygon_status"], "SAMPLE")
        self.assertEqual(j["trial_site"]["kind"], "point")

    def test_trial_index_and_gains(self):
        rots = {r["id"]: r for r in self.c.get("/api/rotation/harrow").json()["rotations"]}
        self.assertEqual(rots["corn-soy"]["trial_gain_vs_continuous_pct"], {"maize": 30.5})
        self.assertEqual(rots["corn-soy-wheat-clover"]["trial_gain_vs_continuous_pct"], {"maize": 43.2})
        self.assertEqual(rots["soy-soy-wheat"]["trial_gain_vs_continuous_pct"], {"soybean": 29.3})
        self.assertEqual(rots["corn-soy-wheat"]["trial_gain_vs_continuous_pct"]["soybean"], 56.1)
        self.assertEqual(rots["corn-soy"]["score"], 91.1)        # 154 / 169
        self.assertEqual(rots["soy-soy-wheat"]["score"], 82.8)   # 53 / 64
        self.assertIn("2.25", rots["corn-soy-wheat"]["soil"])    # soil is its own line
        self.assertEqual(rots["corn-soy"]["soil"], "not available")

    def test_wheat_only_from_sources(self):
        j = self.c.get("/api/rotation/harrow?must_grow=wheat&need_bu=70").json()
        self.assertTrue(j["rotations"])
        for r in j["rotations"]:
            for y in r["yields"]:
                if y["crop"].startswith("Wheat"):
                    self.assertIn(y["evidence"], ("trial_longterm", "regional", "none"))
            self.assertIn(r["quantity"]["evidence"], ("trial_longterm", "regional"))
        self.assertEqual(j["regional_yields"]["wheat"]["value"], 96.9)   # Essex 2025, shown separately

    def test_must_grow_filters_and_corn_alias(self):
        a = self.c.get("/api/rotation/harrow?must_grow=maize").json()
        b = self.c.get("/api/rotation/harrow?must_grow=corn").json()
        self.assertEqual([r["id"] for r in a["rotations"]], [r["id"] for r in b["rotations"]])
        self.assertNotIn("soy-soy-wheat", [r["id"] for r in a["rotations"]])
        self.assertEqual(a["must_grow"], "maize")

    def test_unknown_crop_gives_empty_list_and_message(self):
        j = self.c.get("/api/rotation/harrow?must_grow=rice").json()
        self.assertEqual(j["rotations"], [])
        self.assertIn("No rotation", j["message"])

    def test_dry_rank_first_and_drought_low_end(self):
        rots = self.c.get("/api/rotation/harrow?must_grow=maize").json()["rotations"]
        self.assertEqual([r["rank_dry"] for r in rots], sorted(r["rank_dry"] for r in rots))
        diverse = [r for r in rots if r["dry"]["drought"]["applies"]]
        self.assertTrue(diverse)
        self.assertTrue(all(r["dry"]["drought"]["loss_reduction_low_pct"] == 14 for r in diverse))
        for r in rots:
            self.assertLessEqual(r["dry"]["water"]["low_pct"], r["dry"]["water"]["high_pct"])

    def test_quantity_check(self):
        rots = {r["id"]: r for r in self.c.get("/api/rotation/harrow?must_grow=maize&need_bu=160").json()["rotations"]}
        self.assertTrue(rots["corn-soy-wheat-clover"]["quantity"]["meets"])
        self.assertFalse(rots["corn-soy"]["quantity"]["meets"])
        self.assertEqual(rots["corn-soy"]["quantity"]["shortfall_bu_ac"], 6.0)

    def test_soybean_pick_ranks_by_soybean_yield(self):
        rots = self.c.get("/api/rotation/harrow?must_grow=soybean").json()["rotations"]
        ids = [r["id"] for r in rots]
        # 5-year trial 64, 53 first; then long-term trial only 50.6 (clover) and 49.1 (corn-soy)
        self.assertEqual(ids, ["corn-soy-wheat", "soy-soy-wheat", "corn-soy-wheat-clover", "corn-soy"])
        self.assertEqual([r["picked_crop_yield_bu_ac"] for r in rots], [64.0, 53.0, 50.6, 49.1])

    def test_every_rotation_number_has_a_calculation(self):
        j = self.c.get("/api/rotation/harrow?must_grow=maize&need_bu=160").json()
        for r in j["rotations"]:
            self.assertTrue(r["score_calc"])
            self.assertIn("of 3 years" if len(r["crops"]) == 3 else "of 2 years", r["quantity"]["calc"])
            for y in r["yields"]:
                self.assertIn(y["status"], ("SOURCED", "DERIVED", "REGIONAL", "MISSING"))
                self.assertEqual(y["storage"], "CACHED")

    def test_predict_has_two_source_rain_range(self):
        dry = self.c.get("/api/predict/harrow").json()["scenarios"][1]
        lo, hi = dry["rainfall_range_mm"]
        self.assertLess(lo, hi)
        self.assertLess(hi, 0)
        self.assertEqual({x["source"] for x in dry["stress_by_source"]}, {"POWER", "IMERG"})

    def test_detect_reports_data_quality(self):
        dq = self.c.get("/api/detect/harrow").json()["data_quality"]["files"]
        self.assertEqual(dq["power_t2m_harrow_1981_2025.csv"]["usable_rows"], 540)

    def test_quantity_shows_both_trial_figures(self):
        r = {x["id"]: x for x in self.c.get("/api/rotation/harrow?must_grow=soybean&need_bu=60").json()["rotations"]}
        q = r["corn-soy-wheat"]["quantity"]
        self.assertIsNone(q["meets"])                  # 64 meets, long-term 52.0 does not
        self.assertEqual([c["bu_ac"] for c in q["checks"]], [64.0, 52.0])

    def test_revenue_has_its_arithmetic(self):
        r = self.c.get("/api/rotation/harrow").json()["rotations"][0]
        self.assertTrue(r["revenue"].endswith("CAD/ac/yr gross"))
        self.assertIn("divided by 3 years", r["revenue_calc"])

    def test_bowles_wording_is_us_only(self):
        t = self.c.get("/api/rotation/harrow").json()["rotations"][0]["dry"]["drought"]["text"]
        self.assertIn("US sites only", t)
        self.assertIn("88.9", t)

    def test_other_crops_are_suitability_only(self):
        j = self.c.get("/api/crops/harrow").json()
        crops = {c["crop"]: c for c in j["crops"]}
        self.assertEqual(len(crops), 21)                                   # every Kaggle crop except maize
        self.assertEqual(crops["Chickpea"]["gaez"]["si_2001_2020"], 75.81)
        self.assertEqual(crops["Watermelon"]["gaez"]["si_2001_2020"], 0.0)
        self.assertIsNone(crops["Lentil"]["gaez"])                        # no GAEZ v5 layer
        self.assertIn("soybean", crops["Kidney beans"]["evidence_note"])  # white mould advice
        for c in crops.values():
            self.assertIn("suitability only", c["label"])
            self.assertNotIn("yield_bu_ac", c)

    def test_bad_inputs(self):
        self.assertEqual(self.c.get("/api/rotation/nope").status_code, 404)
        self.assertEqual(self.c.get("/api/rotation/harrow?scenario=wet").status_code, 422)
        self.assertEqual(self.c.get("/api/detect/elsewhere").status_code, 404)


if __name__ == "__main__":
    unittest.main()
