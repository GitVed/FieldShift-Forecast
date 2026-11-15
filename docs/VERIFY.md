# How to check the numbers

This page lets anyone check the Plan screen by hand. It was generated from the running API, so the numbers match what the app shows. Regenerate it after any data change.

Sources: corn from Top Crop Manager (Drury, 30 July 2021). Soybean 5-year figures from a Drury interview (RealAgriculture, April 2021). Long-term soybean from Agomoh et al. 2021 and long-term wheat from Agomoh et al. 2020, both in Soil Science Society of America Journal, converted from t/ha. Essex wheat from OMAFA county estimates, 2025. Prices from Grain Farmers of Ontario, September 2026. Full links are in `data/seed/harrow_trial_yields.csv`, `data/seed/regional_yields.csv` and `data/seed/model2_prices.json`.

## Pick corn, need 160 bu/ac

| Rank | Rotation | Answer | How calculated |
|---|---|---|---|
| 1 | Corn → Soy → Winter wheat + red clover | Yes: trial 169 bu/ac meets 160 | 169 >= 160. Per acre in a year you grow maize (1 of 3 years). Averaged over every year of the rotation: 169 x 1/3 = 56.3 bu/ac/yr. Normal-year averages, not drought yields. |
| 2 | Corn → Soy → Winter wheat | Yes: trial 164 bu/ac meets 160 | 164 >= 160. Per acre in a year you grow maize (1 of 3 years). Averaged over every year of the rotation: 164 x 1/3 = 54.7 bu/ac/yr. Normal-year averages, not drought yields. |
| 3 | Corn → Soy | No: trial 154 bu/ac, short by 6 | 154 < 160. Per acre in a year you grow maize (1 of 2 years). Averaged over every year of the rotation: 154 x 1/2 = 77 bu/ac/yr. Normal-year averages, not drought yields. |

Ranking rule: rank = rank_for_crop: ordered by the maize trial yield in each rotation. Rotations with no trial yield for that crop come last. Ties use the dry-year rank.

## Pick soybean, need 60 bu/ac

| Rank | Rotation | Answer | How calculated |
|---|---|---|---|
| 1 | Corn → Soy → Winter wheat | Depends on the figure: trial 64 bu/ac meets 60; long-term trial 52 bu/ac, short by 8 | 64 >= 60 ; 52 < 60. Per acre in a year you grow soybean (1 of 3 years). Averaged over every year of the rotation: 64 x 1/3 = 21.3, 52 x 1/3 = 17.3 bu/ac/yr. Normal-year averages, not drought yields. |
| 2 | Soy → Soy → Wheat | No: trial 53 bu/ac, short by 7; long-term trial 41.6 bu/ac, short by 18.4 | 53 < 60 ; 41.6 < 60. Per acre in a year you grow soybean (2 of 3 years). Averaged over every year of the rotation: 53 x 2/3 = 35.3, 41.6 x 2/3 = 27.7 bu/ac/yr. Normal-year averages, not drought yields. |
| 3 | Corn → Soy → Winter wheat + red clover | No: long-term trial 50.6 bu/ac, short by 9.4 | 50.6 < 60. Per acre in a year you grow soybean (1 of 3 years). Averaged over every year of the rotation: 50.6 x 1/3 = 16.9 bu/ac/yr. Normal-year averages, not drought yields. |
| 4 | Corn → Soy | No: long-term trial 49.1 bu/ac, short by 10.9 | 49.1 < 60. Per acre in a year you grow soybean (1 of 2 years). Averaged over every year of the rotation: 49.1 x 1/2 = 24.6 bu/ac/yr. Normal-year averages, not drought yields. |

Ranking rule: rank = rank_for_crop: ordered by the soybean trial yield in each rotation. Rotations with no trial yield for that crop come last. Ties use the dry-year rank.

## Pick wheat, need 70 bu/ac

| Rank | Rotation | Answer | How calculated |
|---|---|---|---|
| 1 | Corn → Soy → Winter wheat + red clover | No: long-term trial 62.5 bu/ac, short by 7.5 | 62.5 < 70. Per acre in a year you grow wheat (1 of 3 years). Averaged over every year of the rotation: 62.5 x 1/3 = 20.8 bu/ac/yr. Normal-year averages, not drought yields. |
| 2 | Corn → Soy → Winter wheat | No: long-term trial 62.5 bu/ac, short by 7.5 | 62.5 < 70. Per acre in a year you grow wheat (1 of 3 years). Averaged over every year of the rotation: 62.5 x 1/3 = 20.8 bu/ac/yr. Normal-year averages, not drought yields. |
| 3 | Soy → Soy → Wheat | No: long-term trial 59.5 bu/ac, short by 10.5 | 59.5 < 70. Per acre in a year you grow wheat (1 of 3 years). Averaged over every year of the rotation: 59.5 x 1/3 = 19.8 bu/ac/yr. Normal-year averages, not drought yields. |

Ranking rule: rank = rank_for_crop: ordered by the wheat trial yield in each rotation. Rotations with no trial yield for that crop come last. Ties use the dry-year rank.

## Trial yield index and revenue, all rotations

| Rotation | Index | How calculated | Revenue | How calculated |
|---|---|---|---|---|
| Corn → Soy → Winter wheat + red clover | 100.0 | (Corn 169/169 x 100 = 100) averaged = 100. Left out, no trial yield: Soy, Wheat | 851 CAD/ac/yr gross | Corn 169 x 7.00 + Soy 50.6 x 16.46 + Wheat 62.5 x 8.58, divided by 3 years = 851 CAD/ac/yr. Uses a long-term trial average for at least one crop. |
| Corn → Soy → Winter wheat | 98.5 | (Corn 164/169 x 100 = 97; Soy 64/64 x 100 = 100) averaged = 98.5. Left out, no trial yield: Wheat | 912 CAD/ac/yr gross | Corn 164 x 7.00 + Soy 64 x 16.46 + Wheat 62.5 x 8.58, divided by 3 years = 912 CAD/ac/yr. Uses a long-term trial average for at least one crop. |
| Soy → Soy → Wheat | 82.8 | (Soy 53/64 x 100 = 82.8) averaged = 82.8. Left out, no trial yield: Wheat | 752 CAD/ac/yr gross | Soy 53 x 16.46 + Soy 53 x 16.46 + Wheat 59.5 x 8.58, divided by 3 years = 752 CAD/ac/yr. Uses a long-term trial average for at least one crop. |
| Corn → Soy | 91.1 | (Corn 154/169 x 100 = 91.1) averaged = 91.1. Left out, no trial yield: Soy | 943 CAD/ac/yr gross | Corn 154 x 7.00 + Soy 49.1 x 16.46, divided by 2 years = 943 CAD/ac/yr. Uses a long-term trial average for at least one crop. |

## 2012 dry year, measured

- POWER: May to September rain 317.9 mm in 2012 against 426.4 mm normal (1991-2020). Longest dry spell 10 days against 11.3. Days with 10 mm or more: 7 against 11.5.
- IMERG: May to September rain 416.1 mm in 2012 against 470.7 mm normal (2001-2020). Longest dry spell 8 days against 11.4. Days with 10 mm or more: 15 against 15.8.
- Degree days above 10 C (NASA POWER): 1698.4 against 1438.2 normal.

## What a check cannot prove

- Trial yields are normal-year averages from the Woodslee trial, about 26 km from the field. They are not drought yields and not a forecast for this field.
- The 5-year and long-term trial figures cover different years. They are shown side by side, never averaged.
- Revenue is gross. There is no profit because costs are not verified.
