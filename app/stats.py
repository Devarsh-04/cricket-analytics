import pandas as pd

NOT_BOWLER_WICKETS = {"run out", "retired hurt", "retired out", "retired not out", "obstructing the field"}


def _innings(d: pd.DataFrame, innings: int) -> pd.DataFrame:
    return d[d.innings == innings].reset_index(drop=True)


def _overs(legal_balls: int) -> str:
    return f"{legal_balls // 6}.{legal_balls % 6}"


def _dismissal(row) -> str:
    if row is None:
        return "not out"
    if row.wicket_kind == "bowled":
        return f"b {row.bowler}"
    if row.wicket_kind in NOT_BOWLER_WICKETS:
        return row.wicket_kind
    return f"{row.wicket_kind} b {row.bowler}"


def batting_card(d: pd.DataFrame, innings: int) -> pd.DataFrame:
    inn = _innings(d, innings)
    order = pd.concat([inn.batter, inn.player_out.dropna()]).astype(str)
    order = order.sort_index(kind="stable").drop_duplicates()
    outs = {r.player_out: r for r in inn[inn.player_out.notna()].itertuples()}
    rows = []
    for name in order:
        faced = inn[(inn.batter == name) & (inn.wides == 0)]
        runs, balls = int(faced.runs_batter.sum()), len(faced)
        rows.append({
            "batter": name, "dismissal": _dismissal(outs.get(name)), "runs": runs, "balls": balls,
            "fours": int((faced.runs_batter == 4).sum()), "sixes": int((faced.runs_batter == 6).sum()),
            "strike_rate": runs / balls * 100 if balls else 0.0,
        })
    return pd.DataFrame(rows, columns=["batter", "dismissal", "runs", "balls", "fours", "sixes", "strike_rate"])


def bowling_card(d: pd.DataFrame, innings: int) -> pd.DataFrame:
    inn = _innings(d, innings).astype({"bowler": str})
    inn = inn.assign(
        conceded=inn.runs_batter + inn.wides + inn.noballs,
        credited=inn.is_wicket & ~inn.wicket_kind.isin(NOT_BOWLER_WICKETS),
    )
    g = inn.groupby("bowler", sort=False).agg(
        legal=("is_legal", "sum"), runs=("conceded", "sum"), wickets=("credited", "sum")).reset_index()
    return pd.DataFrame({
        "bowler": g.bowler,
        "overs": g.legal.map(_overs),
        "runs": g.runs.astype(int),
        "wickets": g.wickets.astype(int),
        "economy": g.runs / g.legal.where(g.legal > 0) * 6,
    })


def fall_of_wickets(d: pd.DataFrame, innings: int) -> pd.DataFrame:
    inn = _innings(d, innings)
    inn = inn.assign(
        score=inn.runs_total.cumsum(),
        ball_in_over=inn.groupby("over").is_legal.cumsum(),
    )
    w = inn[inn.is_wicket]
    return pd.DataFrame({
        "wicket": range(1, len(w) + 1),
        "score": w.score.astype(int).tolist(),
        "batter": w.player_out.astype(str).tolist(),
        "over": [f"{o}.{b}" for o, b in zip(w.over, w.ball_in_over)],
    })


