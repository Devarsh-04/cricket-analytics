# What decides a T20 chase — findings memo

**Data:** 2,800 completed full-length T20 chases (IPL, BBL, men's T20Is between ICC full members), ball by ball, from Cricsheet.
**Method:** a win-probability model trained on matches before 2023 and tested on the 723 matches (82,381 balls) since then. It beats a simple baseline in every competition (Brier score 0.139 vs 0.146; lower is better). Every number below comes from the test matches only, which the model never saw.

---

### 1. Death overs swing a chase the most per ball, but the middle overs decide it

| Phase | Avg. win-probability swing per ball | Share of all swing |
|---|---|---|
| Powerplay (overs 1–6) | 1.5 pts | 30% |
| Middle (overs 7–15) | 1.4 pts | **41%** |
| Death (overs 16–20) | **2.4 pts** | 29% |

A ball in the last five overs moves the result about 1.7× more than an earlier ball. But the middle overs are the longest phase, so most of a chase is won or lost there. A wicket costs the chasing team 6.9 percentage points on average.

**So what:** teams pay a premium for finishers, yet the middle overs hold the most total value.

### 2. IPL chasing changed in 2023, and a model trained on history underrates it

| IPL | Avg. target | Targets of 200+ chased successfully |
|---|---|---|
| Before 2023 | 164 | 16% (15 of 97) |
| 2023 onward | **191** | **32%** (40 of 124) |

At the start of a 200+ chase, the model, which learned only from pre-2023 cricket, gives the chasing team 14%. Since 2023 they have won 32% of the time. Across all test balls, the model's IPL predictions average 39% while chasing teams actually won 51%. BBL shows a smaller gap (54% vs 62%) and T20Is almost none (44% vs 47%). The timing matches IPL's Impact Player rule (2023), which adds a specialist batter to every innings.

**So what:** historical par scores no longer hold in the IPL. Any model or captain using pre-2023 benchmarks will undervalue chasing teams. I left this gap visible rather than tuning it away on the test data. The fix is to retrain on recent seasons, or to weight them more heavily.

### 3. Some players matter far more to winning chases than their raw stats suggest

These players have the biggest gaps between their rank on win probability added per ball and their rank on strike rate or economy (minimum 500 balls, chases only). Names are as they appear in Cricsheet.

- **Batters:** Mushfiqur Rahim, SC Ganguly and Mohammad Rizwan. Their strike rates are modest (106–122), but they rank highly for impact on chases. These are anchors who keep wickets in hand.
- **Bowlers:** MJ Henry, SH Johnson and MJ McClenaghan. They are expensive (economy 8.5–9.7), but they still rank in the top 65 for impact, because their wickets end chases.

**So what:** strike rate and economy miss context. Win probability added credits what actually moved the result. The full sortable list is in the dashboard.

### 4. Venue and season didn't help this model

I tested adding venue and season on a 2022 validation slice, before touching the test set. Both made the model worse (Brier 0.122 and 0.126 vs 0.113). A likely reason is that the target already reflects how batting-friendly the ground and era are. Venue also has hundreds of grounds with few matches each, so the model overfits to it. A numeric "venue average score" feature is the natural next test. The final model uses only the match situation: runs needed, balls left, wickets in hand and required rate.

---

**Limits:** the model covers the chase (second innings) only, so player value only credits chasing batters and defending bowlers. Excluded: rain-affected (DLS), tied and no-result matches; chases shortened before they began; and two matches with umpire-miscounted overs. Penalty runs awarded during a chase are ignored (rare). Run-outs of the non-striker are credited to the striker.
