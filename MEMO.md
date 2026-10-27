# What decides a T20 chase — findings memo

**Data:** 2,800 completed full-length T20 chases (IPL, BBL, men's T20Is between ICC full members), ball by ball, from Cricsheet.
**Method:** a win-probability model trained on matches before 2025 and tested on the 358 matches (40,387 balls) from 2025 and 2026. It beats a simple baseline in every competition (Brier score 0.129 vs 0.139; lower is better). Every number below comes from the test matches only, which the model never saw.

---

### 1. Death overs swing a chase the most per ball, but the middle overs decide it

| Phase | Avg. win-probability swing per ball | Share of all swing |
|---|---|---|
| Powerplay (overs 1–6) | 1.4 pts | 31% |
| Middle (overs 7–15) | 1.3 pts | **42%** |
| Death (overs 16–20) | **2.2 pts** | 26% |

A ball in the last five overs moves the result about 1.6× more than an earlier ball. But the middle overs are the longest phase, so most of a chase is won or lost there. A wicket costs the chasing team 6.9 percentage points on average.

**So what:** teams pay a premium for finishers, yet the middle overs hold the most total value.

### 2. IPL chasing changed in 2023, and models trained on history still underrate it

| IPL | Avg. target | Targets of 200+ chased successfully |
|---|---|---|
| Before 2023 | 164 | 16% (15 of 97) |
| 2023 onward | **191** | **32%** (40 of 124) |

Even after retraining on everything up to the end of 2024, the model still trails reality on 2025–26 matches. At the start of a 200+ chase it gives the chasing side 17%; they won 30% of the time (118 chases, all competitions). Across all test balls, IPL predictions average 41% while chasing teams actually won 56%. BBL shows a similar gap (51% vs 63%), T20Is a smaller one (43% vs 47%). The IPL jump lines up with the Impact Player rule (2023), which adds a specialist batter to every innings, and scoring has kept rising since.

**So what:** historical par scores no longer hold. A model or captain using older benchmarks will undervalue chasing teams, and two seasons of new data weren't enough to catch up. I left this gap visible rather than tuning it away on the test data. The next steps are weighting recent seasons more heavily, and adding competition as a feature: on the 2024 validation slice it improved the Brier score slightly (0.132 vs 0.134).

### 3. Some players matter far more to winning chases than their raw stats suggest

These players have the biggest gaps between their rank on win probability added per ball and their rank on strike rate or economy (minimum 500 balls, chases only). Names are as they appear in Cricsheet.

- **Batters:** Mushfiqur Rahim, SC Ganguly and SR Tendulkar. Their strike rates are modest (106–119), but they rank highly for impact on chases. These are anchors who keep wickets in hand.
- **Bowlers:** MJ Henry, SH Johnson and MJ McClenaghan. They are expensive (economy 8.5–9.7), but they still rank in the top 75 for impact, because their wickets end chases.

**So what:** strike rate and economy miss context. Win probability added credits what actually moved the result. The full sortable list is in the dashboard.

### 4. Venue and season didn't help this model

I tested adding venue and season on a 2024 validation slice, before touching the test set. Both made the model worse (Brier 0.152 and 0.166 vs 0.134). A likely reason is that the target already reflects how batting-friendly the ground and era are. Venue also has hundreds of grounds with few matches each, so the model overfits to it. A numeric "venue average score" feature is the natural next test. The final model uses only the match situation: runs needed, balls left, wickets in hand and required rate.

---

**Limits:** the model covers the chase (second innings) only, so player value only credits chasing batters and defending bowlers. Excluded: rain-affected (DLS), tied and no-result matches; chases shortened before they began; and two matches with umpire-miscounted overs. Penalty runs awarded during a chase are ignored (rare). Run-outs of the non-striker are credited to the striker.
