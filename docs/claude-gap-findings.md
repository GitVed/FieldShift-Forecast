# Claude gap findings on the Muse report

Written Sat Nov 14, 2026. This file checks Muse's `report.md` and `rotation-evidence.csv`. It does not replace them.

How this was done: three research and data agents worked in parallel. One re-checked Muse's crop list and items 1 to 4, one checked trial evidence for the model, and one read FAO GAEZ v5 directly. GAEZ values were spot-checked by hand (chickpea, watermelon, sorghum all matched). The web quotes below were collected by an AI agent from the sources listed. Check a quote against its source before putting it on a slide.

## Summary

### Confirmed
- Kidney beans are a commercial Ontario crop (OMAFRA Pub 811 ch. 5). Agricorp 2017 kidney beans 2,264 lb/ac (via Field Crop News).
- SARE LNC11-336 all-bean yields 2,655 (2011), 1,852 (2012-2013), 1,234 (2014) kg/ha.
- Essex County paddy rice, late 1990s, about 5 t/ha with hulls removed (Top Crop Manager, quoting AAFC Harrow).
- Ontario watermelon 35,084 t is the 2023 Statistics Canada figure.
- Perennials (apple, grapes, banana, coconut, coffee, mango, orange, papaya, pomegranate) are correctly excluded from an annual rotation.

### Corrected
- Item 1: "Christensen et al. 1982" is Christenson, D.R. 1982, a proceedings paper not found online. The full Michigan trial reports (MSU Research Report 516, 1975-1990; MSU Staff Paper 98-22, 1975-1994) do not contain 18.6, 17.3 and 16.3 cwt/A for beans in 25, 50 and 75 percent of years. The trial has no 75 percent treatment. Treat Muse's numbers as UNVERIFIED. The trial is at the Saginaw Valley Research Farm, Michigan, on Misteguay silty clay, four replications. What it does show: navy beans in 4-year rotations yielded 7.2 percent more than in 2- and 3-year rotations, and 11.3 percent more after corn or oats than after sugar beet.
- Item 2: SARE Table 4 kidney beans averaged 1,398 kg/ha over 2011-2014, the lowest bean class. The 'Majesty' sentence Muse quoted is from a different experiment.
- Mungbean 1,800 and 660 kg/ha: found only in Better Farming 2012, which credits a 1996 report, not 1997. Still UNVERIFIED against the original.
- Chickpea and lentil: Statistics Canada shows 0 or suppressed Ontario acres in every year 2018-2026 (lentil yield only in 2019, 2,500 lb/ac). Muse called them plausible; official data shows no Ontario production.
- Muskmelon is not its own Statistics Canada category ("other fresh melons").

### New
- OMAFRA advice for dry beans: once in 3 years, corn, forages and cereals before beans, and soybean is a poor partner because of white mould. Beans fit a corn-bean-wheat rotation, not our soybean rotations.
- Adzuki beans are an Ontario crop (1,375 lb/ac in 2017). Not in Kaggle.
- Latest Ontario dry bean yields (Statistics Canada 2025): all dry beans 22.3 cwt/ac, coloured (includes kidney) 21.0, white 23.7.
- Watermelon 2025: 2,646 acres harvested, 62,346 t. Yield not stated.
- Ridgetown, Ontario rotation trial 2012-2017 (Field Crop News 2023, from Janovicek et al. 2021): winter wheat 112-114 bu/ac, and corn and soybean yields by rotation. Not Harrow, so not added to the model yet.

### Item 5: GAEZ v5 codes (read from FAO's own code list in the GAEZ v5 data bucket)
- CHK (Chickpea): 75.81 now, 75.81 in 2021-2040 SSP370
- Kidney bean: no kidney-only layer. PHB (Phaseolus bean): 75.81 now, 75.81 in 2021-2040 SSP370
- Lentil: no GAEZ v5 layer
- Mungbean: no confirmed layer. GRM (Gram): 0.00 now, 0.00 in 2021-2040 SSP370. GAEZ does not name the species, so this mapping is UNVERIFIED
- Muskmelon: no GAEZ v5 layer
- WMEL (Watermelon): 0.00 now, 0.00 in 2021-2040 SSP370. Ontario grows watermelon commercially, so 0 reflects GAEZ's rain-fed model, not reality here
- Rice: RCD (Dryland rice): 0.00 now, 0.00 in 2021-2040 SSP370; RCW (Wetland rice): 0.00 now, 21.89 in 2021-2040 SSP370

Muse said no v5 code was found. The codes exist in FAO's list: `DATA/GAEZ-V5/DIMENSION/GAEZ-V5.CROP-RES05.csv` in the GAEZ v5 bucket.

### Still not found
- Christenson 1982 proceedings text, and the Cardwell document Muse cited.
- Original Park and Anderson mungbean report.
- Any rotation yield trial for chickpea, lentil, mungbean, muskmelon, watermelon or rice with corn, soybean or wheat.
- Any Ontario dry bean rotation yield trial.
- Agricorp kidney bean yield for any year after 2017.
- Official Ontario yield for mungbean, chickpea, rice or muskmelon.

