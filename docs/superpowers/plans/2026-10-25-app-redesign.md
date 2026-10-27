# App Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-screen demo into a Home / Matches / Teams / About-the-model app with full scorecards, fall of wickets, starting win chance, team records and head-to-heads, backed by cleaned team/venue names and a model retrained through 2024.

**Architecture:** dbt gains a loose `stg_all_matches` / `stg_all_deliveries` pair (every in-scope match, cleaned names, outcome columns); the existing strict `stg_matches` / `stg_deliveries` are derived from them so the model is unchanged except for the split. A new `export_app.py` writes `matches.parquet`, `deliveries.parquet` (both innings, chase win probability joined on) and `findings.json` into `app/data/`. All page logic lives in pure, tested functions in `app/stats.py`; Streamlit pages in `app/views/` only render.

**Tech Stack:** Python 3, DuckDB, dbt-duckdb 1.12, LightGBM, pandas, Streamlit 1.66 (`st.navigation`), Altair.

**Spec:** `docs/superpowers/specs/2026-10-25-app-redesign-design.md`

## Global Constraints

- Work on a branch `redesign` off `main`. Never force push, never `--no-verify`. Commit at each task's commit step (approved by Devarsh as part of plan execution); do not push.
- App dependencies stay exactly: altair, pandas, pyarrow, streamlit (`app/requirements.txt`). No new packages anywhere.
- `app/data/` total under 25 MB; it is committed and is the only data the deployed app reads.
- Scope: IPL, BBL, and men's T20Is between the 12 full members only; male; 20-over matches.
- Split: train `start_date < 2025-01-01`, test `>= 2025-01-01`. Ablation validation on 2024.
- Team records are W–L–T–NR over every in-scope match, including ties, no-results and DLS/shortened games. Super-over ties count as T.
- No number on any page is hand-typed; every stat, finding and turning-point sentence is computed.
- Plain English on main pages: no "WPA", "Brier", "AUC" outside About the model. Win probability is called "win chance"; WPA is "points of win chance".
- Every chart has a one-line caption saying what it means.
- Two team colours: chasing side `#2563eb`, defending side `#ea580c`.
- Existing tests keep passing (22 pytest, 17 dbt) apart from deliberate updates listed in tasks.

## Review Focus

1. A tied / no-result / DLS match opened on the match page → page renders scorecards and a note "No win-chance line: <reason>", no exception. (Task 8 test)
2. A match with no first innings (no-result abandoned after toss) or only one innings → scorecard shows what exists, no exception. (Tasks 5, 8 tests)
3. Team that existed briefly (Kochi Tuskers Kerala, one season) or has no matches since 2023 → team page renders; phase table shows "No matches since 2023". (Tasks 6, 9 tests)
4. Renamed teams/venues in data from any source (team1/team2/winner/batting_team/eliminator) → all map to one name; no raw alias appears anywhere in exports. (Task 2 dbt test)
5. Invalid or stale query param (`?match=nope`, `?team=Foo`) → page falls back to its selectors, no exception. (Tasks 8, 9 tests)

---

### Task 1: Ingest season and super-over eliminator

**Files:**
- Modify: `ingest.py` (`flatten_match` row dict)
- Test: `tests/test_ingest.py`

**Interfaces:**
- Produces: `raw_matches` gains `season VARCHAR` (`str(info["season"])`) and `eliminator VARCHAR` (`outcome.get("eliminator")`).

