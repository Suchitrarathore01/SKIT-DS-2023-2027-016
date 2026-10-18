
"""Evaluation metrics for phishing URL classification."""

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


PHISHING_LABEL = 0
LEGITIMATE_LABEL = 1


def evaluate_url_classifier(
    y_true: Any,
    y_pred: Any,
    phishing_scores: Any = None,
) -> dict:
    """
    Calculate classification metrics for URL phishing detection.

    Labels:
        0 = phishing
        1 = legitimate

    phishing_scores, when provided, must be a continuous score where
    higher values indicate a greater likelihood of phishing. These
    may be probabilities or decision scores, not necessarily probabilities.
    """

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    if y_true.ndim != 1 or y_pred.ndim != 1:
        raise ValueError("y_true and y_pred must be one-dimensional.")

    if len(y_true) == 0:
        raise ValueError("Evaluation data must not be empty.")

    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have equal lengths.")

    valid_labels = {PHISHING_LABEL, LEGITIMATE_LABEL}

    if not set(np.unique(y_true)).issubset(valid_labels):
        raise ValueError("y_true must contain only labels 0 and 1.")

    if not set(np.unique(y_pred)).issubset(valid_labels):
        raise ValueError("y_pred must contain only labels 0 and 1.")

    phishing_precision = precision_score(
        y_true,
        y_pred,
        pos_label=PHISHING_LABEL,
        zero_division=0,
    )
    phishing_recall = recall_score(
        y_true,
        y_pred,
        pos_label=PHISHING_LABEL,
        zero_division=0,
    )
    phishing_f1 = f1_score(
        y_true,
        y_pred,
        pos_label=PHISHING_LABEL,
        zero_division=0,
    )

    legitimate_precision = precision_score(
        y_true,
        y_pred,
        pos_label=LEGITIMATE_LABEL,
        zero_division=0,
    )
    legitimate_recall = recall_score(
        y_true,
        y_pred,
        pos_label=LEGITIMATE_LABEL,
        zero_division=0,
    )
    legitimate_f1 = f1_score(
        y_true,
        y_pred,
        pos_label=LEGITIMATE_LABEL,
        zero_division=0,
    )

    results = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "phishing_precision": float(phishing_precision),
        "phishing_recall": float(phishing_recall),
        "phishing_f1": float(phishing_f1),
        "legitimate_precision": float(legitimate_precision),
        "legitimate_recall": float(legitimate_recall),
        "legitimate_f1": float(legitimate_f1),
        "macro_f1": float(
            f1_score(y_true, y_pred, average="macro", zero_division=0)
        ),
        # Rows = actual class; columns = predicted class.
        # Order: phishing (0), legitimate (1).
        "confusion_matrix": confusion_matrix(
            y_true,
            y_pred,
            labels=[PHISHING_LABEL, LEGITIMATE_LABEL],
        ).tolist(),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=[PHISHING_LABEL, LEGITIMATE_LABEL],
            target_names=["phishing", "legitimate"],
            output_dict=True,
            zero_division=0,
        ),
    }

    if phishing_scores is not None:
        phishing_scores = np.asarray(phishing_scores, dtype=float)

        if phishing_scores.ndim != 1:
            raise ValueError("phishing_scores must be one-dimensional.")

        if len(phishing_scores) != len(y_true):
            raise ValueError(
                "phishing_scores must have the same length as y_true."
            )

        if not np.isfinite(phishing_scores).all():
            raise ValueError("phishing_scores contain NaN or infinite values.")

        binary_phishing_labels = (y_true == PHISHING_LABEL).astype(int)

        if len(np.unique(binary_phishing_labels)) == 2:
            results["roc_auc"] = float(
                roc_auc_score(binary_phishing_labels, phishing_scores)
            )
            results["pr_auc"] = float(
                average_precision_score(
                    binary_phishing_labels,
                    phishing_scores,
                )
            )
        else:
            # Ranking metrics require examples from both classes.
            results["roc_auc"] = None
            results["pr_auc"] = None

    return results


def print_url_metrics(results: dict) -> None:
    """Print a readable summary of URL classifier metrics."""

    print("\n=== URL Classification Evaluation ===")
    print(f"Accuracy:             {results['accuracy']:.4f}")
    print(f"Phishing precision:   {results['phishing_precision']:.4f}")
    print(f"Phishing recall:      {results['phishing_recall']:.4f}")
    print(f"Phishing F1:          {results['phishing_f1']:.4f}")
    print(f"Legitimate precision: {results['legitimate_precision']:.4f}")
    print(f"Legitimate recall:    {results['legitimate_recall']:.4f}")
    print(f"Legitimate F1:        {results['legitimate_f1']:.4f}")
    print(f"Macro F1:             {results['macro_f1']:.4f}")

    if "roc_auc" in results:
        roc_auc = results["roc_auc"]
        pr_auc = results["pr_auc"]
        print(
            "ROC-AUC:              "
            + (f"{roc_auc:.4f}" if roc_auc is not None else "undefined")
        )
        print(
            "PR-AUC (AP):          "
            + (f"{pr_auc:.4f}" if pr_auc is not None else "undefined")
        )

    print("\nConfusion matrix (actual rows, predicted columns):")
    print("                    Predicted phishing | Predicted legitimate")
    print(
        f"Actual phishing:    {results['confusion_matrix'][0][0]:>18} |"
        f" {results['confusion_matrix'][0][1]:>19}"
    )
    print(
        f"Actual legitimate:  {results['confusion_matrix'][1][0]:>18} |"
        f" {results['confusion_matrix'][1][1]:>19}"
    )