### What changed in the app because of this
- `data/seed/other_crops.csv` and the "Explore other crops" panel use these statuses, sources and GAEZ values. All 21 Kaggle crops are listed as suitability only.
- No Muse number was added to the rotation model.

---

# Appendix: full research notes, quotes and references

# Gap research: checking Muse's crop-rotation report

Independent check for the Harrow, Essex County, Ontario pilot. All access dates are 2026-11-14.
Rule used: no number is given unless a source states it. If a source gives only area and production, yield is marked "yield not stated" and is not computed.

Labels used below:
- TRIAL = a replicated field experiment result
- STATS = official statistics (Statistics Canada, Agricorp)
- EXTENSION = advice from a government or university extension guide
- GENERAL = a general statement or news report

---

## 1. Checked

| Question | Sources tried | Result |
|---|---|---|
| A. Step 1, 21 Kaggle crops in Ontario | Statistics Canada tables 32-10-0359-01 (field crops), 32-10-0364-01 (fruit), 32-10-0365-01 (vegetables), downloaded as full CSVs; OMAFRA Agronomy Guide for Field Crops, Chapter 5 (2022 PDF); Ontario Data Catalogue vegetable files (2024-25 xlsx); Top Crop Manager; U of Guelph OAC; Better Farming; web searches for urad/blackgram, cotton, jute in Ontario | Done, see sections 2 to 4 |
| B. Original Christensen et al. 1982 | Web searches; MSU Extension archive; AgEcon Search; FAO AGRIS; MSU Research Report 516 (1991, full PDF); MSU Staff Paper 98-22 (1998, full PDF); UW/UMN Alternative Field Crops Manual (Field Bean). core.ac.uk PDF returned 403 | The 1982 item is identified (it is "Christenson", not "Christensen") but its text is not online. The same Saginaw Valley trial is fully reported in RR 516 (1975-1990) and Staff Paper 98-22 (1975-1994). Muse's 18.6 / 17.3 / 16.3 at 25 / 50 / 75 percent are NOT found |
| C. SARE LNC11-336 Table 4, kidney yield | SARE project report page; Table-4.pdf (downloaded, text extracted) | Found: kidney yields by site, 2011-2014 |
| D. Rotation trials for chickpea, lentil, muskmelon, watermelon, dry bean | Web searches (Great Lakes, humid temperate); Purdue melon variety trials; Illinois 1950 melon bulletin; Prairie pulse rotation papers; OMAFRA Chapter 5; Ridgetown and Elora long-term trials (Field Crop News); Gillard (Ridgetown) pages | No rotation yield trial found for chickpea, lentil, muskmelon or watermelon with corn, soybean or wheat in a humid climate. Dry bean: Michigan and Minnesota trials found (with corn as previous crop). No Ontario dry bean rotation yield trial found |
| E. Ontario average yields | StatCan 32-10-0359-01, 32-10-0365-01; Agricorp via OMAFA Field Crop News (2017, 2024, 2025 summaries); OMAFRA vegetable xlsx 2024-25 (no melons listed) | Dry beans, lentil (2019 only): yield stated. Chickpea: zero area. Watermelon and other melons: area and production only, yield not stated. Rice, mungbean: no official statistics found |

---

## 2. Confirmed

### 2.1 Kidney beans are a commercial Ontario crop (EXTENSION + STATS)
- OMAFRA Agronomy Guide for Field Crops, Ch. 5 Dry Edible Beans: "The main types of beans grown in Ontario include white (navy), kidney, cranberry, black, otebo, and adzuki (or azuki) beans."
- Same page: "Production of dry edible beans occurs primarily in western Ontario, and the crop is typically grown under contract."

### 2.2 Agricorp 2017 kidney yield 2,264 lb/ac (STATS, reported in OMAFRA extension article)
- Field Crop News, "Dry Edible Bean Seasonal Summary", Meghan Moran, posted Dec 6 2017: "UPDATE Jan 29, 2018 – Agricorp average provincial yields:" ... "Kidney beans – 2264 lb/ac". Muse is correct. This is a secondary report of Agricorp data, not an Agricorp document.

### 2.3 SARE LNC11-336 all-bean yields by year (TRIAL, organic, Minnesota)
- "Overall, bean yields were highest in 2011 with 2,655 kg/ha, followed by 2012 and 2013 with an average of 1,852 kg/ha, and lowest in 2014 with 1,234 kg/ha." Muse is correct. Note this "bean" average includes soybean as one of the "bean types" in Table 4.

### 2.4 Rice in Essex, late 1990s, about 5 t/ha (TRIAL report in trade press)
- Top Crop Manager, "Growing rice in southern Ontario", Blair Andrews, Feb 20 2009: "In a more a recent experiment, paddy rice was grown for two years near Holiday Beach in Essex County in the late 1990s." and "...Park, who estimated the yield at five tonnes/ha (about 4460 lbs/ac) with hulls removed." Park is "Dr. Soon Park, a crop breeder from the Agriculture and Agri-Food Canada research station at Harrow, Ontario". Also: "the yields from the Essex County project were about 30 to 50 percent smaller than those in California." Muse is correct. It is paddy (flooded) rice.

