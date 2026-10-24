# What decides a T20 chase — findings memo

**Data:** 2,840 completed T20 chases (IPL, BBL, men's T20Is between ICC full members), ball by ball, from Cricsheet.
**Method:** a win-probability model trained on matches before 2023 and tested on 83,306 balls from matches since then. It beats a simple baseline in every competition (Brier score 0.140 vs 0.147; lower is better).

---

### 1. Death overs swing a chase the most per ball, but the middle overs decide it

| Phase | Avg. win-probability swing per ball | Share of all swing |
|---|---|---|
| Powerplay (overs 1–6) | 1.4 pts | 29% |
| Middle (overs 7–15) | 1.4 pts | **41%** |
| Death (overs 16–20) | **2.5 pts** | 30% |

A ball in the last five overs moves the result about 1.7× more than an earlier ball. But the middle overs are the longest phase, so most of a chase is won or lost there. A wicket costs the chasing team 7.6 percentage points on average.

**So what:** teams pay a premium for finishers, yet the middle overs hold the most total value. A batter who keeps the required rate under control through overs 7–15 is worth more than their strike rate suggests (see finding 3).

### 2. IPL chasing changed in 2023, and a model trained on history underrates it

| IPL | Avg. target | Targets of 200+ chased successfully |
|---|---|---|
| Before 2023 | 164 | 15% |
| 2023 onward | **191** | **32%** |

At the start of a 200+ chase, the model, which learned only from pre-2023 cricket, gives the chasing team 14%. Since 2023 they have won 32% of the time. The model's IPL predictions average 39% against a real chase win rate of 51%. BBL shows a smaller gap and T20Is almost none. The timing matches IPL's Impact Player rule (2023), which adds a specialist batter to every innings.

**So what:** historical par scores no longer hold in the IPL. Any model or captain using pre-2023 benchmarks will undervalue chasing teams. I left this gap visible rather than tuning it away on the test data. The fix is to retrain on recent seasons, or to weight them more heavily.

### 3. The most underrated players are anchors who protect wickets and death bowlers who take them

These are players who rank far higher by win probability added per ball than by their raw strike rate or economy (minimum 500 balls, chases only):

- **Batters:** Mohammad Rizwan and Eoin Morgan. Their strike rates are modest (122, 128), but they rank in the top 50–80 for impact on winning chases.
- **Bowlers:** Josh Hazlewood, Mitchell McClenaghan and Umar Gul. They are expensive (economy 8.0–8.5), but their wickets come at the moments that end chases.

**So what:** strike rate and economy miss context. Win probability added credits what actually moved the result.

### 4. Venue doesn't help once you know the target

I tested adding venue and season to the model on a 2022 validation slice, before touching the test set. Both made it worse (Brier 0.123 and 0.127 vs 0.114). The target already reflects how batting-friendly the ground and era are. The final model uses only the match situation: runs needed, balls left, wickets in hand and required rate.

---

**Limits:** the model covers the chase (second innings) only, so player value only credits chasing batters and defending bowlers. Rain-affected (DLS), tied and no-result matches are excluded, as are two matches with umpire-miscounted overs.
