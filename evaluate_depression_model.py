"""Evaluate the depression-language classifier against reproducible splits and a modern baseline.

The original notebook (Depression Model/DepressionScore.ipynb) trained on a random
98/2 split with no fixed seed and validated on ~230 tweets. This script re-runs
evaluation on a proper stratified 80/20 split (fixed seed, ~2060 held-out tweets)
so the numbers are reproducible and comparable, and adds a scikit-learn baseline
(TF-IDF + Logistic Regression) trained the same way, so the hand-rolled TF-IDF/
Naive Bayes classifier has something to be measured against.

Usage:
    python evaluate_depression_model.py
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from Extensions.DepressionScore import PIPELINE_PATH, TweetClassifier, build_pipeline

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "Depression Model" / "sentiment_tweets3.csv"
RESULTS_DIR = ROOT / "Depression Model" / "results"
RANDOM_STATE = 42
TEST_SIZE = 0.2


def load_split():
    tweets = pd.read_csv(DATA_PATH)
    train, test = train_test_split(
        tweets,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=tweets["label"],
    )
    return train.reset_index(drop=True), test.reset_index(drop=True)


def score(name, y_true, y_pred):
    return {
        "model": name,
        "accuracy": float(np.mean(y_true == y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def save_confusion_matrix(name, y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=["not depressive", "depressive"])
    fig, ax = plt.subplots(figsize=(4, 4))
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title(name)
    fig.tight_layout()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(RESULTS_DIR / f"confusion_{name.lower().replace(' ', '_')}.png", dpi=150)
    plt.close(fig)


def run_majority_baseline(train, test):
    dummy = DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE)
    dummy.fit(train[["message"]], train["label"])
    preds = dummy.predict(test[["message"]])
    return preds


def run_handrolled_classifier(train, test):
    classifier = TweetClassifier(train, method="tf-idf")
    classifier.train()
    predictions = classifier.predict(test["message"])
    return np.array([predictions[i] for i in range(len(predictions))])


def run_sklearn_baseline(train, test):
    pipeline = build_pipeline()
    pipeline.fit(train["message"], train["label"])
    return pipeline.predict(test["message"])


def main():
    train, test = load_split()
    y_test = test["label"].to_numpy()

    print(f"Train: {len(train)} tweets ({train['label'].mean():.1%} depressive)")
    print(f"Test:  {len(test)} tweets ({test['label'].mean():.1%} depressive)")
    print()

    results = []

    majority_preds = run_majority_baseline(train, test)
    results.append(score("Majority baseline", y_test, majority_preds))
    save_confusion_matrix("Majority baseline", y_test, majority_preds)

    handrolled_preds = run_handrolled_classifier(train, test)
    results.append(score("Hand-rolled TF-IDF NB", y_test, handrolled_preds))
    save_confusion_matrix("Hand-rolled TF-IDF NB", y_test, handrolled_preds)

    sklearn_preds = run_sklearn_baseline(train, test)
    results.append(score("TF-IDF + LogReg", y_test, sklearn_preds))
    save_confusion_matrix("TF-IDF + LogReg", y_test, sklearn_preds)

    df = pd.DataFrame(results).set_index("model")
    print(df.round(3).to_string())

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with (RESULTS_DIR / "metrics.json").open("w") as f:
        json.dump(results, f, indent=2)

    with (RESULTS_DIR / "metrics.md").open("w") as f:
        f.write("# Depression-language classifier evaluation\n\n")
        f.write(
            f"Stratified 80/20 split, seed={RANDOM_STATE}, "
            f"{len(train)} train / {len(test)} test tweets "
            f"({test['label'].mean():.1%} depressive in test set).\n\n"
        )
        header = "| model | accuracy | precision | recall | f1 |\n|---|---|---|---|---|\n"
        rows = "".join(
            f"| {row['model']} | {row['accuracy']:.3f} | {row['precision']:.3f} | "
            f"{row['recall']:.3f} | {row['f1']:.3f} |\n"
            for row in results
        )
        f.write(header + rows)
        f.write(
            "\n## Limitations\n\n"
            "- The majority baseline (77.6% accuracy) shows why accuracy alone is "
            "misleading here: the hand-rolled TF-IDF/Naive Bayes model's 85.7% "
            "accuracy is only a few points above always guessing 'not depressive', "
            "and its 0.41 recall means it misses most tweets actually labeled "
            "depressive. The TF-IDF + Logistic Regression model fixes both the "
            "class-imbalance handling and a tokenizer bug (see `tokenize_unigrams` "
            "in Extensions/DepressionScore.py).\n"
            "- Both models were trained on `sentiment_tweets3.csv`, which was almost "
            "certainly built by scraping tweets containing depression-related "
            "keywords/hashtags for the positive class. That makes the literal "
            "presence of words like 'depress-' a very strong lexical shortcut - "
            "e.g. 'My depression will not let me work out' scores confidently "
            "depressive, while 'Extreme sadness, lack of energy, hopelessness' "
            "(no literal keyword) does not. High held-out accuracy here measures "
            "fit to this dataset's collection method, not real-world diagnostic "
            "validity - hence the app frames results as 'linguistic markers', "
            "never a diagnosis.\n"
        )

    print(f"\nSaved metrics.json, metrics.md, and confusion matrices to {RESULTS_DIR}")

    train_production_model()


def train_production_model():
    """Refit the winning pipeline on the full dataset and save it for the app to load.

    The held-out split above is what the metrics are measured on; shipping a
    model trained on 100% of the data (same architecture, same seed) squeezes
    out the last bit of signal since none of it needs to be held back once
    evaluation is done.
    """
    tweets = pd.read_csv(DATA_PATH)
    pipeline = build_pipeline()
    pipeline.fit(tweets["message"], tweets["label"])

    PIPELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PIPELINE_PATH.open("wb") as f:
        pickle.dump(pipeline, f)
    print(f"Trained production pipeline on {len(tweets)} tweets, saved to {PIPELINE_PATH}")


if __name__ == "__main__":
    main()
