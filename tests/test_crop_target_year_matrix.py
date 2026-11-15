"""Crop x target x year matrix for /api/recommendations/harrow.

Proves the answer moves with the inputs: the target answer follows the
target, the rain check and corn climate range follow the year, and the
rotation list follows the crop. Trial yields themselves never change.
"""
import unittest

from fastapi.testclient import TestClient

from backend.app import app

CROPS = {"maize": "corn", "soybean": "soybean", "wheat": "wheat"}
TARGETS = [50, 60, 90, 160, 170, 200]
YEARS = [2021, 2026, 2035, 2040]


class CropTargetYearMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = TestClient(app)
        cls.data = {}
        for crop in CROPS:
            for year in YEARS:
                for target in TARGETS:
                    r = c.get(f"/api/recommendations/harrow?year={year}&must_grow={crop}&need_bu={target}")
                    assert r.status_code == 200, (crop, year, target, r.text)
                    cls.data[crop, year, target] = r.json()

    def test_every_rotation_has_the_picked_crop_and_a_target_answer(self):
        for (crop, year, target), d in self.data.items():
            self.assertTrue(d["rotations"])
            for row in d["rotations"]:
                stem = {"corn": "corn", "soybean": "soy", "wheat": "wheat"}[CROPS[crop]]
                self.assertTrue(any(stem in c.lower() for c in row["crops"]), (crop, row["crops"]))
                q = row["quantity"]
                self.assertEqual(q["need_bu_ac"], target)
                figs = [c["bu_ac"] for c in q["checks"]]
                want = "all" if min(figs) >= target else "none" if max(figs) < target else "some"
                self.assertEqual(q["target_support"], want, (crop, year, target, row["id"]))
                self.assertEqual(q["meets"], {"all": True, "none": False, "some": None}[want])

    def test_target_changes_the_answer(self):
        for crop in CROPS:
            for year in YEARS:
                answers = {t: tuple(r["quantity"]["target_support"] for r in self.data[crop, year, t]["rotations"]) for t in TARGETS}
                self.assertGreater(len(set(answers.values())), 1, (crop, year))
                low, high = self.data[crop, year, 50], self.data[crop, year, 200]
                self.assertTrue(all(r["quantity"]["target_support"] == "none" for r in high["rotations"]))
                self.assertIn("above every", high["target_position"]["text"])
                if crop == "maize":
                    self.assertIn("at or below every", low["target_position"]["text"])

    def test_target_position_matches_the_figures(self):
        for (crop, year, target), d in self.data.items():
            p = d["target_position"]
            self.assertEqual(p["target_bu_ac"], target)
            for f in p["figures"]:
                self.assertEqual(f["meets"], f["bu_ac"] >= target)

    def test_trial_yields_do_not_change_with_year(self):
        for crop in CROPS:
            for target in TARGETS:
                seen = {tuple((r["id"], r["picked_crop_yield_bu_ac"]) for r in self.data[crop, y, target]["rotations"]) for y in YEARS}
                self.assertEqual(len(seen), 1, (crop, target))

    def test_year_changes_the_rain_check(self):
        for crop in CROPS:
            checks = {y: tuple(r["planning_score"] for r in self.data[crop, y, 60]["rotations"]) for y in YEARS}
            self.assertEqual(len(set(checks.values())), len(YEARS), (crop, checks))

    def test_corn_climate_range_only_in_projected_years_and_changes(self):
        for target in TARGETS:
            ranges = {}
            for y in YEARS:
                for r in self.data["maize", y, target]["rotations"]:
                    check = r["quantity"].get("climate_range_check")
                    if y <= 2025:
                        self.assertIsNone(check)
                    else:
                        self.assertEqual(check["status"], "DERIVED")
                        lo, hi = check["low_bu_ac"], check["high_bu_ac"]
                        where = "above" if target > hi else "below" if target < lo else "inside"
                        self.assertIn(where, check["position"])
                        ranges.setdefault(r["id"], set()).add((lo, hi))
            for rid, seen in ranges.items():
                self.assertEqual(len(seen), 3, (target, rid))

    def test_crop_changes_the_list(self):
        ids = {crop: {r["id"] for r in self.data[crop, 2026, 60]["rotations"]} for crop in CROPS}
        self.assertEqual(len(ids["soybean"]), 4)
        self.assertEqual(ids["maize"], {"corn-soy-wheat-clover", "corn-soy-wheat", "corn-soy"})
        self.assertEqual(ids["wheat"], {"corn-soy-wheat-clover", "corn-soy-wheat", "soy-soy-wheat"})

    def test_wheat_tie_is_explained_and_ordered_by_rotation_score(self):
        rows = self.data["wheat", 2026, 60]["rotations"]
        tied = [r for r in rows if r["picked_crop_yield_bu_ac"] == 62.5]
        self.assertEqual(len(tied), 2)
        self.assertTrue(all(r["tie_note"] and "Tie on wheat" in r["tie_note"] for r in tied))
        self.assertGreaterEqual(tied[0]["score"], tied[1]["score"])
        self.assertIsNone([r for r in rows if r["picked_crop_yield_bu_ac"] == 59.5][0]["tie_note"])

    def test_notes_name_the_count_and_the_year_range(self):
        d = self.data["soybean", 2035, 60]
        self.assertIn("Only 4 trial rotations", d["rotation_count_note"])
        self.assertIn("2021 to 2040", d["year_note"])
        self.assertIn("Only 3 trial rotations include wheat", self.data["wheat", 2035, 60]["rotation_count_note"])


if __name__ == "__main__":
    unittest.main()
