
"""Run and compare classical phishing URL baselines."""

from pathlib import Path

import pandas as pd

from src.models.baselines.logistic_regression import (
    train_logistic_regression,
)
from src.models.baselines.svm import train_svm
from src.models.baselines.random_forest import train_random_forest


RESULTS_DIRECTORY = Path("reports/experiments/url_baselines")

COMPARISON_COLUMNS = [
    "model",
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


def run_url_baselines() -> pd.DataFrame:
    """Train all URL baselines and save their validation comparison."""

    experiments = [
        ("logistic_regression", train_logistic_regression),
        ("linear_svm", train_svm),
        ("random_forest", train_random_forest),
    ]

    rows = []

    for model_name, train_function in experiments:
        print(f"\n{'=' * 60}")
        print(f"Running model: {model_name}")
        print("=" * 60)

        metrics = train_function()

        row = {
            "model": model_name,
            **{
                metric: metrics.get(metric)
                for metric in COMPARISON_COLUMNS
                if metric != "model"
            },
        }
        rows.append(row)

    comparison = pd.DataFrame(
        rows,
        columns=COMPARISON_COLUMNS,
    )

    comparison = comparison.sort_values(
        by="macro_f1",
        ascending=False,
    ).reset_index(drop=True)

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIRECTORY / "validation_comparison.csv"

    comparison.to_csv(output_path, index=False)

    print("\n=== URL Baseline Validation Comparison ===")
    print(comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"\nResults saved to: {output_path}")
    print(
        "\nReminder: these are validation results. "
        "The test split has not been used for model selection."
    )

    return comparison


if __name__ == "__main__":
    run_url_baselines()
