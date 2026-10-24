import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["runs_needed", "balls_remaining", "wickets_in_hand", "required_run_rate"]
MONOTONE = [-1, 1, 1, -1]
ABLATION_FEATURES = {
    "+ competition": FEATURES + ["competition"],
    "+ venue": FEATURES + ["venue_clean"],
    "+ venue, season": FEATURES + ["venue_clean", "season_year"],
}
BASELINE_FEATURES = ["runs_needed", "balls_remaining", "wickets_in_hand"]
CATEGORICAL = ["venue_clean", "competition"]
CUTOFF = "2023-01-01"
OUT_DIR = Path("app/data")


def load_states(db_path: Path) -> pd.DataFrame:
    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.sql("SELECT * FROM chase_states ORDER BY match_id, over, ball_seq").df()
    return df.assign(start_date=pd.to_datetime(df.start_date))


def time_split(df: pd.DataFrame, cutoff: str = CUTOFF) -> tuple[pd.DataFrame, pd.DataFrame]:
    is_test = df.start_date >= pd.Timestamp(cutoff)
    return df[~is_test], df[is_test]


def _matrix(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    X = df[columns].copy()
    for c in CATEGORICAL:
        if c in X:
            X[c] = X[c].astype("category")
    return X


def fit_baseline(train: pd.DataFrame):
    model = make_pipeline(StandardScaler(), LogisticRegression())
    return model.fit(_matrix(train, BASELINE_FEATURES), train.chase_won)


def fit_model(train: pd.DataFrame, features: list[str] = FEATURES) -> LGBMClassifier:
    monotone = [MONOTONE[FEATURES.index(f)] if f in FEATURES else 0 for f in features]
    model = LGBMClassifier(
        n_estimators=300, learning_rate=0.05, min_child_samples=500,
        monotone_constraints=monotone, verbose=-1,
    )
    return model.fit(_matrix(train, features), train.chase_won)


def ablation(train: pd.DataFrame, cutoff: str = "2022-01-01") -> dict:
    fit_part, valid = time_split(train, cutoff)
    variants = {"baseline": fit_baseline(fit_part), "model": fit_model(fit_part)}
    variants |= {name: fit_model(fit_part, f) for name, f in ABLATION_FEATURES.items()}
    return {name: _scores(valid.chase_won, predict(m, valid)) for name, m in variants.items()}


def predict(model, df: pd.DataFrame) -> np.ndarray:
    p = model.predict_proba(_matrix(df, list(model.feature_names_in_)))[:, 1]
    lost = (df.runs_needed > 0) & ((df.wickets_in_hand == 0) | (df.balls_remaining == 0))
    p = np.where(df.runs_needed <= 0, 1.0, p)
    return np.where(lost, 0.0, p)


def start_state(df: pd.DataFrame) -> pd.DataFrame:
    s = df.groupby("match_id", sort=False).head(1).copy()
    return s.assign(
        runs_needed=s.target,
        balls_remaining=120,
        wickets_in_hand=10,
        required_run_rate=s.target * 6 / 120,
    )


def _scores(y, p) -> dict:
    return {
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "auc": float(roc_auc_score(y, p)) if len(set(y)) > 1 else None,
        "n": int(len(y)),
    }


def evaluate(y, p, competition) -> dict:
    y, p, competition = np.asarray(y), np.asarray(p), np.asarray(competition)
    return {
        "overall": _scores(y, p),
        "by_competition": {c: _scores(y[competition == c], p[competition == c]) for c in np.unique(competition)},
    }


def calibration_table(y, p, bins: int = 10) -> pd.DataFrame:
    df = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    df["bin"] = pd.cut(df.p, np.linspace(0, 1, bins + 1), include_lowest=True, labels=False)
    return (
        df.groupby("bin")
        .agg(mean_pred=("p", "mean"), frac_won=("y", "mean"), n=("y", "size"))
        .reset_index()
    )


def with_predictions(model, df: pd.DataFrame) -> pd.DataFrame:
    out = df.assign(wp=predict(model, df), in_test=df.start_date >= pd.Timestamp(CUTOFF))
    start = start_state(df)
    start_wp = pd.Series(predict(model, start), index=start.match_id)
    out["wp_before"] = out.groupby("match_id").wp.shift(1).fillna(out.match_id.map(start_wp))
    return out


def main() -> None:
    states = load_states(Path("data/cricket.duckdb"))
    train, test = time_split(states)
    models = {"baseline": fit_baseline(train), "model": fit_model(train)}

    metrics, calibration = {}, []
    for name, model in models.items():
        p = predict(model, test)
        metrics[name] = evaluate(test.chase_won, p, test.competition)
        calibration.append(calibration_table(test.chase_won, p).assign(model_name=name))

    metrics["ablation_validation_2022"] = ablation(train)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    pd.concat(calibration).to_parquet(OUT_DIR / "calibration.parquet", index=False)
    with_predictions(models["model"], states).to_parquet(OUT_DIR / "predictions.parquet", index=False)
    print(json.dumps({k: metrics[k]["overall"] for k in models}, indent=2))
    print(json.dumps(metrics["ablation_validation_2022"], indent=2))


if __name__ == "__main__":
    main()
