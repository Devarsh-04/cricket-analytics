# T20 Cricket Win-Probability Analytics — Design

Date: 2026-10-23
Owner: Devarsh Varma

## Intent and the why

A portfolio project for graduate data analyst / BA roles in Sydney. Devarsh's CV is
strong on ML research (HalluciGuard, SolarVision) but has no SQL/BI project. This fills
that gap.

The one thing a hiring manager should think after opening the repo:
**"This person knows proper analytics and predictions."** Credibility comes from
rigour — clean, tested data models, honest model evaluation, and clear written
findings — not from flashy visuals.

Sports was chosen because Devarsh is comfortable being questioned on it in an
interview. It must be framed like business analytics (question → metric → model →
validation → recommendation) so it doesn't read as a hobby project.

## Goals

1. **Data pipeline:** Cricsheet ball-by-ball T20 data → DuckDB → dbt models
   (`matches`, `innings`, `deliveries`, `players`, plus marts) with dbt data tests
   (unique ball keys, innings totals reconcile with summed deliveries, no orphan
   players/matches).
2. **Win-probability model:** probability the chasing team wins, after every ball of
   the second innings. Features at minimum: runs required, balls remaining, wickets in
   hand, venue, season. Validation:
   - time-based split (train on older seasons, test on newer — no leakage)
   - compared against a simple baseline (e.g. logistic regression on runs/balls/wickets,
     or historical lookup table)
   - calibration (reliability curve + Brier score) and log loss reported
3. **Player value (secondary):** credit each ball's change in win probability to batter
   and bowler; produce a leaderboard and an "underrated vs raw stats" comparison.
   **Chase-only** (Devarsh's decision): credits only chasing batters and defending
   bowlers. Label this clearly on the leaderboard, the comparison, and in the memo.4. **Streamlit dashboard (public, free hosting):**
   - Match explorer: pick a past match → ball-by-ball win-probability curve with key
     moments (wickets, big overs) annotated
   - Model page: calibration chart, metrics vs baseline
   - Player value leaderboard
5. **Insights memo:** one page, 3–4 findings (e.g. which phase of a T20 decides
   matches, undervalued players), written for a non-technical stakeholder.
6. **README:** results chart and accuracy numbers at the top, then how to reproduce.
7. **Stretch (week 2, only if on schedule):** first-innings win-probability model
   (same approach, features = current score, balls bowled, wickets, venue, season),
   validated the same way. If shipped, extend player value to whole careers and drop
   the chase-only label. Must not delay the core deliverables.

## Non-goals

- Betting tips or odds.
- Live match feeds / real-time scoring.
- Deep learning.
- ODI and Test formats.

## Anti-goals (failure even if it technically works)

- Looks like a hobby/fan project with no business framing.
- Model metrics that can't be defended — any leakage, no baseline, no calibration.
- A dashboard with no written interpretation.
- A repo a reviewer can't run or understand in five minutes.

## Constraints

- Timeline: **2 weeks** (Devarsh is actively job hunting; finished beats perfect).
  - Week 1: ingest, dbt models + tests, exploratory SQL analysis.
  - Week 2: model + validation, Streamlit app, memo, README, deploy.
- Free tools and hosting only.
- Public GitHub repo under Devarsh-04. Data source attribution per Cricsheet's licence.
- Python 3, PEP8, simple code; no unnecessary abstractions.

## Decided

- Data: Cricsheet (cricsheet.org), T20 only — IPL, BBL, men's T20 internationals.
- Stack (Claude's call, Devarsh delegated it): DuckDB, dbt (dbt-duckdb), Python with
  scikit-learn / LightGBM, Streamlit (Community Cloud).
- T20Is limited to matches between ICC full members (Claude's call): avoids lopsided
  associate mismatches inflating metrics and the leaderboard.
- One pooled model with a competition feature; metrics reported overall and per
  competition (IPL, BBL, T20I) (Claude's call).
- Project location: `~/Documents/cricket-analytics`.
- Timeline: 2 weeks (Claude's call, Devarsh delegated it).

## Left to the builder

- Cricsheet download format (JSON vs CSV) and ingest script details.
- Exact dbt model layering (staging / intermediate / marts) and naming.
- Final feature set beyond the minimum; LightGBM vs logistic regression as final model,
  chosen on test-set metrics.
- How data ships to Streamlit Cloud (e.g. exported Parquet of the marts in repo) so
  the deployed app doesn't need the raw-data pipeline.
- Handling rain-affected / DLS / no-result / super-over matches (exclude or flag —
  document the choice).
- Repo layout, Makefile or simple run scripts.
