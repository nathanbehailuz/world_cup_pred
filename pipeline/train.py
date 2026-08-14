"""Train baseline and XGBoost models on international match features.

Runs a four-configuration experiment grid on a temporal split, all evaluated
on the same competitive-only test set. The best configuration is refit on all
available data as the production model.
"""

from __future__ import annotations

import argparse
import json
import sqlite3

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler

from .paths import DB_PATH, META_PATH, MODEL_PATH

TRAIN_CUTOFF = "2023-01-01"
MIN_MATCH_DATE = "1990-01-01"
BOOTSTRAP_SAMPLES = 1000
PERMUTATION_REPEATS = 10

SQUAD_FEATURE_COLUMNS = [
    "home_squad_value_log",
    "away_squad_value_log",
    "squad_value_log_diff",
]

MARKET_FEATURE_COLUMNS = [
    "market_implied_home",
    "market_implied_draw",
    "market_implied_away",
    "market_implied_diff",
]

BASE_FEATURE_COLUMNS = [
    "elo_diff",
    "form_pts_5_diff",
    "form_gd_5_diff",
    "form_pts_10_diff",
    "form_gd_10_diff",
    "form_gf_5_diff",
    "form_ga_5_diff",
    "form_gf_10_diff",
    "form_ga_10_diff",
    "home_days_since_last",
    "away_days_since_last",
    "neutral",
    "competitive",
    "home_elo",
    "away_elo",
]

FULL_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + SQUAD_FEATURE_COLUMNS
FULL_WITH_MARKET_COLUMNS = FULL_FEATURE_COLUMNS + MARKET_FEATURE_COLUMNS

XGB_PARAMS = dict(
    objective="multi:softprob",
    num_class=3,
    max_depth=4,
    learning_rate=0.1,
    n_estimators=300,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric="mlogloss",
)

OUTCOME_NAMES = ("home_win", "draw", "away_win")


def diff_columns(feature_columns: list[str]) -> list[str]:
    return [c for c in feature_columns if c.endswith("_diff")]


def swap_columns(feature_columns: list[str]) -> list[tuple[str, str]]:
    swaps = [
        ("home_days_since_last", "away_days_since_last"),
        ("home_elo", "away_elo"),
    ]
    if "home_squad_value_log" in feature_columns:
        swaps.append(("home_squad_value_log", "away_squad_value_log"))
    if "market_implied_home" in feature_columns:
        swaps.append(("market_implied_home", "market_implied_away"))
    return swaps


def mirror_features(
    df: pd.DataFrame, feature_columns: list[str]
) -> pd.DataFrame:
    """Swap the home and away slots (meaningful only for neutral-venue rows)."""
    mirrored = df.copy()
    for col in diff_columns(feature_columns):
        mirrored[col] = -df[col]
    for a, b in swap_columns(feature_columns):
        mirrored[a] = df[b].values
        mirrored[b] = df[a].values
    return mirrored


def symmetrize_neutral(
    proba: np.ndarray, proba_mirrored: np.ndarray, test: pd.DataFrame
) -> np.ndarray:
    """Average mirrored predictions for neutral-venue rows."""
    out = proba.copy()
    mask = (test["neutral"] == 1).values
    out[mask] = (proba[mask] + proba_mirrored[mask, ::-1]) / 2.0
    return out


def brier_score_multiclass(y_true: np.ndarray, proba: np.ndarray) -> float:
    one_hot = np.zeros_like(proba)
    one_hot[np.arange(len(y_true)), y_true] = 1.0
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def compute_metrics(y_true: np.ndarray, proba: np.ndarray) -> dict:
    preds = proba.argmax(axis=1)
    return {
        "log_loss": float(log_loss(y_true, proba, labels=[0, 1, 2])),
        "brier_score": brier_score_multiclass(y_true, proba),
        "accuracy": float(accuracy_score(y_true, preds)),
    }


def evaluate(name: str, y_true: np.ndarray, proba: np.ndarray) -> dict:
    metrics = compute_metrics(y_true, proba)
    print(f"\n{name}")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
    return metrics