def runs_per_over(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(["innings", "over"]).agg(
        team=("batting_team", "first"), runs=("runs_total", "sum"), wickets=("is_wicket", "sum")).reset_index()
    return g.assign(over=g.over + 1, team=g.team.astype(str), wickets=g.wickets.astype(int))[
        ["innings", "team", "over", "runs", "wickets"]]


def _over_text(o: pd.DataFrame) -> str:
    bowler = o.bowler.astype(str).value_counts().index[0]
    runs = int(o.runs_total.sum())
    out = o[o.is_wicket].player_out.astype(str).tolist()
    if out:
        noun = "wicket" if len(out) == 1 else "wickets"
        return f"{bowler} took {len(out)} {noun} ({', '.join(out)}) for {runs} runs"
    by_batter = o.groupby(o.batter.astype(str)).runs_batter.sum()
    return f"{by_batter.idxmax()} scored {int(by_batter.max())} of the {runs} runs off {bowler}"


def turning_points(d: pd.DataFrame, n: int = 3) -> list[dict]:
    chase = _innings(d, 2)
    if chase.empty or chase.wp.isna().all():
        return []
    overs = [
        {"over": int(over) + 1, "wp_from": float(o.wp_before.iloc[0]), "wp_to": float(o.wp.iloc[-1]), "text": _over_text(o)}
        for over, o in chase.groupby("over")
    ]
    top = sorted(overs, key=lambda t: abs(t["wp_to"] - t["wp_from"]), reverse=True)[:n]
    return sorted(top, key=lambda t: t["over"])


def match_impact(d: pd.DataFrame, top: int = 3) -> pd.DataFrame:
    chase = _innings(d, 2)
    chase = chase[chase.wp.notna()]
    delta = (chase.wp - chase.wp_before) * 100
    bat = delta.groupby(chase.batter.astype(str)).sum()
    bowl = -delta.groupby(chase.bowler.astype(str)).sum()
    out = pd.concat([
        pd.DataFrame({"player": bat.index, "role": "bat", "points": bat.values}),
        pd.DataFrame({"player": bowl.index, "role": "bowl", "points": bowl.values}),
    ], ignore_index=True)
    return out.sort_values("points", ascending=False, ignore_index=True).head(top)


PHASES = {"Powerplay": range(0, 6), "Middle": range(6, 15), "Death": range(15, 20)}
PHASE_WORDS = {"Powerplay": "the powerplay", "Middle": "the middle overs", "Death": "the death overs"}
FRACTIONS = {0.1: "a tenth", 0.2: "a fifth", 0.25: "a quarter", 1 / 3: "a third", 0.5: "half"}
RECORD_KEYS = {"W": "won", "L": "lost", "T": "tied", "NR": "nr"}


def team_matches(m: pd.DataFrame, team: str) -> pd.DataFrame:
    tm = m[(m.team1 == team) | (m.team2 == team)].copy()
    tm["opponent"] = tm.team2.where(tm.team1 == team, tm.team1)
    tm["result"] = "L"
    tm.loc[tm.winner == team, "result"] = "W"
    tm.loc[tm.outcome == "tie", "result"] = "T"
    tm.loc[tm.outcome == "no result", "result"] = "NR"
    return tm.sort_values("start_date")


def record(tm: pd.DataFrame) -> dict:
    counts = tm.result.value_counts()
    return {"played": len(tm)} | {key: int(counts.get(r, 0)) for r, key in RECORD_KEYS.items()}


def team_summary(m: pd.DataFrame, team: str) -> dict:
    tm = team_matches(m, team)
    seasons = sorted(tm.season.unique())[-2:]
    return {
        "overall": record(tm),
        "batting_first": record(tm[tm.bat_first == team]),
        "chasing": record(tm[tm.bat_first.notna() & (tm.bat_first != team)]),
        "last_two_seasons": record(tm[tm.season.isin(seasons)]),
        "seasons": seasons,
    }


def wins_by_season(m: pd.DataFrame, team: str) -> pd.DataFrame:
    tm = team_matches(m, team)
    return (tm.assign(won=tm.result == "W").groupby("season")
            .agg(played=("match_id", "size"), won=("won", "sum")).reset_index())


def head_to_head(m: pd.DataFrame, team: str) -> pd.DataFrame:
    tm = team_matches(m, team)
    rows = [{"opponent": opp} | record(g) for opp, g in tm.groupby("opponent")]
    return (pd.DataFrame(rows, columns=["opponent", "played", "won", "lost", "tied", "nr"])
            .sort_values(["played", "won"], ascending=False, ignore_index=True))


def _phase_stats(balls: pd.DataFrame) -> tuple[float, float]:
    legal = balls.is_legal.sum()
    innings = balls[["match_id", "innings"]].drop_duplicates().shape[0]
    if not legal:
        return float("nan"), float("nan")
    return balls.runs_total.sum() / legal * 6, balls.is_wicket.sum() / innings


def phase_table(d: pd.DataFrame, m: pd.DataFrame, team: str, since: str = "2023-01-01") -> pd.DataFrame:
    recent = d[d.match_id.isin(m.match_id[m.start_date >= pd.Timestamp(since)])]
    mine = recent.batting_team == team
    columns = ["phase", "team_run_rate", "rest_run_rate", "team_wkts", "rest_wkts"]
    if not mine.any():
        return pd.DataFrame(columns=columns)
    rows = []
    for phase, overs in PHASES.items():
        in_phase = recent.over.isin(overs)
        team_rr, team_w = _phase_stats(recent[in_phase & mine])
        rest_rr, rest_w = _phase_stats(recent[in_phase & ~mine])
        rows.append([phase, team_rr, rest_rr, team_w, rest_w])
    return pd.DataFrame(rows, columns=columns)


def _fraction(x: float) -> str:
    nearest = min(FRACTIONS, key=lambda f: abs(f - x))
    if abs(nearest - x) <= 0.02:
        return FRACTIONS[nearest]
    if x > 0.6:
        return f"{x:.0%}"
    return f"about {FRACTIONS[nearest]}"


def phase_note(pt: pd.DataFrame) -> str:
    edge = pt.team_run_rate / pt.rest_run_rate - 1
    row = pt.loc[edge.abs().idxmax()]
    diff = row.team_run_rate - row.rest_run_rate
    lead = "Best" if diff > 0 else "Weakest"
    pace = "faster" if diff > 0 else "slower"
    ratio = row.team_wkts / row.rest_wkts - 1
    if abs(ratio) < 0.05:
        wickets = "losing about as many wickets"
    else:
        wickets = f"losing {_fraction(abs(ratio))} {'fewer' if ratio < 0 else 'more'} wickets"
    return (f"{lead} in {PHASE_WORDS[row.phase]}: {abs(diff):.1f} runs an over {pace} than other teams, "
            f"{wickets}.")


def top_players(d: pd.DataFrame, team: str, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    batting = d[d.batting_team == team]
    bowling = d[d.match_id.isin(batting.match_id.unique()) & (d.batting_team != team)]
    faced = batting[batting.wides == 0].astype({"batter": str})
    bat = faced.groupby("batter").agg(runs=("runs_batter", "sum"), balls=("runs_batter", "size")).reset_index()
    bat["strike_rate"] = bat.runs / bat.balls * 100
    bowling = bowling.astype({"bowler": str}).assign(
        conceded=bowling.runs_batter + bowling.wides + bowling.noballs,
        credited=bowling.is_wicket & ~bowling.wicket_kind.isin(NOT_BOWLER_WICKETS),
    )
    bowl = bowling.groupby("bowler").agg(
        wickets=("credited", "sum"), balls=("is_legal", "sum"), runs=("conceded", "sum")).reset_index()
    bowl["economy"] = bowl.runs / bowl.balls.where(bowl.balls > 0) * 6
    bowl = bowl.astype({"wickets": int, "balls": int}).drop(columns="runs")
    return (bat.sort_values("runs", ascending=False, ignore_index=True).head(n),
            bowl.sort_values(["wickets", "economy"], ascending=[False, True], ignore_index=True).head(n))


def most_played_ground(m: pd.DataFrame, team: str) -> tuple[str, dict]:
    tm = team_matches(m, team)
    venue = tm.venue.value_counts().index[0]
    return venue, record(tm[tm.venue == venue])