### 2.5 Ontario watermelon about 2,000 acres and 35,084 tonnes (STATS)
- StatCan 32-10-0365-01, Ontario, "Fresh watermelons", 2023: Area harvested 1,920 acres; Total production 35,084 metric tonnes. Muse's 35,084 t is the 2023 value. It is not the most recent year (see 4.6).

### 2.6 Mungbean 1,800 vs 660 kg/ha (only a secondary source)
- Better Farming, "Mung bean production may offer diversification opportunities for Ontario growers", Mary Baxter, Jan 2 2012: yields ranged "from 1,800 kilograms per hectare on the well-drained, sandy loamy soils the plant prefers to 660 kilograms on Brookston clay." The numbers are confirmed in this secondary source. See 3.4 for the date problem.

### 2.7 Perennial and tropical exclusions are correct as rotation decisions
- Apple, grapes, banana, coconut, coffee, mango, orange, papaya and pomegranate are not annual field crops. Correctly excluded from an annual rotation. See 4.7 for the note that apple and grapes ARE commercial Ontario crops.

---

## 3. Corrected

### 3.1 "Christensen et al. 1982" is "Christenson, D.R. 1982", and Muse's numbers are not in the trial reports found
- MSU Research Report 516 (1991) cites: "Christenson, D.R. 1982. Cropping sequence effects on yields. p 14-19. In Ninth Michigan Seed, Weed, and Fertilizer School Proceedings. Mich. State Univ. E. Lansing, MI." This proceedings paper was not found online.
- The full trial reports found do not contain 18.6, 17.3, 16.3 cwt/A as yields for 25, 50, 75 percent beans. The design has no 75 percent bean treatment. The highest bean share is 2 of 3 years (NB-NB-SB, 67 percent). The values 16.3 and 17.3 do appear, but for other rotations (NB-SB = 16.3 and C-NB-NB-SB = 17.3 in RR 516; NB-NB-SB first bean year = 16.3 in Staff Paper 98-22). Treat Muse's 18.6 / 17.3 / 16.3 split as UNVERIFIED. Use the RR 516 values in section 6 instead.
- The trial: MSU Saginaw Valley Research Farm near Saginaw, Michigan. Started 1972, data 1975-1990 (RR 516) and 1975-1994 (Staff Paper 98-22). RR 516: "The soil on this site is presently mapped as a Misteguay silty clay. It is alkaline in reaction (pH 7.5-7.9)". "The experiment was arranged as a randomized complete block design with four replications. Each of the crops in each of the cropping systems was grown each year." 28-inch rows. Navy bean yields from 1986 excluded because of flooding.

### 3.2 Michigan result is about rotation length and previous crop, not a simple frequency curve
- RR 516: "Navy bean yields in the four-year rotations were 7.2% greater than the average of the three-year and the two-year rotations combined. The yield differences were not significant between the two-year and the three-year rotations."
- RR 516: "navy bean yields were significantly higher by an average of 11.3%, when navy beans followed corn or oats rather than sugar beets."
- RR 516: "The 15 year averages for first versus second year beans in the four-year rotations were identical (Table 10). This result does not agree with earlier reports that dry bean yields tend to decrease when following another dry bean crop".
- RR 516 summary: "Corn following corn yielded 12% less than corn following sugar beets or navy beans." (OCR text reads "com" and "whe~"; only these OCR letter errors are corrected in quotes.)

### 3.3 SARE: kidney beans were the LOWEST bean type, and the Majesty number is a different experiment
- The kidney yields Muse could not extract are in Table 4 (section 6). Kidney mean 1,398 kg/ha, the lowest class (letter E).
- The "'Majesty' kidney bean yields being intermediate" sentence is from Objective 3 (winter rye cover crop, Lamberton, 2014), not the rotation trial. No Majesty number is given in the text.

### 3.4 Mungbean source date and original
- Better Farming says the figures come from "a 1996 academic report" by Soon Park and T.R. Anderson, not 1997. 1997 is the year AC Harosprout was released ("By 1997, Park had released a variety called the AC Harosprout mungbean."). The Olson et al. 2011 paper (Can. J. Plant Sci. 91:137-141) is paywalled (403) and could not be checked. The original Park and Anderson report was not found. Keep 1,800 / 660 kg/ha as UNVERIFIED against the original.

### 3.5 Chickpea and lentil are not Ontario crops in official statistics
- Muse carried chickpea and lentil forward as "plausible/experimental". StatCan 32-10-0359-01 Ontario "Chick peas" seeded area is 0 acres in 2018, 2019, 2020, 2023, 2024, 2025 and 2026, and suppressed (F, too unreliable) in 2021 and 2022. "Lentils" seeded area is 0 in 2018, 2020, 2022, 2023, 2024, 2026, and F in 2019, 2021, 2025. Only 2019 has a lentil yield (see 4.4). StatCan "0" can also mean a value rounded to zero. No Ontario chickpea or lentil trial was found.

### 3.6 Rice is a pilot, not an established crop
- Rice is not in the StatCan principal field crops list for Ontario. The 2019 Chatham-Kent crop was a 2.5-acre pilot (U of Guelph OAC, Jan 7 2020). OMAFRA's rice CropOp page (omafra.gov.on.ca/CropOp/.../whri.html) could not be fetched (403 and "Web App - Unavailable"), so the "3150 heat units" statement seen in a search snippet is UNVERIFIED.

