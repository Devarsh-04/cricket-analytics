# T20 Cricket Win-Probability Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Public portfolio repo: Cricsheet T20 data → DuckDB/dbt tested models → calibrated chase win-probability model → player value → Streamlit dashboard + memo.

**Architecture:** One Python ingest script flattens Cricsheet JSON into two raw DuckDB tables. dbt (dbt-duckdb) cleans, filters and builds one ball-by-ball chase mart with tests. Python scripts train/evaluate the model and compute player value, writing Parquet into `app/data/`, which the Streamlit app reads (so the deployed app never runs the pipeline).

**Tech Stack:** Python 3.11+, duckdb, dbt-duckdb, pandas, pyarrow, scikit-learn, lightgbm, streamlit (charts via its bundled altair), pytest.

**Spec:** `docs/superpowers/specs/2026-10-23-cricket-analytics-design.md`

## Global Constraints

- T20 only: IPL, BBL, men's T20Is. T20Is only where **both** teams are ICC full members: Afghanistan, Australia, Bangladesh, England, India, Ireland, New Zealand, Pakistan, South Africa, Sri Lanka, West Indies, Zimbabwe.
- Excluded matches: `result` in (`no result`, `tie`), any `method` set (DLS), scheduled overs ≠ 20. Super-over innings ignored.
- Time split: train = matches with `start_date < 2023-01-01`, test = on/after. No feature may use information from after the ball it describes.
- Every model metric reported against the baseline, overall and per competition: Brier score, log loss, ROC AUC, 10-bin calibration table.
- Player value is chase-only unless Task 7 ships; label it "Chase-only" in app and memo.
- Free tools/hosting only. Public repo under Devarsh-04. Attribute Cricsheet per its licence (check cricsheet.org; add to README).
- PEP8, f-strings, no unnecessary abstractions, no comments that restate code.
- Commits: Devarsh must OK committing before the first commit step runs (his global rule: never commit without being asked).
- Deadline: core (Tasks 1–6) in 2 weeks. Task 7 is stretch; skip it if behind.

## Review Focus

1. **Wides/no-balls counted as balls** → `balls_remaining` wrong for every later ball. Pinned by dbt test `assert_legal_balls_max_120` and ingest test `test_extras_flags` (Tasks 1, 2).
2. **Target taken wrongly** (Cricsheet `target` missing on older files) → fall back to first-innings total + 1; pinned by singular test `assert_target_matches_first_innings` (Task 2).
3. **Terminal states** (chase already won, all out, no balls left) → model must output exactly 1.0/0.0, not a fitted guess. Pinned by `test_terminal_states_override` (Task 3).
4. **Unseen venue in test set** (new grounds after 2023) → prediction must not crash; pinned by `test_predict_unseen_venue` (Task 3).
5. **Player name collisions** (two "Mohammad Nabi"-style duplicates) → key players on Cricsheet registry id, not name; pinned by `test_registry_ids` (Task 1) and `test_player_value_keys_on_id` (Task 4).

---

## File Structure

```
cricket-analytics/
  requirements.txt
  ingest.py                    # download + flatten Cricsheet JSON → raw DuckDB tables
  dbt/
    dbt_project.yml
    profiles.yml               # duckdb at ../data/cricket.duckdb
    models/staging/stg_matches.sql
    models/staging/stg_deliveries.sql
    models/marts/chase_states.sql
    models/schema.yml          # generic tests
    tests/assert_target_matches_first_innings.sql
    tests/assert_legal_balls_max_120.sql
    tests/assert_runs_total_adds_up.sql
    tests/assert_unique_ball_key.sql
  winprob.py                   # features, split, baseline + LightGBM, evaluation, writes app/data
  player_value.py              # WPA per ball → leaderboard, writes app/data
  app/streamlit_app.py
  app/data/                    # committed Parquet outputs (small)
  tests/fixtures/match_ok.json, match_dls.json
  tests/test_ingest.py, test_winprob.py, test_player_value.py
  MEMO.md
  README.md
  data/                        # gitignored: raw zips, JSON, cricket.duckdb
```

