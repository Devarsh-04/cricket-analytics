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