### 3.7 Muskmelon is not a separate StatCan category
- StatCan 32-10-0365-01 has "Fresh watermelons" and "Other fresh melons". The metadata does not say "Other fresh melons" is only cantaloupe or muskmelon. OMAFRA's 2024-25 "Specified Commercial Vegetable Crops" table lists no melons.

---

## 4. New findings

### 4.1 SARE LNC11-336 Table 4 includes a corn-before-beans comparison (TRIAL, organic)
Table 4 title: "Mean bean yields (kg ha-1) by bean type and previous crop at four MN locations from 2011-2014." Previous crop corn mean 1,813 kg/ha; alfalfa 1,990 kg/ha, same letter A (not significantly different across locations). Report text: averaged across eight site-years "there was no significant rotation effect on bean yield." Rotation design: corn or alfalfa, then dry bean or soybean, then spring wheat, at Lamberton, Rosemount, Becker and Madison, MN.

### 4.2 Ontario extension advice for dry bean rotation (EXTENSION)
OMAFRA Ch. 5:
- "A rotation where beans are grown only once in 3 years (or longer) is essential to avoid the build-up of diseases."
- "Soybean, canola, potato and sunflower are poor rotation choices with beans since they are all susceptible to white mould."
- "Considering all the factors, the ultimate rotation crops for dry edible beans include corn, forages and cereals."
- "The earlier harvest date of dry edible beans allows for timely planting of winter wheat."
- Important for Brookston clay loam: "Heavy soils that are poorly drained, prone to crusting or hard to till risk uneven emergence and poor stands." and "Yield reductions from compaction and poor soil structure can be as high as 30%–50%."

This means a corn, dry bean, winter wheat rotation fits Ontario advice. A rotation with both soybean and dry bean is advised against.

### 4.3 Adzuki beans are an Ontario crop (Muse did not mention them)
Not in the Kaggle list, but the closest Ontario relative of mungbean (both Vigna). OMAFRA lists adzuki as a main Ontario bean type. Agricorp 2017: "Adzuki beans – 1375 lb/ac". 2025 Agricorp seeded acres: adzuki 9,842 (Field Crop News, "Dry Bean Seasonal Summary 2025", Nov 20 2025).

### 4.4 Ontario official yields (STATS)
StatCan 32-10-0359-01 (downloaded 2026-11-14). 2025 is the latest full year. 2026 values exist but are probably the September model-based estimate (table footnote 46: "Starting in September 2016, model-based data was used to estimate the September survey occasion yield and production for the provinces of Ontario..."), so treat 2026 as preliminary.
- All dry beans, 2025: 22.3 cwt/ac (2,497 kg/ha). 2026 prelim: 24.4 cwt/ac (2,735 kg/ha)
- Dry coloured beans (includes kidney; kidney not separate), 2025: 21.0 cwt/ac (2,350 kg/ha). 2026 prelim: 23.1 (2,595)
- Dry white beans, 2025: 23.7 cwt/ac (2,661 kg/ha). 2026 prelim: 25.5 (2,861)
- Lentils, 2019 only: 2,500 lb/ac (2,802 kg/ha), production 3,900 t, seeded area F (suppressed)
- Chickpeas: no yield in any year (0 acres or F)
- Kidney-specific Agricorp yield: newest found is 2017 (2,264 lb/ac). Field Crop News 2024 and 2025 summaries say Agricorp had not yet released yields. 2025 summary: "Yields are reported to be below average."

### 4.5 Rice, Chatham-Kent 2019 pilot (GENERAL, university news)
U of Guelph OAC, "Bringing rice to Canadian fields", Stephanie Craig, Jan 7 2020: "an average yield of 6,920 lbs. per acre (or 154 bushels per acre)". 2.5-acre test plot in Chatham-Kent. Paddy or milled basis is not stated.

### 4.6 Ontario melon area and production, latest year 2025 (STATS)
StatCan 32-10-0365-01, Ontario, 2025:
- Fresh watermelons: area planted 2,976 ac; area harvested 2,646 ac (1,071 ha); total production 62,346 t; marketed 62,307 t. Yield not stated.
- Other fresh melons: area harvested 467 ac (189 ha); total production 5,373 t. Yield not stated.
2024: watermelon 2,153 ac harvested, 39,504 t; other melons 483 ac, 5,063 t.

### 4.7 Apple and grapes are big Ontario crops (but perennial)
StatCan 32-10-0364-01, Ontario 2025, "Cultivated area, total": Fresh apples 15,804 acres; Fresh grapes 17,277 acres. Still correctly excluded from an annual rotation. No banana, coconut, coffee, mango, orange, papaya or pomegranate category exists for Ontario in this table.