---

### Task 1: Project setup + ingest

**Files:**
- Create: `requirements.txt`, `.gitignore` (`data/`, `.venv/`, `dbt/target/`, `dbt/logs/`), `ingest.py`
- Test: `tests/test_ingest.py`, `tests/fixtures/match_ok.json`, `tests/fixtures/match_dls.json`

**Interfaces:**
- Produces:
  - `URLS = {"ipl": "https://cricsheet.org/downloads/ipl_json.zip", "bbl": "https://cricsheet.org/downloads/bbl_json.zip", "t20i": "https://cricsheet.org/downloads/t20s_male_json.zip"}` (verify URLs on cricsheet.org/downloads before use)
  - `flatten_match(match: dict, match_id: str, competition: str) -> tuple[dict, list[dict]]`
  - `load(competitions: list[str], db_path: Path) -> None` — downloads, unzips to `data/json/<comp>/`, replaces tables `raw_matches`, `raw_deliveries`
  - `raw_matches` columns: `match_id, competition, start_date (DATE), venue, city, team1, team2, winner, result, method, overs (INT), gender`
  - `raw_deliveries` columns: `match_id, innings (1-based), batting_team, over (0-based), ball_seq (1-based within over, counts extras), batter, batter_id, bowler, bowler_id, runs_batter, runs_extras, runs_total, wides, noballs, is_wicket (BOOL), player_out, wicket_kind, target_runs, target_overs, is_super_over (BOOL)`
  - ids come from `info.registry.people[name]`

- [ ] **Step 1:** `git init`, create `.venv`, write `requirements.txt` (duckdb, dbt-duckdb, pandas, pyarrow, scikit-learn, lightgbm, streamlit, pytest), `pip install -r requirements.txt`.
- [ ] **Step 2: Write fixtures.** `match_ok.json`: minimal real-shaped Cricsheet match, 2 innings × 2 overs, containing one wide, one no-ball, one wicket, a `target` on innings 2, registry entries. `match_dls.json`: copy with `info.outcome.method = "D/L"`.
- [ ] **Step 3: Write failing tests**

```python
def test_flatten_counts():
    m, d = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert m["match_id"] == "m1" and m["competition"] == "ipl" and m["overs"] == 20
    assert len(d) == FIXTURE_DELIVERY_COUNT

def test_extras_flags():
    _, d = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert sum(r["wides"] > 0 for r in d) == 1
    assert sum(r["noballs"] > 0 for r in d) == 1

def test_registry_ids():
    _, d = flatten_match(load_fixture("match_ok.json"), "m1", "ipl")
    assert all(r["batter_id"] and r["bowler_id"] for r in d)

def test_method_captured():
    m, _ = flatten_match(load_fixture("match_dls.json"), "m2", "ipl")
    assert m["method"] == "D/L"
```

- [ ] **Step 4:** `pytest tests/test_ingest.py -v` → FAIL (import error).
- [ ] **Step 5:** Implement `flatten_match` and `load` in `ingest.py`; `__main__` runs `load(["ipl", "bbl", "t20i"], Path("data/cricket.duckdb"))`. Use `urllib.request` + `zipfile` (stdlib). Write tables via `duckdb` from pandas DataFrames.
- [ ] **Step 6:** `pytest tests/test_ingest.py -v` → PASS. Run `python3 ingest.py`; check `SELECT competition, count(*) FROM raw_matches GROUP BY 1` shows all three competitions.
- [ ] **Step 7:** Commit `feat: ingest Cricsheet T20 data into DuckDB`.

---

### Task 2: dbt models + data tests

**Files:**
- Create: everything under `dbt/`