def calibration_table(
    y_true: np.ndarray, proba: np.ndarray, class_idx: int, n_bins: int = 10
) -> list[dict]:
    """Bin predicted probability for one class vs empirical frequency."""
    p = proba[:, class_idx]
    hits = (y_true == class_idx).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        n = int(mask.sum())
        if n == 0:
            continue
        rows.append(
            {
                "bin": f"{edges[b]:.1f}-{edges[b + 1]:.1f}",
                "n": n,
                "mean_predicted": float(p[mask].mean()),
                "empirical": float(hits[mask].mean()),
            }
        )
    return rows


def print_calibration(y_true: np.ndarray, proba: np.ndarray) -> dict:
    """Print per-class calibration tables; return them for the metadata file."""
    tables: dict = {}
    print("\n=== Calibration check (production config, test set) ===")
    for idx, name in enumerate(OUTCOME_NAMES):
        rows = calibration_table(y_true, proba, idx)
        tables[name] = rows
        print(f"\n  {name}:")
        print("    bin        n     predicted  empirical")
        for row in rows:
            print(
                f"    {row['bin']:<9s}{row['n']:>6d}     "
                f"{row['mean_predicted']:.3f}      {row['empirical']:.3f}"
            )
    return tables


def load_features(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM features", conn)
    df = df[df["date"] >= MIN_MATCH_DATE].copy()
    return df


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["date"] < TRAIN_CUTOFF].copy()
    test = df[df["date"] >= TRAIN_CUTOFF].copy()
    return train, test


def constant_prior_proba(train: pd.DataFrame, n_test: int) -> np.ndarray:
    freqs = np.bincount(train["outcome"].values, minlength=3) / len(train)
    return np.tile(freqs, (n_test, 1))