### 4.8 Ontario wheat-in-rotation trial numbers (useful for the open wheat yield gap)
Not asked, but directly relevant to the project's "wheat yield not available" item. OMAFA Field Crop News, "Putting the economics to a three-crop rotation in Ontario", Jake Munroe with Ken Janovicek and Dave Hooker, Jan 17 2023 (raw page text checked):
- "At Ridgetown, corn in a corn-soybean-wheat rotation yielded 5.8 bu/ac over corn in rotation with only soybeans."
- Table 2 (Ridgetown, 2012-2017, averaged across tillage), bu/ac: Continuous corn 194.5; Corn-soybean corn 195.6, soybean 62.2; Corn-soybean-w. wheat corn 201.4, soybean 66.9; Corn-soybean-w. wheat (red clover) corn 209.3, soybean 67.8
- "Wheat yields averaged 112-114 bu/ac during this time." (Ridgetown, 2012-2017)
- Elora: "...despite achieving only average wheat yields (79 bu/ac) from 2002-2017 (provincial average: 78 bu/ac)."
- Peer-reviewed original: Janovicek K, Hooker D, Weersink A, Vyn R, Deen B. 2021. Corn and soybean yields and returns are greater in rotations with wheat. Agronomy Journal 113(2):1691-1711. https://doi.org/10.1002/agj2.20605 (full text not accessed; abstract via FAO AGRIS).
- Caveat: Ridgetown (Chatham-Kent) is not Harrow. Soil type is not stated in the article. These are not AAFC Harrow numbers.

### 4.9 Upper Midwest extension advice for dry bean (EXTENSION)
Alternative Field Crops Manual, "Dry Field Bean", Hardman, Oplinger, Schulte, Doll, Worf, May 1990: "rotations should be a minimum of 2 years, but 3 and 4 year cycles are best." and "Crops such as corn, wheat, oats, barley, and flax should precede beans".

### 4.10 Melon and watermelon rotation advice exists only as old general advice
University of Illinois melon bulletin (Dec 1950, core.ac.uk 10199844, not opened; seen in search summary only) names corn, wheat and soybeans as intermediate crops. UNVERIFIED, old, no yields.

### 4.11 No evidence of Ontario production for blackgram, mothbean, pigeonpea, cotton, jute
None of these appears in StatCan principal field crops (32-10-0359-01) crop list for Ontario. Web searches found no Ontario trial or commercial production for urad/blackgram, cotton or jute. This is absence of evidence. Muse's exclusion stands.

---

## 5. Still not found

- The text of Christenson, D.R. 1982, "Cropping sequence effects on yields", Ninth Michigan Seed, Weed, and Fertilizer School Proceedings, p 14-19. Check: MSU Libraries special collections or interlibrary loan.
- The Cardwell (University of Minnesota) document Muse cited. Not located in any search.
- Muse's 18.6, 17.3, 16.3 cwt/A at 25, 50, 75 percent beans.
- Original Park and Anderson (1996) mungbean report, and Olson et al. 2011 text (paywalled).
- Any rotation yield trial with corn, soybean or winter wheat for chickpea, lentil, mungbean, muskmelon, watermelon or rice, in Ontario, the Great Lakes, or a similar humid temperate climate.
- Any Ontario dry bean rotation yield trial (Ridgetown, Exeter, Gillard, Sikkema). Gillard pages found are about SCN, seeding rate and herbicides.
- Agricorp kidney bean average yield for any year after 2017.
- Official Ontario yield for mungbean, chickpea, rice, muskmelon/cantaloupe (none published).
- RR 516 Table 4 (rotation-length means) is damaged in the OCR text (digits cut off). Table 10 is readable.

---

## 6. CSV

