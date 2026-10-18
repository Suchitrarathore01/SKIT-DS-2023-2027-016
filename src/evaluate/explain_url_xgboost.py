
"""Generate phishing-oriented SHAP explanations for XGBoost URL detection."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from src.features.preprocessing import load_url_split


MODEL_PATH = Path("models/url_baselines/xgboost.joblib")
SPLIT_DIRECTORY = Path("data/processed/url_splits")
VALIDATION_FILE = "stratified_validation.csv"
OUTPUT_DIRECTORY = Path("reports/experiments/url_xgboost_shap")

MAX_EXPLANATION_ROWS = 500
MAX_BACKGROUND_ROWS = 100


def explain_xgboost_url_model() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate global and local SHAP explanations oriented toward phishing."""

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained XGBoost model not found: {MODEL_PATH}. "
            "Train the URL baselines first."
        )

    model = joblib.load(MODEL_PATH)
    classifier = model.named_steps["classifier"]
    imputer = model.named_steps["imputer"]

    # The project's fixed label convention is 0 = phishing, 1 = legitimate.
    if list(classifier.classes_) != [0, 1]:
        raise ValueError(
            "Expected XGBoost classes [0, 1], where 0 is phishing "
            "and 1 is legitimate."
        )

    X_validation, y_validation = load_url_split(
        SPLIT_DIRECTORY,
        VALIDATION_FILE,
        "validation",
    )

    sample_size = min(MAX_EXPLANATION_ROWS, len(X_validation))
    background_size = min(MAX_BACKGROUND_ROWS, len(X_validation))

    X_sample = X_validation.sample(
        n=sample_size,
        random_state=42,
    )
    y_sample = y_validation.loc[X_sample.index]

    X_background = X_validation.sample(
        n=background_size,
        random_state=42,
    )

    X_sample_imputed = pd.DataFrame(
        imputer.transform(X_sample),
        columns=X_sample.columns,
        index=X_sample.index,
    )
    X_background_imputed = pd.DataFrame(
        imputer.transform(X_background),
        columns=X_background.columns,
        index=X_background.index,
    )

    explainer = shap.TreeExplainer(
        classifier,
        data=X_background_imputed,
        feature_perturbation="interventional",
        model_output="raw",
    )
    shap_values = explainer(X_sample_imputed)

    if shap_values.values.shape != X_sample_imputed.shape:
        raise ValueError(
            f"Unexpected SHAP shape {shap_values.values.shape}; "
            f"expected {X_sample_imputed.shape}."
        )

    # For this binary XGBoost model, raw output is class-1 log-odds.
    # Negating it makes positive contributions point toward phishing (class 0).
    class_1_margin = classifier.predict(
        X_sample_imputed,
        output_margin=True,
    )
    base_values = np.asarray(shap_values.base_values).reshape(-1)

    reconstructed_class_1_margin = (
        base_values + shap_values.values.sum(axis=1)
    )

    if not np.allclose(
        reconstructed_class_1_margin,
        class_1_margin,
        rtol=1e-3,
        atol=1e-2,
    ):
        max_error = np.max(
            np.abs(reconstructed_class_1_margin - class_1_margin)
        )
        raise ValueError(
            "SHAP additivity check failed. "
            f"Maximum raw-margin difference: {max_error:.6f}"
        )

    phishing_shap_values = -shap_values.values

    # Mean absolute SHAP measures influence magnitude; signed mean
    # now indicates average contribution toward phishing or legitimate.
    importance = pd.DataFrame(
        {
            "feature": X_sample_imputed.columns,
            "mean_absolute_shap": np.abs(
                phishing_shap_values
            ).mean(axis=0),
            "mean_phishing_oriented_shap": phishing_shap_values.mean(
                axis=0
            ),
        }
    ).sort_values(
        "mean_absolute_shap",
        ascending=False,
    ).reset_index(drop=True)

    predictions = model.predict(X_sample)
    phishing_class_index = list(classifier.classes_).index(0)
    phishing_probabilities = model.predict_proba(X_sample)[
        :, phishing_class_index
    ]

    local_explanations = pd.DataFrame(
        phishing_shap_values,
        columns=X_sample_imputed.columns,
        index=X_sample_imputed.index,
    )
    local_explanations.insert(0, "actual_label", y_sample)
    local_explanations.insert(1, "predicted_label", predictions)
    local_explanations.insert(
        2,
        "actual_class_name",
        y_sample.map({0: "phishing", 1: "legitimate"}),
    )
    local_explanations.insert(
        3,
        "predicted_class_name",
        pd.Series(predictions, index=X_sample.index).map(
            {0: "phishing", 1: "legitimate"}
        ),
    )
    local_explanations.insert(
        4,
        "phishing_probability",
        phishing_probabilities,
    )

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    importance_path = OUTPUT_DIRECTORY / "global_feature_importance.csv"
    local_path = OUTPUT_DIRECTORY / "local_explanations.csv"

    importance.to_csv(importance_path, index=False)
    local_explanations.to_csv(local_path, index_label="validation_row")

    print(f"Explained {sample_size} validation URLs.")
    print("SHAP additivity check passed.")
    print(
        "Interpretation: positive feature contributions push toward "
        "phishing; negative contributions push toward legitimate."
    )
    print("Contributions are in negative raw-margin (log-odds) units.")
    print("\nTop 10 features by mean absolute SHAP value:")
    print(importance.head(10).to_string(index=False))
    print(f"\nGlobal results saved to: {importance_path}")
    print(f"Local explanations saved to: {local_path}")

    return importance, local_explanations


if __name__ == "__main__":
    explain_xgboost_url_model()