**Interfaces:**
- Consumes: `raw_matches`, `raw_deliveries` (Task 1).
- Produces:
  - `stg_matches`: Global Constraints filters applied; adds `venue_clean = trim(split_part(venue, ',', 1))`, `season_year = year(start_date)`.
  - `stg_deliveries`: inner-joined to `stg_matches`, `is_super_over = false`, adds `is_legal = (wides = 0 and noballs = 0)`.
  - `chase_states`: one row per innings-2 delivery. Columns: `match_id, competition, start_date, season_year, venue_clean, batting_team, over, ball_seq, batter_id, batter, bowler_id, bowler, runs_total, is_wicket, is_legal, target, runs_needed, balls_remaining, wickets_in_hand, required_run_rate, chase_won (INT 0/1)`. All state columns are **after** the ball. `target = coalesce(target_runs, innings-1 sum(runs_total) + 1)`; `balls_remaining = 120 - running sum(is_legal)`; `wickets_in_hand = 10 - running count(is_wicket)`; `required_run_rate = runs_needed * 6.0 / nullif(balls_remaining, 0)`; window order `over, ball_seq`.

- [ ] **Step 1:** Write `dbt_project.yml` + `profiles.yml` (dbt-duckdb, `path: ../data/cricket.duckdb`), sources for the two raw tables.
- [ ] **Step 2:** Write tests first: `schema.yml` (`not_null` on keys; `accepted_values` competition in `ipl, bbl, t20i`; `chase_won` in 0/1) and the four singular tests:
  - `assert_target_matches_first_innings`: rows where `target_runs` present and ≠ innings-1 total + 1.
  - `assert_legal_balls_max_120`: any innings with sum(`is_legal`) > 120, or `balls_remaining < 0`.
  - `assert_runs_total_adds_up`: rows where `runs_total ≠ runs_batter + runs_extras`.
  - `assert_unique_ball_key`: `match_id, innings, over, ball_seq` with count > 1 in `stg_deliveries`.
- [ ] **Step 3:** `cd dbt && dbt build` → FAIL (models missing).
- [ ] **Step 4:** Write the three models.
- [ ] **Step 5:** `dbt build` → all models and tests PASS. If `assert_target_matches_first_innings` fails on a handful of real matches, inspect them; exclude in `stg_matches` with a named reason in the SQL, don't loosen the test.
- [ ] **Step 6:** Commit `feat: dbt staging and chase_states mart with data tests`.

---

### Task 3: Win-probability model + evaluation

**Files:**
- Create: `winprob.py`
- Test: `tests/test_winprob.py`

**Interfaces:**
- Consumes: `chase_states` (Task 2).
- Produces:
  - `FEATURES = ["runs_needed", "balls_remaining", "wickets_in_hand", "required_run_rate", "venue_clean", "competition", "season_year"]`; `BASELINE_FEATURES = ["runs_needed", "balls_remaining", "wickets_in_hand"]`
  - `load_states(db_path: Path) -> pd.DataFrame`
  - `time_split(df, cutoff="2023-01-01") -> tuple[pd.DataFrame, pd.DataFrame]`
  - `fit_baseline(train) -> sklearn Pipeline` (logistic regression on `BASELINE_FEATURES`)
  - `fit_model(train) -> lightgbm.LGBMClassifier` (`venue_clean`, `competition` as pandas `category`; unseen categories at predict → NaN category, LightGBM handles)
  - `predict(model, df) -> np.ndarray` — applies terminal override: `runs_needed <= 0` → 1.0; `runs_needed > 0 and (wickets_in_hand == 0 or balls_remaining == 0)` → 0.0
  - `start_state(df) -> pd.DataFrame` — one pre-first-ball row per match (`runs_needed = target`, `balls_remaining = 120`, `wickets_in_hand = 10`)
  - `evaluate(y, p, competition) -> dict` — `{"overall": {"brier", "log_loss", "auc"}, "by_competition": {...}}`
  - `calibration_table(y, p, bins=10) -> pd.DataFrame` (`bin, mean_pred, frac_won, n`)
  - Writes `app/data/predictions.parquet` (chase_states keys + `wp`, `wp_before`, `in_test`), `app/data/metrics.json` (`{"baseline": ..., "model": ...}`), `app/data/calibration.parquet` (`model_name, bin, mean_pred, frac_won, n`)
  - `wp_before` = previous ball's `wp`, first ball = `predict` on `start_state`

