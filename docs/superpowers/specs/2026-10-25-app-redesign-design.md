# App redesign — design

**Date:** 2026-10-25
**Builds on:** `2026-10-23-cricket-analytics-design.md` (pipeline, model, player value — all built and pushed).

## Why

Devarsh looked at the live demo and found it "very superficial and not accurate", with weak visuals. He wants:
- better looks and a plain-English explanation of every chart;
- depth on individual **teams**, not just matches;
- opponent statistics, fall of wickets, and the starting win probability for each match.

The audience is still recruiters and hiring managers for grad data analyst / BA / AI roles in Sydney. A recruiter gives it about 30 seconds, so the first screen must say what this is and show a finding. A hiring manager who digs in should find cricket depth that is correct.

## Goals

1. A **home page** (front door): what the app does in one line, three headline findings in plain English, a featured match linking to its match page, and buttons into matches and teams.
2. A **match page** for any match in the data (approved mockup: `.superpowers/brainstorm/64669-1792846495/content/match-page-v2.html`):
   - scoreboard for both innings and the result;
   - starting win chance (chasing team, before ball one);
   - win-probability line across the chase with every fall of wicket marked;
   - 3–4 turning points: the overs that moved win probability most, each with a one-sentence explanation generated from the data (who, what happened, probability before → after);
   - runs per over (Manhattan) for both innings;
   - batting and bowling scorecards for both sides, with the fall-of-wickets list (score/wicket number, batter, over);
   - player impact: top win probability added (WPA) in this match, e.g. "Kohli +23 points";
   - head-to-head strip: the two teams' record against each other in that competition.
3. A **team page** for any IPL or BBL franchise or T20I nation (approved mockup: `team-page-v2.html`):
   - record: overall, batting first, chasing, and the last two seasons;
   - wins per season (bar chart);
   - head-to-head against every opponent; choosing an opponent lists every meeting, each linking to its match page;
   - phase comparison (powerplay 1–6, middle 7–15, death 16–20): run rate and wickets lost per innings, team vs the rest of its competition, since 2023, with one plain-English line saying where the team is strong or weak;
   - top batters and bowlers for this team (runs, strike rate, wickets, economy);
   - home ground record.
4. **Accuracy fix:** retrain the model on everything before 2025-01-01 and test on 2025–26 (358 matches). Match pages show win probability from this model.
5. Every chart gets a one-line "what this means" caption in plain English.
6. The existing Model and Players tabs stay, moved under an "About the model" section.

## Non-goals

- First-innings win-probability model (still the deferred stretch Task 7). The win-probability line covers the chase only; the first innings gets scorecard, Manhattan and fall of wickets but no probability line.
- Live or upcoming matches. Data is Cricsheet history only.
- Player profile pages.
- Moving off Streamlit.

## Anti-goals

- Any number on screen that is wrong. Every headline claim, turning-point sentence and team stat must come from the data, not hand-written. A wrong stat in front of a cricket-literate hiring manager is worse than no stat.
- Renamed teams counted as two teams (e.g. RCB split into "Bangalore" and "Bengaluru").
- Jargon without explanation ("WPA", "Brier") on the main pages.

## Decided

- **Train/test split:** train before 2025-01-01, test 2025-01-01 onward. (Devarsh: "okay".)
- **Front door** is a home page, not a match. (Devarsh: "Front door".)
- **Match and team page contents** as listed above. (Devarsh approved both mockups.)
- The "IPL changed in 2023" finding stays in the memo and home page as a descriptive fact (16% → 32% of 200+ chases won). It no longer depends on the old model split.
- **Team records count every match** (Devarsh: "A"). Records, head-to-heads, wins per season and ground records include ties, no-results and rain-affected (DLS / shortened) games, shown as W–L–T–NR, so totals match Cricinfo. This needs a second, looser match table alongside the strict one the model uses. Rain-affected, tied and miscounted-over games still get a match page (scoreboard, scorecards, Manhattan, fall of wickets) but no win-probability line, with a short note saying why. Super-over ties count as ties in W–L–T–NR, with the super-over winner noted on the match page. Scope rule unchanged: IPL, BBL, and men's T20Is between the 12 full members only.

## Constraints

- Stay on Streamlit; deploy target is Streamlit Community Cloud from `Devarsh-04/cricket-analytics`, branch `main`, file `app/streamlit_app.py`. The app reads only committed files in `app/data/` (the DuckDB file is not in the repo). Keep `app/data/` small enough for git (currently 4.4 MB; aim under ~25 MB).
- App dependencies stay to what `app/requirements.txt` has (altair, pandas, pyarrow, streamlit).
- Existing tests (22 pytest, 17 dbt) keep passing; new logic gets tests.
- Data cleaning goes in dbt staging so every downstream number uses it:
  - team renames: Royal Challengers Bangalore → Royal Challengers Bengaluru; Kings XI Punjab → Punjab Kings; Delhi Daredevils → Delhi Capitals; Rising Pune Supergiants → Rising Pune Supergiant;
  - venue name variants merged (e.g. "M Chinnaswamy Stadium" / "M.Chinnaswamy Stadium").
- The match page needs first-innings deliveries and full scorecards, which `predictions.parquet` (chase only) doesn't have. A new export of both innings is needed.

## My calls (Claude)

- Navigation: Streamlit multipage (`st.navigation` / pages) — Home, Matches, Teams, About the model. Match and team selection carried in query params so a match page has a shareable URL.
- Charts in Altair. Two clearly different colours for the two teams (fixes the "two blues" issue).
- Turning points = the overs with the largest absolute change in chase win probability; sentence template built from that over's balls (runs, wickets, bowler, batter on strike most).
- Head-to-head and team stats include all matches in the cleaned data (both innings), not just test-set matches. Win-probability lines are shown for all chases; the page labels whether the match was in the test set (model never saw it).
- **Season** = Cricsheet's `info.season` (e.g. "2024/25" for BBL), captured in `ingest.py`, so a BBL season isn't split across two calendar years. Requires a re-ingest from the already-downloaded JSON.
- **Home ground** = the team's most-played venue, labelled "Most-played ground" (Cricsheet has no home-team field).
- **Home-page findings** (all computed from data, none depend on the old split): (1) IPL 200+ chases won, before vs since 2023; (2) death-over balls swing a chase most per ball; (3) average win-probability cost of a wicket, recomputed on the 2025–26 test set. The memo's "model underrates IPL since 2023" finding is re-measured under the new split and kept, reworded or dropped depending on what the numbers show.
- Ablation validation slice moves to 2024 (the last year of training data), keeping the "validate before touching test" rule.
- MEMO.md and README numbers refreshed for the new split.

## Left to the builder

- File layout for the new pages and export script.
- Exact table/parquet shapes for the new exports.
- Wording of captions, within the plain-English rule.
- Styling details beyond the approved mockups.

## Known limitations carried over

- Run-out of the non-striker credited to the striker.
- Penalty runs awarded during a chase ignored.
- Players with identical names are not distinguished.
