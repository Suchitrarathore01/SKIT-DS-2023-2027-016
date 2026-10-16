
"""Evaluate URL baselines using five domain-held-out folds."""

from pathlib import Path

import pandas as pd
from sklearn.base import clone

from src.evaluate.url_metrics import evaluate_url_classifier
from src.features.preprocessing import load_url_split
from src.models.baselines.logistic_regression import build_logistic_regression
from src.models.baselines.svm import build_svm
from src.models.baselines.random_forest import build_random_forest
from src.models.baselines.xgboost_model import build_xgboost


SPLIT_DIRECTORY = Path("data/processed/url_splits")
RESULTS_DIRECTORY = Path("reports/experiments/url_domain_folds")

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

MODEL_BUILDERS = {
    "logistic_regression": build_logistic_regression,
    "linear_svm": build_svm,
    "random_forest": build_random_forest,
    "xgboost": build_xgboost,
}

def load_domain_folds():
    """Load all five pre-generated domain-held-out folds."""

    files = sorted(
        SPLIT_DIRECTORY.glob("domain_aware_fold_*.csv")
    )

    if len(files) != 5:
        raise ValueError(
            f"Expected exactly 5 domain-aware folds, found {len(files)}."
        )

    folds = {}

    for fold_file in files:
        fold_name = fold_file.stem
        X, y = load_url_split(
            SPLIT_DIRECTORY,
            fold_file.name,
            fold_name,
        )
        folds[fold_name] = (X, y)

        print(f"Loaded {fold_name}: {len(X):,} rows")

    return folds


def get_phishing_scores(model, X):
    """Return continuous scores where larger values mean more phishing-like."""

    classifier = model.named_steps["classifier"]
    classes = list(classifier.classes_)
    phishing_index = classes.index(0)

    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, phishing_index]

    # LinearSVC decision scores are oriented toward classes_[1].
    decision_scores = model.decision_function(X)

    if phishing_index == 0:
        return -decision_scores

    return decision_scores


def evaluate_domain_folds():
    """Train on four folds and evaluate on each held-out fifth fold."""

    folds = load_domain_folds()
    fold_names = list(folds.keys())
    results = []

    for held_out_fold in fold_names:
        print(f"\n{'=' * 65}")
        print(f"Held-out evaluation: {held_out_fold}")
        print("=" * 65)

        train_fold_names = [
            name for name in fold_names if name != held_out_fold
        ]

        X_train = pd.concat(
            [folds[name][0] for name in train_fold_names],
            ignore_index=True,
        )
        y_train = pd.concat(
            [folds[name][1] for name in train_fold_names],
            ignore_index=True,
        )

        X_test, y_test = folds[held_out_fold]

        print(f"Training rows: {len(X_train):,}")
        print(f"Held-out rows: {len(X_test):,}")

        for model_name, builder in MODEL_BUILDERS.items():
            print(f"\nTraining {model_name}...")

            model = builder(random_state=42)
            model.fit(X_train, y_train)

            predictions = model.predict(X_test)
            scores = get_phishing_scores(model, X_test)

            metrics = evaluate_url_classifier(
                y_true=y_test,
                y_pred=predictions,
                phishing_scores=scores,
            )

            row = {
                "model": model_name,
                "held_out_fold": held_out_fold,
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                **{metric: metrics.get(metric) for metric in METRICS},
            }
            results.append(row)

            print(
                f"Macro F1: {metrics['macro_f1']:.4f} | "
                f"Phishing recall: {metrics['phishing_recall']:.4f}"
            )

            # Release the fitted model before training the next one.
            del model

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    fold_results = pd.DataFrame(results)
    fold_results.to_csv(
        RESULTS_DIRECTORY / "fold_results.csv",
        index=False,
    )

    aggregate = (
        fold_results.groupby("model")[METRICS]
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

    print("\n=== Domain-aware aggregate results ===")
    print(aggregate.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"\nSaved fold results to: {RESULTS_DIRECTORY / 'fold_results.csv'}")
    print(
        "Saved aggregate results to: "
        f"{RESULTS_DIRECTORY / 'aggregate_results.csv'}"
    )

    print(
        "\nEach result is evaluated on domains excluded from that run's "
        "training data. The standard stratified test split was not used."
    )

    return fold_results, aggregate


if __name__ == "__main__":
    evaluate_domain_folds()
