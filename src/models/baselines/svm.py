
"""Linear SVM baseline for phishing URL classification."""

from pathlib import Path

import joblib
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from src.evaluate.url_metrics import (
    evaluate_url_classifier,
    print_url_metrics,
)
from src.features.preprocessing import load_url_split


def build_svm(random_state: int = 42) -> Pipeline:
    """Build a scaled Linear SVM pipeline."""

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LinearSVC(
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=random_state,
                ),
            ),
        ]
    )


def train_svm(
    split_directory: str = "data/processed/url_splits",
    train_file: str = "stratified_train.csv",
    validation_file: str = "stratified_validation.csv",
    model_directory: str = "models/url_baselines",
    random_state: int = 42,
) -> dict:
    """Train on training data and evaluate on validation data."""

    X_train, y_train = load_url_split(
        split_directory, train_file, "train"
    )
    X_val, y_val = load_url_split(
        split_directory, validation_file, "validation"
    )

    model = build_svm(random_state=random_state)
    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    # LinearSVC scores are decision scores, not probabilities.
    # Negate them because class 0 (phishing) is the target of interest.
    decision_scores = model.decision_function(X_val)
    classes = list(model.named_steps["classifier"].classes_)
    phishing_index = classes.index(0)

    phishing_scores = (
        -decision_scores if phishing_index == 0 else decision_scores
    )

    results = evaluate_url_classifier(
        y_true=y_val,
        y_pred=predictions,
        phishing_scores=phishing_scores,
    )

    print_url_metrics(results)

    output_directory = Path(model_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    model_path = output_directory / "svm.joblib"
    joblib.dump(model, model_path)

    print(f"\nSaved model to: {model_path}")

    return results


if __name__ == "__main__":
    train_svm()