- [ ] **Step 1: Write failing tests** — `test_flatten_captures_season` (fixture `match_ok.json`: `row["season"] == str(<fixture's info.season>)`, add `"season"` to the fixture if absent) and `test_flatten_captures_eliminator` (build a dict from `match_ok.json` with `outcome = {"result": "tie", "eliminator": "Mumbai Indians"}`; assert `row["eliminator"] == "Mumbai Indians"` and `row["winner"] is None`).
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_ingest.py -v` — Expected: 2 FAIL with `KeyError: 'season'` / `'eliminator'`.
- [ ] **Step 3: Implement** the two keys in `flatten_match`.
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: all pass (24).
- [ ] **Step 5: Re-ingest** `.venv/bin/python ingest.py` (zips already in `data/zips`, no download). Expected: `select count(*) from raw_matches where season is null` → 0.
- [ ] **Step 6: Commit** `feat: capture season and super-over eliminator at ingest`

### Task 2: dbt — loose match tables with cleaned names

**Files:**
- Create: `dbt/seeds/team_aliases.csv`, `dbt/seeds/venue_aliases.csv`, `dbt/models/staging/stg_all_matches.sql`, `dbt/models/staging/stg_all_deliveries.sql`, `dbt/tests/assert_no_alias_names.sql`, `dbt/tests/assert_one_outcome_per_match.sql`
- Modify: `dbt/models/staging/stg_matches.sql`, `dbt/models/staging/stg_deliveries.sql`, `dbt/models/sources.yml` (add `season`, `eliminator` if columns are listed), `dbt/models/schema.yml`

**Interfaces:**
- Consumes: Task 1 columns.
- Produces:
  - `stg_all_matches`: `match_id, competition, start_date, season_year INT, season VARCHAR, venue VARCHAR (cleaned), city, team1, team2, winner, outcome VARCHAR ('won'|'tie'|'no result'), method, eliminator, bat_first VARCHAR, has_wp BOOLEAN`. `season` = Cricsheet season for BBL (e.g. `2024/25`), `cast(year(start_date) as varchar)` for IPL and T20I (Cricsheet labels IPL 2008 "2007/08"). `bat_first` = innings-1 batting team (null if no innings). `has_wp` = match_id in `stg_matches`.
  - `stg_all_deliveries`: same columns as `stg_deliveries`, for every match in `stg_all_matches`, `batting_team` cleaned.
  - `stg_matches` = `stg_all_matches` rows passing the existing strict filters (column list unchanged + `season`); `venue_clean` kept as an alias of cleaned `venue` so downstream SQL/Python still works. `stg_deliveries` = `stg_all_deliveries` joined to `stg_matches`.

Seed contents (alias → canonical):
- `team_aliases.csv` (`alias,team`): Royal Challengers Bangalore→Royal Challengers Bengaluru; Kings XI Punjab→Punjab Kings; Delhi Daredevils→Delhi Capitals; Rising Pune Supergiants→Rising Pune Supergiant.
- `venue_aliases.csv` (`alias,venue`), applied after `trim(split_part(venue, ',', 1))`: M.Chinnaswamy Stadium→M Chinnaswamy Stadium; Feroz Shah Kotla→Arun Jaitley Stadium; Punjab Cricket Association Stadium→Punjab Cricket Association IS Bindra Stadium; Sardar Patel Stadium→Narendra Modi Stadium; Zayed Cricket Stadium→Sheikh Zayed Stadium; Subrata Roy Sahara Stadium→Maharashtra Cricket Association Stadium; Simonds Stadium→GMHBA Stadium; Aurora Stadium→University of Tasmania Stadium; Western Australia Cricket Association Ground→W.A.C.A. Ground. Then audit T20I venues with `select venue, count(*) from stg_all_matches where competition='t20i' group by 1 order by 1` and add rows only for names that are clearly the same ground (dotted/undotted, sponsor renames).

- [ ] **Step 1: Write failing dbt tests.** `assert_no_alias_names`: returns rows where any of `team1, team2, winner, bat_first, eliminator` in `stg_all_matches`, or `batting_team` in `stg_all_deliveries`, is in `team_aliases.alias`, or `venue` is in `venue_aliases.alias`. `assert_one_outcome_per_match`: rows where `outcome='won'` and `winner is null`, or `outcome!='won'` and `winner is not null`. Add schema tests: `stg_all_matches.match_id` unique/not_null; `outcome` accepted_values `['won','tie','no result']`.
- [ ] **Step 2: Run** `cd dbt && ../.venv/bin/dbt build` — Expected: FAIL (models don't exist).
- [ ] **Step 3: Implement** seeds and the four models.
- [ ] **Step 4: Run** `../.venv/bin/dbt seed && ../.venv/bin/dbt build` — Expected: all models and tests pass (17 existing + new). Check: `select count(*) from stg_all_matches where competition='ipl' and (team1 like 'Royal Challengers%' or team2 like 'Royal Challengers%')` returns more matches than the strict table, and `select outcome, count(*) from stg_all_matches group by 1` shows ties and no-results.
- [ ] **Step 5: Commit** `feat(dbt): loose match tables with cleaned team and venue names`

### Task 3: Retrain on data through 2024

**Files:**
- Modify: `winprob.py` (`CUTOFF`, `ablation` default, `main` metrics key), `app/streamlit_app.py:91-93` (key and caption — this file is replaced in Task 7, so only keep it running)
- Test: `tests/test_winprob.py`

**Interfaces:**
- Produces: `CUTOFF = "2025-01-01"`; `ablation(train, cutoff="2024-01-01")`; `metrics.json` key `ablation_validation_2024`; `predictions.parquet` unchanged in shape.

- [ ] **Step 1: Write failing test** `test_cutoff_is_2025`: `assert winprob.CUTOFF == "2025-01-01"`, and `inspect.signature(winprob.ablation).parameters["cutoff"].default == "2024-01-01"`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_winprob.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement**; rename the metrics key and the app's reference/caption to 2024.
- [ ] **Step 4: Run** `.venv/bin/python winprob.py && .venv/bin/python player_value.py && .venv/bin/pytest -q` — Expected: model Brier below baseline Brier overall (record both numbers in the commit message body); all tests pass.
- [ ] **Step 5: Commit** `feat: retrain through 2024, test on 2025-26`

### Task 4: App data export

**Files:**
- Create: `export_app.py`, `tests/test_export.py`
- Modify: `README.md` "Run it yourself" block (add `python3 export_app.py` after `player_value.py`)

**Interfaces:**
- Consumes: `stg_all_matches`, `stg_all_deliveries` (Task 2); `app/data/predictions.parquet` (Task 3) with `match_id, over, ball_seq, wp, wp_before, in_test`.
- Produces in `app/data/`:
  - `matches.parquet`: every `stg_all_matches` column plus `inn1_team, inn1_runs, inn1_wkts, inn1_balls, inn2_team, inn2_runs, inn2_wkts, inn2_balls` (nullable ints; legal balls), `in_test BOOLEAN`, `start_wp FLOAT` (chase win chance before ball one; null when `has_wp` false).
  - `deliveries.parquet`: `match_id, innings, batting_team, over, ball_seq, batter, batter_id, bowler, bowler_id, runs_batter, runs_extras, runs_total, wides, noballs, is_legal, is_wicket, player_out, wicket_kind, wp, wp_before` (wp columns null for innings 1 and for matches without `has_wp`). Team/player string columns stored as pandas `category`.
  - `findings.json`: `{"ipl_200_chases": {"before_2023": {"won": int, "n": int}, "since_2023": {"won": int, "n": int}}, "swing_per_ball": {"powerplay": float, "middle": float, "death": float}, "wicket_cost": float}`. Swing and wicket cost from test-set balls (`in_test`), in win-chance points (0–100). 200+ chases from `matches` where `has_wp` and target ≥ 200.
- Functions: `innings_totals(deliveries: pd.DataFrame) -> pd.DataFrame` (one row per match_id with the `inn*` columns), `findings(matches: pd.DataFrame, deliveries: pd.DataFrame) -> dict`, `main() -> None`.

- [ ] **Step 1: Write failing tests** with hand-built frames: `test_innings_totals` (two innings, a wide, a wicket → exact runs/wkts/legal balls; a match with only innings 1 gets null `inn2_*`); `test_findings_counts_200_chases` (three chases: 199 target won, 200 won, 210 lost, dates split around 2023 → exact `won`/`n`); `test_findings_wicket_cost` (two test-set wicket balls with wp deltas −0.10, −0.04 → `wicket_cost == 7.0`).
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_export.py -v` — Expected: FAIL (`ModuleNotFoundError: export_app`).
- [ ] **Step 3: Implement**; `main()` reads from `data/cricket.duckdb` read-only and the predictions parquet, joins wp on `(match_id, over, ball_seq)` for innings 2.
- [ ] **Step 4: Run** `.venv/bin/python export_app.py && du -sh app/data && .venv/bin/pytest -q` — Expected: total under 25 MB; all pass; `matches.parquet` row count equals `select count(*) from stg_all_matches`.
- [ ] **Step 5: Commit** `feat: export matches, deliveries and findings for the app`

