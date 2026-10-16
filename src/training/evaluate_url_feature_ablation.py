
"""Run controlled XGBoost feature ablations on domain-held-out URL folds."""

from pathlib import Path

import pandas as pd

from src.evaluate.url_metrics import evaluate_url_classifier
from src.features.preprocessing import load_url_split
from src.features.url_features_schema import URL_ONLY_FEATURES
from src.models.baselines.xgboost_model import build_xgboost


SPLIT_DIRECTORY = Path("data/processed/url_splits")
RESULTS_DIRECTORY = Path("reports/experiments/url_feature_ablation")

METRICS = [
    "accuracy",
    "phishing_precision",
    "phishing_recall",
    "phishing_f1",
    "legitimate_precision",
    "legitimate_recall",
    "legitimate_f1",
    "macro_f1",
    "roc_auc",
    "pr_auc",
]

REMOVED_PATH_QUERY_FEATURES = {
    "URLDepth",
    "NoOfEqualsInURL",
    "NoOfQMarkInURL",
    "NoOfAmpersandInURL",
}

VARIANTS = {
    "full_21_features": set(URL_ONLY_FEATURES),
    "without_url_depth": set(URL_ONLY_FEATURES) - {"URLDepth"},
    "without_path_query_signals": (
        set(URL_ONLY_FEATURES) - REMOVED_PATH_QUERY_FEATURES
    ),
}


def load_domain_folds():
    """Load the five existing domain-held-out folds."""

    files = sorted(SPLIT_DIRECTORY.glob("domain_aware_fold_*.csv"))

    if len(files) != 5:
        raise ValueError(
            f"Expected 5 domain-aware folds, found {len(files)}."
        )

    folds = {}

    for fold_file in files:
        fold_name = fold_file.stem
        X, y = load_url_split(
            SPLIT_DIRECTORY,
            fold_file.name,
            fold_name,
        )

        missing = set(URL_ONLY_FEATURES) - set(X.columns)
        if missing:
            raise ValueError(
                f"{fold_name} is missing expected features: {sorted(missing)}"
            )

        folds[fold_name] = (X, y)
        print(f"Loaded {fold_name}: {len(X):,} rows")

    return folds


def get_phishing_scores(model, X):
    """Return continuous scores where larger means more phishing-like."""

    classifier = model.named_steps["classifier"]
    classes = list(classifier.classes_)
    phishing_index = classes.index(0)

    return model.predict_proba(X)[:, phishing_index]


def evaluate_ablation():
    """Evaluate each feature set on each held-out domain fold."""

    folds = load_domain_folds()
    fold_names = list(folds)
    results = []

    for variant_name, feature_set in VARIANTS.items():
        features = [name for name in URL_ONLY_FEATURES if name in feature_set]

        print(f"\n{'=' * 72}")
        print(f"Variant: {variant_name} ({len(features)} features)")
        print("=" * 72)

        for held_out_fold in fold_names:
            train_fold_names = [
                name for name in fold_names if name != held_out_fold
            ]

            X_train = pd.concat(
                [folds[name][0][features] for name in train_fold_names],
                ignore_index=True,
            )
            y_train = pd.concat(
                [folds[name][1] for name in train_fold_names],
                ignore_index=True,
            )

            X_test, y_test = folds[held_out_fold]
            X_test = X_test[features]

            model = build_xgboost(random_state=42)
            model.fit(X_train, y_train)

            predictions = model.predict(X_test)
            scores = get_phishing_scores(model, X_test)

            metrics = evaluate_url_classifier(
                y_true=y_test,
                y_pred=predictions,
                phishing_scores=scores,
            )

            row = {
                "variant": variant_name,
                "feature_count": len(features),
                "held_out_fold": held_out_fold,
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                **{metric: metrics.get(metric) for metric in METRICS},
            }
            results.append(row)

            print(
                f"{held_out_fold}: "
                f"Macro F1={metrics['macro_f1']:.4f} | "
                f"Phishing recall={metrics['phishing_recall']:.4f} | "
                f"PR-AUC={metrics['pr_auc']:.4f}"
            )

            del model

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    fold_results = pd.DataFrame(results)
    fold_results.to_csv(
        RESULTS_DIRECTORY / "fold_results.csv",
        index=False,
    )

    aggregate = (
        fold_results.groupby(["variant", "feature_count"])[METRICS]
        .agg(["mean", "std"])
        .reset_index()
    )
    aggregate.columns = [
        "_".join(str(part) for part in column if part).rstrip("_")
        if isinstance(column, tuple)
        else column
        for column in aggregate.columns
    ]

    aggregate.to_csv(
        RESULTS_DIRECTORY / "aggregate_results.csv",
        index=False,
    )

    summary_columns = [
        "variant",
        "feature_count",
        "macro_f1_mean",
        "macro_f1_std",
        "phishing_recall_mean",
        "phishing_recall_std",
        "pr_auc_mean",
        "pr_auc_std",
    ]

    print("\n=== Feature ablation summary ===")
    print(
        aggregate[summary_columns].to_string(
            index=False,
            float_format=lambda value: f"{value:.6f}",
        )
    )

    print(f"\nResults saved to: {RESULTS_DIRECTORY}")
    print("Original models, splits, and baseline reports were not modified.")

    return fold_results, aggregate


if __name__ == "__main__":
    evaluate_ablation()
