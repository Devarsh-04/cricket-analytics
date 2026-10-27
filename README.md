# T20 Chase Win Probability

Ball-by-ball win probability for T20 chases (IPL, BBL and men's T20Is) built from 1.27M deliveries. It is a tested SQL pipeline feeding a calibrated model, with player value built on top.

**Live app:** _coming soon_ · **Findings:** [MEMO.md](MEMO.md)

## Results

The model was trained on matches before 2023 and tested on 82,381 balls from the 723 matches since 2023.

| | Brier ↓ | Log loss ↓ | AUC ↑ |
|---|---|---|---|
| Baseline (logistic regression) | 0.146 | 0.455 | 0.886 |
| **Model (LightGBM, monotone)** | **0.139** | **0.425** | **0.898** |

The model beats the baseline in every competition: IPL 0.153 vs 0.162, BBL 0.145 vs 0.151, T20I 0.123 vs 0.128.

Headline findings (details in the [memo](MEMO.md)):
- Since 2023, IPL teams chase 200+ successfully 32% of the time, up from 16%. A model trained on pre-2023 data underrates them, which matches the timing of the Impact Player rule.
- Death-over balls swing a chase 1.7× more than earlier balls, but the middle overs carry the largest share of total swing (41%).
- Venue and season made the model *worse* on validation data. This is likely because the target already reflects them, and because venue is sparse enough to overfit.

## How it works

```
Cricsheet JSON ──ingest.py──▶ DuckDB raw tables
                                 │
                                dbt: stg_matches → stg_deliveries → chase_states
                                 │   (17 data tests: unique balls, targets reconcile,
                                 │    full 20-over chases, runs add up, …)
                                 ▼
                          winprob.py  ── baseline + LightGBM, time split, calibration
                                 │
                          player_value.py  ── win probability added per batter / bowler
                                 ▼
                     app/data/*.parquet ──▶ Streamlit dashboard
```

- **Scope:** T20 only. T20Is are limited to matches between ICC full members. DLS, tied, no-result and pre-shortened chases are excluded.
- **No leakage:** the train/test split is by date, and every feature describes the match state *after* that ball using only earlier balls.
- **Model:** a LightGBM model on runs needed, balls left, wickets in hand and required rate. Monotone constraints keep it consistent with cricket logic (more balls left can never lower win probability). Terminal states, such as the target reached or the side all out, are fixed at exactly 1 or 0.
- **Player value:** each ball's change in win probability is credited to the batter (+) and the bowler (−). This is chase-only.

## Run it yourself

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 ingest.py                 # downloads Cricsheet data (~22 MB) into data/
cd dbt && dbt build && cd ..      # builds and tests the models
python3 winprob.py                # trains, evaluates, writes app/data/
python3 player_value.py
python3 export_app.py             # writes the app's match, ball and findings files
streamlit run app/streamlit_app.py
pytest                            # 22 tests
```

## Limits

- The model covers the second innings only. A first-innings model is a planned extension.
- The model is calibrated on pre-2023 cricket and underestimates IPL chasers since 2023. This is reported rather than tuned away (see the memo).
- Economy rates include byes and leg-byes. Run-outs of the non-striker are credited to the striker.

## Data

Match data comes from [Cricsheet](https://cricsheet.org) and is licensed under the [Open Data Commons Attribution License](https://opendatacommons.org/licenses/by/1-0/).