```csv
rotation,crop,value,unit,baseline,period,source,note,verification,source_type
C-NB (corn-navy bean),navy bean,18.1,cwt/A,15-year mean,1975-1990 excl 1986,Christenson Bricker Gallagher 1991 MSU RR 516 Table 10,Saginaw Valley MI; Misteguay silty clay; RCBD 4 reps; OCR of scan,VERIFIED,government
C-NB-SB,navy bean,18.0,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Beans after corn; 1 in 3 years,VERIFIED,government
C-C-NB-SB,navy bean,19.3,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Beans after corn; 1 in 4 years,VERIFIED,government
NB-SB,navy bean,16.3,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Beans after sugar beet; 1 in 2 years,VERIFIED,government
NB-NB-SB,navy bean,15.3,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Row marked with underlined first NB; OCR lost underline so bean year is uncertain,UNVERIFIED,government
NB-NB-SB,navy bean,16.5,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Other bean year of NB-NB-SB; underline lost in OCR,UNVERIFIED,government
C-NB-NB-SB,navy bean,17.3,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Both bean years 17.3; text says first and second year identical,VERIFIED,government
O-NB,navy bean,18.4,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Beans after oats; 1 in 2 years,VERIFIED,government
O-NB-SB,navy bean,18.5,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,,VERIFIED,government
O-A-NB-SB,navy bean,19.5,cwt/A,15-year mean,1975-1990 excl 1986,MSU RR 516 Table 10,Highest bean yield in trial,VERIFIED,government
4-yr vs 2- and 3-yr rotations,navy bean,7.2,percent greater,average of 2-yr and 3-yr rotations,1975-1990,MSU RR 516 text,"""Navy bean yields in the four-year rotations were 7.2% greater...""",VERIFIED,government
beans after corn or oats vs after sugar beet,navy bean,11.3,percent higher,beans after sugar beet,1975-1990,MSU RR 516 text,Significant,VERIFIED,government
corn after corn vs after sugar beet or navy bean,corn,-12,percent,corn after sugar beet or navy bean,1975-1990,MSU RR 516 summary,"""Corn following corn yielded 12% less...""",VERIFIED,government
C-NB,navy bean,19.0,cwt/acre,20-year mean,1975-1994 excl 1986,Gebremedhin et al. 1998 MSU Staff Paper 98-22 Table 1 (citing Christenson et al. 1995),Same trial longer period,VERIFIED,other
NB-SB,navy bean,17.0,cwt/acre,20-year mean,1975-1994 excl 1986,MSU Staff Paper 98-22 Table 1,,VERIFIED,other
C-C-NB-SB,navy bean,20.5,cwt/acre,20-year mean,1975-1994 excl 1986,MSU Staff Paper 98-22 Table 1,,VERIFIED,other
O-A-NB-SB,navy bean,20.6,cwt/acre,20-year mean,1975-1994 excl 1986,MSU Staff Paper 98-22 Table 1,,VERIFIED,other
NB-NB-SB,navy bean,16.3 and 18.0,cwt/acre,20-year mean (1st and 2nd bean year),1975-1994 excl 1986,MSU Staff Paper 98-22 Table 1,Staff paper is a working paper not a journal article,VERIFIED,other
"Muse: beans 25/50/75% of years",dry bean,18.6/17.3/16.3,cwt/A,,,Cardwell UMN citing Christensen et al. 1982,Not found in any source checked; design has no 75% treatment,UNVERIFIED,other
corn or alfalfa > bean > spring wheat (organic),kidney bean,1398,kg/ha,mean of 4 MN sites,2011-2014,SARE LNC11-336 Table 4 (Sheaffer UMN),Lowest bean class (E); Becker 1698 Lamberton 980 Madison 1257 Rosemount 1655,VERIFIED,government
corn > bean > spring wheat (organic),all bean types incl soybean,1813,kg/ha,previous crop corn; mean 4 sites,2011-2014,SARE LNC11-336 Table 4,Alfalfa previous crop 1990; same letter A,VERIFIED,government
corn or alfalfa > bean > wheat (organic),all bean types,2655,kg/ha,annual mean,2011,SARE LNC11-336 report,"""Overall, bean yields were highest in 2011 with 2,655 kg/ha""",VERIFIED,government
corn or alfalfa > bean > wheat (organic),all bean types,1852,kg/ha,annual mean,2012-2013,SARE LNC11-336 report,,VERIFIED,government
corn or alfalfa > bean > wheat (organic),all bean types,1234,kg/ha,annual mean,2014,SARE LNC11-336 report,,VERIFIED,government
none (provincial average),kidney bean,2264,lb/ac,Ontario provincial average,2017,Agricorp via Field Crop News (Moran 2017 update Jan 29 2018),Secondary report of Agricorp data,VERIFIED,government
none (provincial average),adzuki bean,1375,lb/ac,Ontario provincial average,2017,Agricorp via Field Crop News,,VERIFIED,government
none (provincial average),all dry beans,22.3,cwt/ac,Ontario average,2025,StatCan 32-10-0359-01 v54532310,2497 kg/ha,VERIFIED,government
none (provincial average),dry coloured beans,21.0,cwt/ac,Ontario average,2025,StatCan 32-10-0359-01 v54532312,Includes kidney; 2350 kg/ha,VERIFIED,government
none (provincial average),dry white beans,23.7,cwt/ac,Ontario average,2025,StatCan 32-10-0359-01 v54532311,2661 kg/ha,VERIFIED,government
none (provincial average),all dry beans,24.4,cwt/ac,Ontario average,2026,StatCan 32-10-0359-01 v54532310,Probably preliminary model-based estimate,VERIFIED,government
none (provincial average),lentil,2500,lb/ac,Ontario average,2019,StatCan 32-10-0359-01,2802 kg/ha; production 3900 t; area suppressed F; only year with a value,VERIFIED,government
none,chickpea,not stated,,,2018-2026,StatCan 32-10-0359-01,0 acres or F every year,VERIFIED,government
none,watermelon,not stated,,,2025,StatCan 32-10-0365-01,Area harvested 2646 ac; production 62346 t; yield not stated,VERIFIED,government
none,watermelon,not stated,,,2023,StatCan 32-10-0365-01,Area harvested 1920 ac; production 35084 t (Muse's figure),VERIFIED,government
none,other fresh melons,not stated,,,2025,StatCan 32-10-0365-01,Area harvested 467 ac; production 5373 t; category not defined as muskmelon only,VERIFIED,government
none (paddy experiment),rice,5,t/ha,hulls removed,late 1990s (2 years),Top Crop Manager Andrews 2009 quoting Soon Park AAFC Harrow,Holiday Beach Essex County; 30-50% below California,VERIFIED,industry
none (pilot),rice,6920,lb/ac,2.5-acre pilot,2019,U of Guelph OAC news Craig 2020,Chatham-Kent; paddy or milled not stated,VERIFIED,other
none (soil comparison),mungbean,1800,kg/ha,sandy loam,not stated,Better Farming Baxter 2012 citing Park and Anderson 1996,Secondary only; original not found,UNVERIFIED,industry
none (soil comparison),mungbean,660,kg/ha,Brookston clay,not stated,Better Farming Baxter 2012 citing Park and Anderson 1996,Secondary only; original not found,UNVERIFIED,industry
continuous corn,corn,194.5,bu/ac,Ridgetown trial,2012-2017,Field Crop News Munroe Janovicek Hooker 2023 Table 2,Ridgetown ON; avg across tillage,VERIFIED,government
corn-soybean,corn,195.6,bu/ac,Ridgetown trial,2012-2017,Field Crop News 2023 Table 2,,VERIFIED,government
corn-soybean,soybean,62.2,bu/ac,Ridgetown trial,2012-2017,Field Crop News 2023 Table 2,,VERIFIED,government
corn-soybean-winter wheat,corn,201.4,bu/ac,Ridgetown trial,2012-2017,Field Crop News 2023 Table 2,,VERIFIED,government
corn-soybean-winter wheat,soybean,66.9,bu/ac,Ridgetown trial,2012-2017,Field Crop News 2023 Table 2,,VERIFIED,government
corn-soybean-winter wheat (red clover),corn,209.3,bu/ac,Ridgetown trial,2012-2017,Field Crop News 2023 Table 2,,VERIFIED,government
corn-soybean-winter wheat (red clover),soybean,67.8,bu/ac,Ridgetown trial,2012-2017,Field Crop News 2023 Table 2,,VERIFIED,government
wheat-containing rotations,winter wheat,112-114,bu/ac,Ridgetown trial,2012-2017,Field Crop News 2023,"""Wheat yields averaged 112-114 bu/ac during this time.""",VERIFIED,government
wheat-containing rotations,winter wheat,79,bu/ac,Elora trial,2002-2017,Field Crop News 2023,Provincial average 78 bu/ac,VERIFIED,government
```

