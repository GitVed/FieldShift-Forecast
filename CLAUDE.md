# CLAUDE.md

Context for Claude Code. Read this first, then the two files it imports.

@SUMMARY-README.md
@TASKS.md

## What this is

FieldShift Forecast, Team Tuxedo's NASA Space Apps Toronto 2026 entry. Harrow, Ontario pilot. Main branch is Avenue 1 Harrow only.

## Rules

- Do not invent numbers, coordinates, prices, soil values, or dataset codes. If unsure, write UNVERIFIED and say how to check.
- Label every number LIVE, CACHED, or SAMPLE. The demo reads cache and never calls an API live.
- Model 2 is a transparent rule-based scorer, not an ML yield predictor.
- Model 1 follows section 3b of SUMMARY-README.md. Never use Kaggle for wheat or soy. If a crop has no source, do not score it.
- Do not reopen the Harrow-as-main decision.
- Never push to main without the team. Avenue 2 stays on `avenue-2-global`.
- Big raw downloads go in `data/raw/`, which is git-ignored.
- Plain language, short sentences, no em dashes in docs.
- Ask before large structural changes.

## How to work

- Check which branch you are on and who the user is before editing. Read TASKS.md to find their jobs.
- Only edit files the user owns, per the ownership table in TASKS.md.
- Keep README.md, SUMMARY-README.md, and TASKS.md in sync when a decision changes.