### Task 5: Match stats functions

**Files:**
- Create: `app/stats.py`, `tests/test_stats_match.py`
- Modify: `pytest.ini` → `pythonpath = . app`

**Interfaces:**
- Consumes: `deliveries.parquet` rows for one match (columns from Task 4).
- Produces (all take `d: pd.DataFrame` = one match's deliveries):
  - `batting_card(d, innings: int) -> pd.DataFrame` columns `batter, dismissal, runs, balls, fours, sixes, strike_rate`, in batting order (first appearance as batter or player_out). Balls = deliveries with `wides == 0`. `dismissal` = `wicket_kind` + bowler for bowler-credited kinds, `"run out"` for run outs, `"not out"` otherwise.
  - `bowling_card(d, innings: int) -> pd.DataFrame` columns `bowler, overs ("3.2" format), runs, wickets, economy`. Runs conceded = `runs_batter + wides + noballs`. Wickets exclude `run out`, `retired hurt`, `retired out`, `retired not out`, `obstructing the field`.
  - `fall_of_wickets(d, innings: int) -> pd.DataFrame` columns `wicket (1..n), score (runs at that ball, cumulative runs_total), batter (player_out), over ("14.3", legal-ball count within over)`.
  - `runs_per_over(d) -> pd.DataFrame` columns `innings, team, over (1-based), runs, wickets`.
  - `turning_points(d, n: int = 3) -> list[dict]` over innings 2 only; each dict `over (1-based), wp_from, wp_to, text`; picks the `n` overs with largest `abs(wp_last_ball - wp_before_first_ball)`, returned in over order; empty list when `wp` is all null. `text`: if wickets in the over → `"{bowler} took {k} wicket(s) ({names}) for {r} runs"`; else → `"{top_batter} scored {b} of the {r} runs off {bowler}"`, where bowler is the one who bowled most balls of that over.
  - `match_impact(d, top: int = 3) -> pd.DataFrame` columns `player, role ('bat'|'bowl'), points` (sum of `wp - wp_before` × 100, batters +, bowlers −), largest `points` first, innings 2 only; empty when wp null.

- [ ] **Step 1: Write failing tests** on a hand-built two-innings frame (≈12 balls per innings incl. a wide, a no-ball, a bowled wicket and a run out): exact batting card rows (run-out batter shows `"run out"`, bowler not credited), bowling overs `"1.4"` after 10 legal balls, FOW scores/overs, `runs_per_over` totals equal innings totals, `turning_points(d, 1)` picks the over with the wicket and its text contains the bowler and dismissed batter, `match_impact` signs; `test_card_handles_missing_innings` (only innings 1 present → `batting_card(d, 2)` is empty, no exception); `test_turning_points_empty_without_wp`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_stats_match.py -v` — Expected: FAIL (`ModuleNotFoundError: stats`).
- [ ] **Step 3: Implement** in `app/stats.py`.
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: all pass. Spot-check on real data: match `1535465` batting card has Kohli 75 (42) and `turning_points` includes over 4.
- [ ] **Step 5: Commit** `feat: scorecard, fall of wickets and turning points`

### Task 6: Team stats functions

**Files:**
- Modify: `app/stats.py`
- Create: `tests/test_stats_team.py`

**Interfaces:**
- Consumes: `matches.parquet`, `deliveries.parquet` (Task 4).
- Produces (`m` = matches, `d` = deliveries, filtered to one competition by the caller):
  - `team_matches(m, team) -> pd.DataFrame` rows where team is team1 or team2, plus `opponent`, `result` (`'W'|'L'|'T'|'NR'`), sorted by date.
  - `record(tm: pd.DataFrame) -> dict` `{"played","won","lost","tied","nr"}`; also used on subsets.
  - `team_summary(m, team) -> dict` `{"overall": record, "batting_first": record, "chasing": record, "last_two_seasons": record, "seasons": [two season labels]}`; batting first = `bat_first == team`; last two seasons = the two latest distinct `season` values the team played.
  - `wins_by_season(m, team) -> pd.DataFrame` `season, played, won`.
  - `head_to_head(m, team) -> pd.DataFrame` `opponent, played, won, lost, tied, nr`, most played first.
  - `phase_table(d, m, team, since: str = "2023-01-01") -> pd.DataFrame` `phase ('Powerplay'|'Middle'|'Death'), team_run_rate, rest_run_rate, team_wkts, rest_wkts`; overs 1–6 / 7–15 / 16–20 (0-based `over` 0–5 / 6–14 / 15–19); run rate = runs_total / legal balls × 6; wickets = wickets per innings batted in that phase; "rest" = all other batting innings in `d`/`m` since the date. Empty frame when the team batted no innings since the date.
  - `phase_note(pt: pd.DataFrame) -> str` one sentence naming the phase with the biggest run-rate edge (or deficit) and the wicket comparison there, e.g. `"Best in the powerplay: 0.5 runs an over faster than the rest of the league, losing a quarter fewer wickets."`; fractions phrased from the actual ratio (nearest of "a tenth", "a fifth", "a quarter", "a third", "half"; percentage otherwise).
  - `top_players(d, team, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]` batters (`batter, runs, balls, strike_rate`, by runs) and bowlers (`bowler, wickets, balls, economy`, by wickets) for deliveries where the team batted / bowled.
  - `most_played_ground(m, team) -> tuple[str, dict]` venue with most matches and the team's record there.

- [ ] **Step 1: Write failing tests** on a hand-built 6-match `m` (incl. a tie with eliminator, a no-result with no innings, a DLS win, a renamed-team-free set) and matching `d`: exact `team_summary` counts (tie counted T, no-result NR, DLS win W); `head_to_head` row values; `wins_by_season` uses BBL label `"2024/25"` for a January 2025 match; `phase_table` run rates to 2 dp; `phase_note` names the right phase and says "a quarter" for a 0.75 wicket ratio; `test_phase_table_empty_when_no_recent_matches`; `test_brief_team_renders_stats` (team with one match → every function returns without exception).
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_stats_team.py -v` — Expected: FAIL (`AttributeError`).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: all pass. Spot-check: RCB IPL `head_to_head` and `team_summary` totals now include ties/NR (compare against Cricinfo for RCB v CSK; record the comparison in the commit body).
- [ ] **Step 5: Commit** `feat: team records, head-to-head and phase stats`

### Task 7: Navigation, Home and About pages

**Files:**
- Modify: `app/streamlit_app.py` (becomes the navigation entry only)
- Create: `app/load.py`, `app/views/home.py`, `app/views/about.py`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: Task 4 files, `metrics.json`, `calibration.parquet`, `player_value.parquet`.
- Produces:
  - `load.py`: `@st.cache_data` loaders `matches()`, `deliveries()`, `findings()`, `metrics()`, `calibration()`, `players()`; constants `COMPETITIONS = {"ipl": "IPL", "bbl": "BBL", "t20i": "T20I"}`, `CHASE_COLOUR = "#2563eb"`, `DEFEND_COLOUR = "#ea580c"`; `match_link(match_id) -> str` = `f"/match?id={match_id}"`; `team_link(comp, team) -> str` = `f"/team?comp={comp}&team={quote(team)}"`.
  - `streamlit_app.py`: `st.set_page_config(page_title="T20 Win Probability", layout="wide")`; `st.navigation([st.Page("views/home.py", title="Home", default=True), st.Page("views/match.py", title="Matches", url_path="match"), st.Page("views/team.py", title="Teams", url_path="team"), st.Page("views/about.py", title="About the model", url_path="about")]).run()`.
  - Home: one-line description; three finding cards from `findings.json` (IPL 200+ chases before vs since 2023 as "x% → y%"; death-over swing vs powerplay/middle as "×N more per ball"; wicket cost "a wicket costs the chasing side N points of win chance"), each with a caption; a featured match card (`1535465` if present in `matches`, else the latest `has_wp` match) showing teams, score, start win chance and a link; buttons/links to Matches and Teams.
  - About: the current Model and Players tabs' content moved unchanged in substance (metrics table, calibration with caption, ablation on 2024, players table), plus a short plain-English "How the win chance works" paragraph.

- [ ] **Step 1: Write failing tests** in `tests/test_app.py`: `test_home_renders` (`AppTest.from_file("../app/views/home.py")` runs, no exception, markdown contains "%" from the 200+ finding); `test_about_renders` (no exception; radio interactions from the old test still work). Create stub `views/match.py` and `views/team.py` (one `st.title`) so navigation resolves; `test_entry_renders` on `../app/streamlit_app.py`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_app.py -v` — Expected: FAIL (files missing).
- [ ] **Step 3: Implement.** Views import `load` and `stats` (app dir is on `sys.path` under Streamlit; `pytest.ini` covers tests).
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: all pass. Restart the local server (stop the old background `streamlit run`, start a new one) and check Home and About in Chrome.
- [ ] **Step 5: Commit** `feat: multipage app with home and about pages`

### Task 8: Match page

**Files:**
- Modify: `app/views/match.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: Task 5 functions, Task 7 `load`.
- Behaviour:
  - Selectors: competition, season, team (optional, "All teams"), match (label `"{date:%d %b %Y} · {team1} v {team2} · {venue}"`, newest first). `st.query_params["id"]`, if it names a known match, preselects all four; unknown ids are ignored.
  - Header scoreboard: both innings `"{team} {runs}/{wkts} ({overs} ov)"`, result line (`"{winner} won"`, `"Tied — {eliminator} won the super over"`, `"No result"`, `" (DLS)"` suffix when `method`), venue/date, and `"Test-set match — the model never saw it"` when `in_test`.
  - If `has_wp`: big "Starting win chance" number (`start_wp` of chasing side), win-chance Altair line over legal ball number with wicket points (tooltip: batter out, score, over), 50% rule, caption; turning points as 3 short cards; "Biggest impact" list from `match_impact` in "points of win chance". Else: `st.info("No win-chance line: <reason>")` with reason from outcome/method ("tied", "no result", "rain-shortened (DLS)", "chase shortened before it started", "over miscounted by umpires").
  - Runs-per-over grouped bars for both innings in team colours, wickets as dots, caption.
  - Two tabs/columns with each innings' batting card, bowling card and FOW list.
  - Head-to-head strip: `head_to_head` (Task 6) for team1 in this competition, the row for team2, as "Team1 W–L–T–NR v Team2", link to team page.

- [ ] **Step 1: Write failing tests**: `test_match_page_with_wp` (set `at.query_params["id"] = "1535465"`, run, no exception, a metric labelled "Starting win chance" exists); `test_match_page_tie` (query param = a tied match id picked from `matches.parquet` in the test), no exception, an info element containing "No win-chance line"; `test_match_page_bad_id` (`"nope"` → no exception, selectors shown).
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_app.py -v` — Expected: the three new tests FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: all pass. Open `http://localhost:8501/match?id=1535465` in Chrome; compare against the approved mockup (start 65%, Kohli 75 (42), FOW, turning points).
- [ ] **Step 5: Commit** `feat: match page with scorecards, fall of wickets and turning points`

### Task 9: Team page

**Files:**
- Modify: `app/views/team.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: Task 6 functions, Task 7 `load`.
- Behaviour: selectors competition + team (from `matches` team1/team2 in that competition, sorted); `?comp=&team=` preselect when valid, ignored otherwise. Sections in mockup order: record tiles (overall, batting first, chasing, last two seasons — each "W–L" with T/NR shown when non-zero and win %); wins-per-season bar chart with caption; head-to-head table, then an opponent selectbox listing every meeting (date, venue, result, score line) each with a `match_link`; phase table team vs rest of competition since 2023 with `phase_note` sentence (or "No matches since 2023"); top batters and bowlers tables; most-played ground with record.

- [ ] **Step 1: Write failing tests**: `test_team_page_rcb` (`comp=ipl`, `team=Royal Challengers Bengaluru` → no exception, head-to-head dataframe present); `test_team_page_short_lived_team` (`Kochi Tuskers Kerala` → no exception, text "No matches since 2023"); `test_team_page_bad_team` (`team=Foo` → no exception).
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_app.py -v` — Expected: the three new tests FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: all pass. Check RCB, Sydney Sixers and India in Chrome.
- [ ] **Step 5: Commit** `feat: team page with records, head-to-head and phase comparison`

### Task 10: Refresh memo and README, deploy-ready check

**Files:**
- Modify: `MEMO.md`, `README.md`

- [ ] **Step 1:** Recompute every MEMO number on the 2025–26 test set (counts, Brier, phase swing table, wicket cost, IPL predicted-vs-actual gap, underrated players, ablation on 2024). Keep, reword or drop finding 2's "model underrates IPL" part according to the new numbers; keep the 16% → 32% descriptive fact. Update README results table, test counts, pipeline diagram (add `export_app.py`, new dbt test count) and limits.
- [ ] **Step 2: Fresh-clone check:** `git clone . ../ca-check && cd ../ca-check && python3 -m venv .venv && .venv/bin/pip install -r app/requirements.txt && .venv/bin/streamlit run app/streamlit_app.py --server.headless true` — Expected: Home, a match and a team load with no error using only committed `app/data/`. Remove `../ca-check` after.
- [ ] **Step 3: Run** `.venv/bin/pytest -q && (cd dbt && ../.venv/bin/dbt build)` — Expected: all pass.
- [ ] **Step 4: Commit** `docs: refresh memo and README for the 2025-26 test set`