---

## 7. References with quotes

1. Christenson, D.R., C.E. Bricker, R.S. Gallagher. 1991. Crop Yields as Affected by Cropping System and Rotation. Michigan State University Agricultural Experiment Station Research Report 516. https://sanweb.lib.msu.edu/DMC/extension_publications/RR516/RR516.pdf. Government (university experiment station). Accessed 2026-11-14. Quotes: "The soil on this site is presently mapped as a Misteguay silty clay." "Navy bean yields in the four-year rotations were 7.2% greater than the average of the three-year and the two-year rotations combined." "navy bean yields were significantly higher by an average of 11.3%, when navy beans followed corn or oats rather than sugar beets." "Corn following corn yielded 12% less than corn following sugar beets or navy beans." Table 10 title: "Navy bean yield (cwt/A) as affected by cropping system from 1975-1990 at the Saginaw Valley Research Farm." Reference entry: "Christenson, D.R. 1982. Cropping sequence effects on yields. p 14-19. In Ninth Michigan Seed, Weed, and Fertilizer School Proceedings."
2. Gebremedhin, B., G. Schwab, R.R. Harwood, D. Christenson, C. Bricker. 1998. A Stochastic Dominance Analysis of Alternative Sugar Beet- and Navy Bean-Based Crop Rotations in Michigan. MSU Dept. of Agricultural Economics Staff Paper 98-22. https://ageconsearch.umn.edu/record/11509/files/sp98-22.pdf, DOI 10.22004/ag.econ.11509. Other (working paper). Quote: "The Saginaw Valley Cropping System study was initiated in 1972 on Misteguay silty clay lake bed soil at the Michigan State University Saginaw Valley Research Farm. The experiment was arranged as a randomized complete block design with four replications." Table 1 note: "Units: corn and oats = bu/acre; sugar beets and alfalfa = tons/acre; navy beans = cwt/acre."
3. Christenson, D.R., R.S. Gallagher, T.M. Harrigan, J.R. Black. 1995. Net returns from 12 cropping systems containing sugarbeet and navy bean. Journal of Production Agriculture 8(2):276-281. https://doi.org/10.2134/jpa1995.0276. Peer-reviewed. Abstract only (via FAO AGRIS). Quote: "Yield of navy bean is generally better in 4-yr rotations than in shorter rotations (Table 1)."
4. Sheaffer, C. (project leader), University of Minnesota. Organic Beans and Peas: Nutritious and Gluten-free Local Foods. SARE project LNC11-336, final report. https://projects.sare.org/project-reports/lnc11-336/ and Table 4 https://projects.sare.org/media/pdf/T/a/b/Table-4.pdf. Government-funded grant report. Quotes: "Overall, bean yields were highest in 2011 with 2,655 kg/ha, followed by 2012 and 2013 with an average of 1,852 kg/ha, and lowest in 2014 with 1,234 kg/ha." Table 4: "Mean bean yields (kg ha-1) by bean type and previous crop at four MN locations from 2011-2014." Row: "Kidney 1698 b 980 c 1257 b 1655 c 1398 E". Row: "Corn 2026 b 1506 a 1781 b 1939 b 1813 A".
5. Ontario Ministry of Agriculture, Food and Rural Affairs. 2022. Agronomy Guide for Field Crops, Chapter 5: Dry Edible Beans. https://www.ontario.ca/files/2022-10/omafra-agronomy-guide-for-field-crops-chapter-5-en-2022-10-13.pdf. Government extension. Quotes in sections 2.1 and 4.2.
6. Moran, M. 2017 (updated Jan 29 2018). Dry Edible Bean Seasonal Summary. Field Crop News (OMAFRA). https://fieldcropnews.com/2017/12/dry-edible-bean-seasonal-summary/. Government extension reporting Agricorp data. Quotes: "Kidney beans – 2264 lb/ac", "Adzuki beans – 1375 lb/ac", "White beans – 2154 lb/ac", "Black beans – 2030 lb/ac", "Cranberry beans – 2376 lb/ac".
7. OMAFA Field Crop Team. Nov 20 2025. Dry Bean Seasonal Summary 2025. Field Crop News. https://fieldcropnews.com/?p=29699. Government extension. Quotes: "In 2025, approximately 130,000 acres of dry beans were insured by Agricorp in Ontario." "Agricorp has not yet reported average yields." "Yields are reported to be below average."
8. Field Crop News Team. Apr 2 2025. Site Selection and Crop Rotation. https://fieldcropnews.com/?p=27191. Government extension (same text as reference 5).
9. Statistics Canada. Table 32-10-0359-01, Estimated areas, yield, production, average farm price and total farm value of principal field crops, in metric and imperial units. https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3210035901 (full CSV downloaded 2026-11-14). Government statistics. Footnote 46 quoted in 4.4.
10. Statistics Canada. Table 32-10-0365-01, Area, production and farm gate value of marketed vegetables. https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3210036501 (full CSV downloaded 2026-11-14). Government statistics.
11. Statistics Canada. Table 32-10-0364-01, Area, production and farm gate value of marketed fruits. https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3210036401 (full CSV downloaded 2026-11-14). Government statistics.
12. OMAFRA. Area, Production and Farm Value of Specified Commercial Vegetable Crops, Ontario, 2025 (veg_all24-25_en.xlsx). Ontario Data Catalogue, https://data.ontario.ca/dataset/ontario-commercial-vegetable-crops-production. Government statistics. No melon rows.
13. Andrews, B. Feb 20 2009. Growing rice in southern Ontario. Top Crop Manager. https://www.topcropmanager.com/growing-rice-in-southern-ontario-4315/. Industry press. Quotes in 2.4. Also: "Brookston clay is the major, flat clay soil in Essex, Chatham-Kent and the southern edge of Lambton County."
14. Craig, S. Jan 7 2020. Bringing rice to Canadian fields. Ontario Agricultural College, University of Guelph. https://www.uoguelph.ca/oac/news/bringing-rice-canadian-fields. Other (university news). Quote: "an average yield of 6,920 lbs. per acre (or 154 bushels per acre)".
15. Baxter, M. Jan 2 2012. Mung bean production may offer diversification opportunities for Ontario growers. Better Farming. https://betterfarming.com/magazines/better-farming-ontario/featured-articles/mung-bean-production-may-offer-diversification-opportunities-for-ontario-growers. Industry press. Quotes in 2.6 and 3.4.
16. Olson, M. et al. 2011. Evaluation of mungbean accessions for the southern Canadian prairies. Canadian Journal of Plant Science 91:137-141. Peer-reviewed. Not accessed (paywall, 403).
17. Munroe, J., K. Janovicek, D. Hooker. Jan 17 2023. Putting the economics to a three-crop rotation in Ontario: Wheat improves corn and soybean yields and returns. Field Crop News. https://fieldcropnews.com/2023/01/putting-the-economics-to-a-three-crop-rotation-in-ontario-wheat-improves-corn-and-soybean-yields-and-returns/. Government extension summarising peer-reviewed work. Quotes in 4.8.
18. Janovicek, K., D. Hooker, A. Weersink, R. Vyn, B. Deen. 2021. Corn and soybean yields and returns are greater in rotations with wheat. Agronomy Journal 113(2):1691-1711. https://doi.org/10.1002/agj2.20605. Peer-reviewed. Abstract only, via FAO AGRIS https://agris.fao.org/search/en/records/65df69164c5aef494fe28f41.
19. Hardman, L.L., E.S. Oplinger, E.E. Schulte, J.D. Doll, G.L. Worf. May 1990. Dry Field Bean. Alternative Field Crops Manual, UW-Madison and UMN Extension. https://corn.agronomy.wisc.edu/Crops/FieldBean.aspx. Extension. Quotes in 4.9.
20. King, C. Nov 6 2008. Exploring the possibility of mung bean production. Top Crop Manager. https://www.topcropmanager.com/exploring-the-possibility-of-mung-bean-production-4139/. Industry press. Alberta only. Quote: "There's a lot of work to be done before it's a commercial crop."

Pages that failed: core.ac.uk/download/226127335.pdf (403); OMAFRA CropOp rice and mung pages (403 / "Web App - Unavailable"); web.archive.org (blocked); cdnsciencepub.com CJPS10062 (403); Farms.com rice article (404); Purdue AFCM drybean.html (404); scisoc.confex.com Olson poster (404).
