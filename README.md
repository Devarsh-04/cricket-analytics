# T20 Chase Win Probability

Ball-by-ball win probability for T20 chases (IPL, BBL and men's T20Is) built from 1.27M deliveries. It is a tested SQL pipeline feeding a calibrated model, with player value built on top.

**Live app:** _coming soon_ · **Findings:** [MEMO.md](MEMO.md)

## Results

The model was trained on matches before 2025 and tested on 40,387 balls from the 358 matches in 2025 and 2026.

| | Brier ↓ | Log loss ↓ | AUC ↑ |
|---|---|---|---|
| Baseline (logistic regression) | 0.139 | 0.430 | 0.909 |
| **Model (LightGBM, monotone)** | **0.129** | **0.393** | **0.923** |

The model beats the baseline in every competition: IPL 0.148 vs 0.160, BBL 0.149 vs 0.156, T20I 0.104 vs 0.112.

Headline findings (details in the [memo](MEMO.md)):
- Since 2023, IPL teams chase 200+ successfully 32% of the time, up from 16%. Even retrained through 2024, the model underrates 2025–26 chasers (IPL: 41% predicted vs 56% won), in line with the Impact Player rule and still-rising scores.
- Death-over balls swing a chase 1.6× more than earlier balls, but the middle overs carry the largest share of total swing (42%).
- Venue and season made the model *worse* on validation data. This is likely because the target already reflects them, and because venue is sparse enough to overfit.

## How it works

```
Cricsheet JSON ──ingest.py──▶ DuckDB raw tables
                                 │
                                dbt: stg_all_matches → stg_matches → stg_deliveries → chase_states
                                 │   (22 data tests: unique balls, targets reconcile, full
                                 │    20-over chases, runs add up, no stale team names, …)
                                 ▼
                          winprob.py  ── baseline + LightGBM, time split, calibration
                                 │
                          player_value.py  ── win probability added per batter / bowler
                                 │
                          export_app.py  ── matches, both innings ball by ball, findings
                                 ▼
                     app/data/ ──▶ Streamlit app (Home · Matches · Teams · About)
```

- **Cleaning:** renamed teams (e.g. Royal Challengers Bangalore → Bengaluru) and grounds are merged via dbt seeds, so records don't split.
- **Scope:** T20 only. T20Is are limited to matches between ICC full members. DLS, tied, no-result and pre-shortened chases are excluded from the model, but team records count every match (won–lost–tied–no result).
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
pytest                            # 53 tests
```

## Limits

- The model covers the second innings only. A first-innings model is a planned extension.
- The model learns from cricket before 2025 and still underestimates 2025–26 chasers, most in the IPL and BBL. This is reported rather than tuned away (see the memo).
- Economy rates include byes and leg-byes. Run-outs of the non-striker are credited to the striker.

## Data

Match data comes from [Cricsheet](https://cricsheet.org) and is licensed under the [Open Data Commons Attribution License](https://opendatacommons.org/licenses/by/1-0/).