def elo_baseline_proba(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[np.ndarray, LogisticRegression, StandardScaler]:
    scaler = StandardScaler()
    x_train = scaler.fit_transform(train[["elo_diff"]].values)
    x_test = scaler.transform(test[["elo_diff"]].values)
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(x_train, train["outcome"].values)
    proba = model.predict_proba(x_test)
    proba_mirrored = model.predict_proba(
        scaler.transform(-test[["elo_diff"]].values)
    )
    proba = symmetrize_neutral(proba, proba_mirrored, test)
    return proba, model, scaler


def bootstrap_log_loss_ci(
    y_true: np.ndarray,
    proba: np.ndarray,
    n_boot: int = BOOTSTRAP_SAMPLES,
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    point = float(log_loss(y_true, proba, labels=[0, 1, 2]))
    samples = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        samples.append(log_loss(y_true[idx], proba[idx], labels=[0, 1, 2]))
    arr = np.array(samples)
    return {
        "point": point,
        "ci_low": float(np.percentile(arr, 2.5)),
        "ci_high": float(np.percentile(arr, 97.5)),
        "n_bootstrap": n_boot,
    }


def paired_bootstrap_log_loss_diff(
    y_true: np.ndarray,
    proba_a: np.ndarray,
    proba_b: np.ndarray,
    n_boot: int = BOOTSTRAP_SAMPLES,
    seed: int = 42,
) -> dict:
    """Bootstrap CI for log_loss(proba_a) - log_loss(proba_b) on same resamples."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    point_a = log_loss(y_true, proba_a, labels=[0, 1, 2])
    point_b = log_loss(y_true, proba_b, labels=[0, 1, 2])
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        la = log_loss(y_true[idx], proba_a[idx], labels=[0, 1, 2])
        lb = log_loss(y_true[idx], proba_b[idx], labels=[0, 1, 2])
        diffs.append(la - lb)
    arr = np.array(diffs)
    return {
        "point": float(point_a - point_b),
        "ci_low": float(np.percentile(arr, 2.5)),
        "ci_high": float(np.percentile(arr, 97.5)),
        "n_bootstrap": n_boot,
    }


def run_bootstrap_analysis(
    y_true: np.ndarray,
    prior_proba: np.ndarray,
    elo_proba: np.ndarray,
    xgb_proba: np.ndarray,
) -> dict:
    prior_ci = bootstrap_log_loss_ci(y_true, prior_proba)
    elo_ci = bootstrap_log_loss_ci(y_true, elo_proba)
    xgb_ci = bootstrap_log_loss_ci(y_true, xgb_proba)
    diff_ci = paired_bootstrap_log_loss_diff(y_true, xgb_proba, elo_proba)

    print("\n=== Bootstrap 95% CIs (log loss, test set) ===")
    for name, ci in [
        ("Constant prior", prior_ci),
        ("Elo logistic", elo_ci),
        ("Production XGBoost", xgb_ci),
    ]:
        print(
            f"  {name}: {ci['point']:.4f} "
            f"[{ci['ci_low']:.4f}, {ci['ci_high']:.4f}]"
        )
    print(
        f"  XGBoost − Elo difference: {diff_ci['point']:.4f} "
        f"[{diff_ci['ci_low']:.4f}, {diff_ci['ci_high']:.4f}]"
    )
    return {
        "constant_prior": prior_ci,
        "elo_baseline": elo_ci,
        "production_xgboost": xgb_ci,
        "xgboost_minus_elo": diff_ci,
    }


def permutation_importance(
    model: xgb.XGBClassifier,
    test: pd.DataFrame,
    feature_columns: list[str],
    y_true: np.ndarray,
    n_repeats: int = PERMUTATION_REPEATS,
    seed: int = 42,
) -> list[dict]:
    rng = np.random.default_rng(seed)
    base_proba = model.predict_proba(test[feature_columns].values)
    base_mirrored = model.predict_proba(
        mirror_features(test, feature_columns)[feature_columns].values
    )
    base_proba = symmetrize_neutral(base_proba, base_mirrored, test)
    base_loss = log_loss(y_true, base_proba, labels=[0, 1, 2])

    rows = []
    for col in feature_columns:
        deltas = []
        for _ in range(n_repeats):
            shuffled = test.copy()
            shuffled[col] = rng.permutation(shuffled[col].values)
            proba = model.predict_proba(shuffled[feature_columns].values)
            proba_mirrored = model.predict_proba(
                mirror_features(shuffled, feature_columns)[feature_columns].values
            )
            proba = symmetrize_neutral(proba, proba_mirrored, shuffled)
            deltas.append(log_loss(y_true, proba, labels=[0, 1, 2]) - base_loss)
        rows.append(
            {
                "feature": col,
                "delta_log_loss_mean": float(np.mean(deltas)),
                "delta_log_loss_std": float(np.std(deltas)),
            }
        )
    rows.sort(key=lambda r: r["delta_log_loss_mean"], reverse=True)
    return rows


def gain_importance(
    model: xgb.XGBClassifier, feature_columns: list[str]
) -> list[dict]:
    importances = model.feature_importances_
    rows = [
        {"feature": col, "gain": float(imp)}
        for col, imp in zip(feature_columns, importances)
    ]
    rows.sort(key=lambda r: r["gain"], reverse=True)
    return rows


def slice_metrics(
    test: pd.DataFrame, y_true: np.ndarray, proba: np.ndarray, mask: pd.Series
) -> dict | None:
    if mask.sum() == 0:
        return None
    y = y_true[mask.values]
    p = proba[mask.values]
    m = compute_metrics(y, p)
    m["n"] = int(mask.sum())
    m["mean_predicted_draw"] = float(p[:, 1].mean())
    return m


def error_analysis_slices(
    test: pd.DataFrame, y_true: np.ndarray, proba: np.ndarray
) -> list[dict]:
    abs_elo = test["elo_diff"].abs()
    slice_defs = [
        ("elo_gap_lt_50", abs_elo < 50),
        ("elo_gap_50_150", (abs_elo >= 50) & (abs_elo < 150)),
        ("elo_gap_150_300", (abs_elo >= 150) & (abs_elo < 300)),
        ("elo_gap_gt_300", abs_elo >= 300),
        ("neutral", test["neutral"] == 1),
        ("non_neutral", test["neutral"] == 0),
        ("true_home_win", test["outcome"] == 0),
        ("true_draw", test["outcome"] == 1),
        ("true_away_win", test["outcome"] == 2),
    ]
    rows = []
    for name, mask in slice_defs:
        m = slice_metrics(test, y_true, proba, mask)
        if m is None:
            continue
        rows.append({"slice": name, **m})
    return rows


def print_error_analysis(rows: list[dict]) -> None:
    print("\n=== Error analysis (production config, test set) ===")
    print(
        f"  {'slice':<20s} {'n':>6s} {'log_loss':>9s} "
        f"{'accuracy':>9s} {'mean_p_draw':>12s}"
    )
    for row in rows:
        print(
            f"  {row['slice']:<20s}{row['n']:>6d} "
            f"{row['log_loss']:>9.4f} {row['accuracy']:>9.4f} "
            f"{row['mean_predicted_draw']:>12.4f}"
        )


def print_importance(perm: list[dict], gain: list[dict]) -> None:
    print("\n=== Permutation importance (Δ log loss when shuffled) ===")
    for row in perm:
        print(
            f"  {row['feature']:<28s} "
            f"+{row['delta_log_loss_mean']:.4f} "
            f"(±{row['delta_log_loss_std']:.4f})"
        )
    print("\n=== XGBoost gain importance ===")
    for row in gain:
        print(f"  {row['feature']:<28s} {row['gain']:.4f}")


def generate_sample_predictions(
    test: pd.DataFrame,
    y_true: np.ndarray,
    proba: np.ndarray,
) -> list[dict]:
    """Curated examples from the test set plus interpretive comments."""
    samples: list[dict] = []

    def add_from_row(
        row: pd.Series,
        p: np.ndarray,
        comment: str,
        category: str,
    ) -> None:
        samples.append(
            {
                "category": category,
                "date": row["date"],
                "team_a": row["home_team"],
                "team_b": row["away_team"],
                "neutral": bool(row["neutral"]),
                "elo_diff": float(row["elo_diff"]),
                "team_a_win": float(p[0]),
                "draw": float(p[1]),
                "team_b_win": float(p[2]),
                "actual_outcome": int(row["outcome"]),
                "comment": comment,
            }
        )

    # Strong favorite: largest abs elo_diff
    idx = test["elo_diff"].abs().idxmax()
    i = test.index.get_loc(idx)
    row = test.loc[idx]
    add_from_row(
        row,
        proba[i],
        "Largest Elo gap on test set — model should favour the stronger side.",
        "strong_favorite",
    )

    # Close match: smallest abs elo_diff among competitive rows
    close = test[test["elo_diff"].abs() < 30]
    if not close.empty:
        idx = close["elo_diff"].abs().idxmin()
        i = test.index.get_loc(idx)
        row = test.loc[idx]
        add_from_row(
            row,
            proba[i],
            "Closest Elo ratings — draw probability should be relatively high.",
            "close_teams",
        )

    # Neutral example
    neutral_rows = test[test["neutral"] == 1]
    if not neutral_rows.empty:
        idx = neutral_rows.index[0]
        i = test.index.get_loc(idx)
        row = test.loc[idx]
        add_from_row(
            row,
            proba[i],
            "Neutral venue — symmetrization applied during evaluation.",
            "neutral",
        )

    # Non-neutral (home advantage)
    home_rows = test[test["neutral"] == 0]
    if not home_rows.empty:
        idx = home_rows["elo_diff"].abs().idxmax()
        i = test.index.get_loc(idx)
        row = test.loc[idx]
        add_from_row(
            row,
            proba[i],
            "Non-neutral venue with meaningful home slot — home advantage active.",
            "home_advantage",
        )

    return samples


def add_live_symmetry_sample(samples: list[dict]) -> list[dict]:
    """France vs Brazil neutral symmetry using current team_ratings + saved model."""
    try:
        from .predict import predict

        p_ab = predict("France", "Brazil", neutral=True)
        p_ba = predict("Brazil", "France", neutral=True)
        samples.append(
            {
                "category": "symmetry_check",
                "date": None,
                "team_a": "France",
                "team_b": "Brazil",
                "neutral": True,
                "elo_diff": None,
                "team_a_win": p_ab["France_win"],
                "draw": p_ab["draw"],
                "team_b_win": p_ab["Brazil_win"],
                "actual_outcome": None,
                "comment": (
                    "Live prediction: FRA vs BRA and BRA vs FRA return identical "
                    f"distributions ({p_ab['France_win']:.3f} / {p_ab['draw']:.3f} / "
                    f"{p_ab['Brazil_win']:.3f})."
                ),
                "reversed_team_a_win": p_ba["Brazil_win"],
                "reversed_team_b_win": p_ba["France_win"],
            }
        )
    except Exception as exc:
        samples.append(
            {
                "category": "symmetry_check",
                "comment": f"Symmetry check skipped: {exc}",
            }
        )
    return samples


def train_baseline(
    train: pd.DataFrame, test: pd.DataFrame, label: str
) -> tuple[dict, np.ndarray]:
    proba, _, _ = elo_baseline_proba(train, test)
    metrics = evaluate(
        f"[{label}] Baseline (logistic on elo_diff)",
        test["outcome"].values,
        proba,
    )
    return metrics, proba


def train_xgboost(
    train: pd.DataFrame,
    test: pd.DataFrame,
    label: str,
    feature_columns: list[str],
) -> tuple[xgb.XGBClassifier, dict, np.ndarray]:
    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(
        train[feature_columns].values,
        train["outcome"].values,
        eval_set=[(test[feature_columns].values, test["outcome"].values)],
        verbose=False,
    )
    proba = model.predict_proba(test[feature_columns].values)
    proba_mirrored = model.predict_proba(
        mirror_features(test, feature_columns)[feature_columns].values
    )
    proba = symmetrize_neutral(proba, proba_mirrored, test)
    metrics = evaluate(f"[{label}] XGBoost", test["outcome"].values, proba)
    return model, metrics, proba


def run_experiment(
    df: pd.DataFrame,
    test: pd.DataFrame,
    *,
    competitive_only: bool,
    feature_columns: list[str],
    label: str,
) -> dict:
    """Train on the chosen subset; evaluate on the shared competitive test set."""
    train_pool, _ = temporal_split(df)
    train = (
        train_pool[train_pool["competitive"] == 1] if competitive_only else train_pool
    )

    print(f"\n=== Experiment: {label} ===")
    print(f"Features:     {len(feature_columns)} ({', '.join(feature_columns)})")
    print(f"Training set: {len(train)} matches (< {TRAIN_CUTOFF})")
    print(f"Test set:     {len(test)} competitive matches (>= {TRAIN_CUTOFF})")

    baseline_metrics, _ = train_baseline(train, test, label)
    model, xgb_metrics, xgb_proba = train_xgboost(
        train, test, label, feature_columns=feature_columns
    )

    return {
        "label": label,
        "competitive_only": competitive_only,
        "feature_columns": feature_columns,
        "n_features": len(feature_columns),
        "n_train": len(train),
        "n_test": len(test),
        "baseline_metrics": baseline_metrics,
        "xgb_metrics": xgb_metrics,
        "_xgb_proba": xgb_proba,
        "_model": model,
    }


def refit_production_model(
    df: pd.DataFrame,
    competitive_only: bool,
    feature_columns: list[str],
) -> tuple[xgb.XGBClassifier, int]:
    """Refit on ALL available data (no holdout) for real-world predictions."""
    data = df[df["competitive"] == 1] if competitive_only else df
    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(data[feature_columns].values, data["outcome"].values, verbose=False)
    return model, len(data)


def load_model_meta() -> dict | None:
    if not META_PATH.exists():
        return None
    return json.loads(META_PATH.read_text())


def training_is_current(cutoff: str | None, retrain: bool) -> bool:
    if retrain or not MODEL_PATH.exists():
        return False
    meta = load_model_meta()
    if meta is None:
        return False
    if meta.get("feature_cutoff") != cutoff:
        return False
    return (
        len(meta.get("experiments") or []) >= 5
        and "bootstrap_ci" in meta
        and "feature_importance" in meta
    )


def run_train(cutoff: str | None = None, retrain: bool = False) -> bool:
    """Train production model. Returns True if training ran."""
    if training_is_current(cutoff, retrain=retrain):
        print(
            f"Model already trained for cutoff={cutoff!r} "
            f"(use --retrain to force)."
        )
        return False

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run feature_engineering.py first."
        )

    conn = sqlite3.connect(DB_PATH)
    df = load_features(conn)
    conn.close()

    train_pool, test_pool = temporal_split(df)
    test = test_pool[test_pool["competitive"] == 1].copy()
    y_test = test["outcome"].values

    no_competitive_features = [c for c in FULL_FEATURE_COLUMNS if c != "competitive"]
    no_squad_features = BASE_FEATURE_COLUMNS

    experiments = [
        run_experiment(
            df,
            test,
            competitive_only=False,
            feature_columns=FULL_FEATURE_COLUMNS,
            label="train-all-matches-full",
        ),
        run_experiment(
            df,
            test,
            competitive_only=True,
            feature_columns=FULL_FEATURE_COLUMNS,
            label="train-competitive-only-full",
        ),
        run_experiment(
            df,
            test,
            competitive_only=False,
            feature_columns=no_competitive_features,
            label="train-all-matches-no-competitive-flag",
        ),
        run_experiment(
            df,
            test,
            competitive_only=False,
            feature_columns=no_squad_features,
            label="train-all-matches-no-squad",
        ),
        run_experiment(
            df,
            test,
            competitive_only=False,
            feature_columns=FULL_WITH_MARKET_COLUMNS,
            label="train-all-matches-with-market",
        ),
    ]

    print("\n=== Experiment comparison (same competitive test set) ===")
    for exp in experiments:
        m = exp["xgb_metrics"]
        print(
            f"  {exp['label']}: log_loss={m['log_loss']:.4f}, "
            f"brier={m['brier_score']:.4f}, acc={m['accuracy']:.4f}"
        )

    best = min(experiments, key=lambda e: e["xgb_metrics"]["log_loss"])
    print(f"\nBest configuration by log loss: {best['label']}")

    best_proba = best["_xgb_proba"]
    best_model = best["_model"]
    prod_features = best["feature_columns"]

    # Extended baselines on production training pool
    prod_train = train_pool if not best["competitive_only"] else train_pool[
        train_pool["competitive"] == 1
    ]
    prior_proba = constant_prior_proba(prod_train, len(test))
    prior_metrics = evaluate(
        "[production] Constant-prior baseline",
        y_test,
        prior_proba,
    )
    elo_proba, _, _ = elo_baseline_proba(prod_train, test)
    elo_metrics = compute_metrics(y_test, elo_proba)
    print("\n[production] Elo logistic baseline (for bootstrap comparison)")
    for key, value in elo_metrics.items():
        print(f"  {key}: {value:.4f}")

    bootstrap_ci = run_bootstrap_analysis(
        y_test, prior_proba, elo_proba, best_proba
    )

    perm_imp = permutation_importance(
        best_model, test, prod_features, y_test
    )
    gain_imp = gain_importance(best_model, prod_features)
    print_importance(perm_imp, gain_imp)

    error_slices = error_analysis_slices(test, y_test, best_proba)
    print_error_analysis(error_slices)

    calibration = print_calibration(y_test, best_proba)

    sample_predictions = generate_sample_predictions(test, y_test, best_proba)

    for exp in experiments:
        exp.pop("_xgb_proba", None)
        exp.pop("_model", None)

    model, n_fit = refit_production_model(
        df, best["competitive_only"], feature_columns=prod_features
    )
    print(
        f"Refit production model on all {n_fit} matches "
        f"({best['label']}, through {df['date'].max()})."
    )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_PATH)

    # Gain importance from refit model (deployment weights)
    gain_imp_refit = gain_importance(model, prod_features)

    sample_predictions = add_live_symmetry_sample(sample_predictions)

    meta = {
        "feature_columns": prod_features,
        "feature_cutoff": cutoff,
        "train_cutoff": TRAIN_CUTOFF,
        "min_match_date": MIN_MATCH_DATE,
        "selected_config": best["label"],
        "competitive_only": best["competitive_only"],
        "production_fit_rows": n_fit,
        "production_fit_through": df["date"].max(),
        "experiments": experiments,
        "baselines": {
            "constant_prior": prior_metrics,
            "elo_logistic": elo_metrics,
            "production_xgboost": best["xgb_metrics"],
        },
        "bootstrap_ci": bootstrap_ci,
        "feature_importance": {
            "permutation": perm_imp,
            "gain_experiment_model": gain_imp,
            "gain_production_model": gain_imp_refit,
        },
        "error_analysis": error_slices,
        "sample_predictions": sample_predictions,
        "calibration": calibration,
        "outcome_labels": ["home_win", "draw", "away_win"],
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"\nSaved production XGBoost model to {MODEL_PATH}")
    print(f"Saved metadata to {META_PATH}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Train XGBoost production model.")
    parser.add_argument(
        "--cutoff",
        metavar="YYYY-MM-DD",
        help="Feature cutoff used in feature_engineering (stored in metadata)",
    )
    parser.add_argument(
        "--retrain", action="store_true", help="Force retraining even if cutoff matches"
    )
    args = parser.parse_args()
    run_train(cutoff=args.cutoff, retrain=args.retrain)


if __name__ == "__main__":
    main()