- [ ] **Step 1: Write failing tests** (synthetic DataFrames, no DuckDB):

```python
def test_time_split_no_leakage():
    train, test = time_split(synthetic_states())
    assert train.start_date.max() < pd.Timestamp("2023-01-01") <= test.start_date.min()
    assert set(train.match_id).isdisjoint(test.match_id)

def test_terminal_states_override():
    df = synthetic_states().head(3).assign(
        runs_needed=[0, 5, 5], wickets_in_hand=[3, 0, 3], balls_remaining=[10, 10, 0])
    assert list(predict(fitted_model(), df)) == [1.0, 0.0, 0.0]

def test_predict_unseen_venue():
    df = synthetic_states().head(1).assign(venue_clean="Brand New Oval")
    p = predict(fitted_model(), df)
    assert 0.0 <= p[0] <= 1.0

def test_calibration_table_bins():
    t = calibration_table(np.array([0, 1] * 50), np.linspace(0, 1, 100), bins=10)
    assert len(t) == 10 and t.n.sum() == 100

def test_model_beats_coinflip():
    train, test = time_split(synthetic_states())
    p = predict(fit_model(train), test)
    assert evaluate(test.chase_won, p, test.competition)["overall"]["brier"] < 0.25
```

`synthetic_states()` lives in the test file: ~200 matches across 2020–2024, `chase_won` drawn from a logistic function of runs_needed/balls/wickets so the signal is learnable.
- [ ] **Step 2:** `pytest tests/test_winprob.py -v` → FAIL.
- [ ] **Step 3:** Implement `winprob.py`; `__main__` loads real data, fits both models on train, evaluates both on test, writes the three outputs.
- [ ] **Step 4:** `pytest tests/test_winprob.py -v` → PASS. Run `python3 winprob.py`; confirm `metrics.json` model Brier < baseline Brier. If not, report it honestly rather than tuning on the test set — tune on a validation slice of train (last train season) only.
- [ ] **Step 5:** Commit `feat: chase win-probability model with baseline and calibration`.

---

### Task 4: Player value (WPA)

**Files:**
- Create: `player_value.py`
- Test: `tests/test_player_value.py`

**Interfaces:**
- Consumes: `app/data/predictions.parquet` (Task 3), `chase_states` for raw stats.
- Produces:
  - `ball_deltas(pred: pd.DataFrame) -> pd.DataFrame` — adds `wpa = wp - wp_before`
  - `player_value(deltas: pd.DataFrame, min_balls=120) -> pd.DataFrame` — columns `player_id, player, role ("bat"|"bowl"), balls, wpa_total, wpa_per_100, raw_stat, raw_rank, wpa_rank, rank_gap`. Batter credited `+wpa`, bowler `-wpa`. Raw stat: batter strike rate, bowler economy (lower is better). `balls` counts legal balls faced/bowled. `rank_gap = raw_rank - wpa_rank` (positive = underrated).
  - Writes `app/data/player_value.parquet`

- [ ] **Step 1: Write failing tests**

```python
def test_credit_signs():
    d = ball_deltas(pd.DataFrame({..., "wp_before": [0.5], "wp": [0.6]}))
    pv = player_value(d, min_balls=0)
    assert pv.query("role == 'bat'").wpa_total.iloc[0] == pytest.approx(0.1)
    assert pv.query("role == 'bowl'").wpa_total.iloc[0] == pytest.approx(-0.1)

def test_player_value_keys_on_id():
    # two different ids sharing one name stay separate
    pv = player_value(two_players_same_name(), min_balls=0)
    assert pv.query("role == 'bat'").player_id.nunique() == 2

def test_min_balls_filter():
    assert player_value(small_sample(), min_balls=10_000).empty
```

- [ ] **Step 2:** `pytest tests/test_player_value.py -v` → FAIL.
- [ ] **Step 3:** Implement; `__main__` writes the Parquet.
- [ ] **Step 4:** `pytest tests/test_player_value.py -v` → PASS; run `python3 player_value.py`, eyeball top 10 batters/bowlers for sanity (known finishers/death bowlers should appear).
- [ ] **Step 5:** Commit `feat: chase-only player win-probability-added leaderboard`.

---

### Task 5: Streamlit dashboard

**Files:**
- Create: `app/streamlit_app.py`

**Interfaces:**
- Consumes: `app/data/predictions.parquet`, `metrics.json`, `calibration.parquet`, `player_value.parquet`. Reads Parquet only — no DuckDB, no dbt.

Three pages via `st.navigation` or `st.tabs`:
1. **Match explorer:** filters competition → season → match (default: test-set matches, `in_test`). Altair line of `wp` vs ball index, y from 0–1, with point markers + tooltip on wickets and on the 3 largest |wpa| balls.
2. **Model:** metrics table model vs baseline (overall + per competition); calibration chart (mean_pred vs frac_won, diagonal reference line) for both models.
3. **Players:** leaderboard with role toggle, sortable; "Underrated" view sorted by `rank_gap`. Heading includes "Chase-only" label.

- [ ] **Step 1:** Build the app.
- [ ] **Step 2:** `streamlit run app/streamlit_app.py`; verify each page renders, a match with a late collapse shows a visible swing, unseen-venue match loads.
- [ ] **Step 3:** Check `app/data/` size (`du -sh app/data`) < 50 MB; if larger, drop non-test-season predictions from `predictions.parquet`.
- [ ] **Step 4:** Commit `feat: Streamlit dashboard`.

---

### Task 6: Memo, README, deploy

**Files:**
- Create: `MEMO.md`, `README.md`

- [ ] **Step 1: MEMO.md** — one page, non-technical reader. 3–4 findings, each = claim + number + one chart/screenshot + "so what". Candidates: which phase (powerplay/middle/death) moves win probability most; how much venue matters; most underrated players (chase-only label). State the model's limits plainly.
- [ ] **Step 2: README.md** — top: one-line pitch, results chart (calibration or a match curve), model vs baseline table, live app link. Then: data source + Cricsheet attribution, pipeline diagram (text), how to reproduce (`pip install`, `python3 ingest.py`, `dbt build`, `python3 winprob.py`, `python3 player_value.py`, `streamlit run`), limits.
- [ ] **Step 3:** Push to public GitHub repo `Devarsh-04/cricket-analytics` (Devarsh creates repo / confirms push). Deploy on Streamlit Community Cloud pointing at `app/streamlit_app.py`. Put live URL in README.
- [ ] **Step 4:** Fresh-clone check: clone repo in scratch dir, run `pytest` and `streamlit run` from the clone — both work.
- [ ] **Step 5:** Commit `docs: memo and README`.

---

### Task 7 (STRETCH — only if Tasks 1–6 done with ≥2 days left): First-innings model

**Files:**
- Modify: `dbt/models/marts/` (add `first_innings_states.sql`), `winprob.py`, `player_value.py`, `app/streamlit_app.py`, `MEMO.md`, `README.md`
- Test: extend `tests/test_winprob.py`

**Interfaces:**
- `first_innings_states`: one row per innings-1 delivery; features `runs_so_far, balls_remaining, wickets_in_hand, current_run_rate, venue_clean, competition, season_year`; label `batting_first_won`. Same exclusions.
- `fit_model` / `predict` reused with a `features` argument; terminal override not applicable (innings 1 has no target).
- Predictions converted to the chasing team's perspective (`1 - p`) and concatenated so one match curve spans both innings.

- [ ] **Step 1:** Add mart + dbt test (`balls_remaining >= 0`), `dbt build` PASS.
- [ ] **Step 2:** Failing test `test_first_innings_split_no_leakage` (same as Task 3's, on first-innings states) → FAIL → implement → PASS.
- [ ] **Step 3:** Evaluate vs baseline (logistic on `runs_so_far, balls_remaining, wickets_in_hand`); add to `metrics.json` under `"first_innings"`.
- [ ] **Step 4:** Player value over both innings; remove "Chase-only" labels in app + memo.
- [ ] **Step 5:** Commit `feat: first-innings win probability (stretch)`.
