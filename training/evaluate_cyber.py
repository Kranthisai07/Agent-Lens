"""Phase 9 — evaluate the cyber policy and print the paper's results table.

Loads the saved cyber model + vectorizer, reuses train_cyber.py's exact test
split, renders the confusion-matrix figure, and prints the headline
Method x {Overall, Hard} x Latency table comparing the LLM baseline against all
four trained classifiers.

Run: python training/evaluate_cyber.py
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "training"))

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

from train_cyber import (BASELINE_COL, LABEL_COL, RANDOM_STATE, SPLIT_PATH,
                         TEXT_COL, load_data)

MODELS_DIR = ROOT / "models"
CM_PATH = ROOT / "data" / "cyber_confusion_matrix.png"
LATENCY_PATH = ROOT / "data" / "llm_latency.json"
CLF_LATENCY_MS = 0.3          # measured for the general model (evaluate.py); same pipeline
LLM_MS_FALLBACK = 209.0       # median from data/llm_latency.json


def _llm_ms():
    if LATENCY_PATH.exists():
        return json.loads(LATENCY_PATH.read_text(encoding="utf-8")).get("median_ms", LLM_MS_FALLBACK)
    return LLM_MS_FALLBACK


def _models():
    return {
        "LogReg": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "SVM": SVC(kernel="linear", random_state=RANDOM_STATE),
        "MLP": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE),
    }


def main():
    for f in ("cyber_policy_model.pkl", "cyber_tfidf_vectorizer.pkl", "cyber_label_classes.json"):
        if not (MODELS_DIR / f).exists():
            raise SystemExit(f"Missing models/{f}. Run training/train_cyber.py first.")

    best = joblib.load(MODELS_DIR / "cyber_policy_model.pkl")
    vec = joblib.load(MODELS_DIR / "cyber_tfidf_vectorizer.pkl")
    meta = json.loads((MODELS_DIR / "cyber_label_classes.json").read_text(encoding="utf-8"))
    labels = meta["classes"]

    df = load_data()
    test_idx = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    test_df = df.loc[test_idx]
    train_df = df.drop(index=test_idx)

    X_train = vec.transform(train_df[TEXT_COL])
    X_test = vec.transform(test_df[TEXT_COL])
    y_train, y_test = train_df[LABEL_COL], test_df[LABEL_COL]
    hard = test_df["difficulty"] == "hard"

    print("=" * 68)
    print("AgentLens - Phase 9: Cyber Evaluation")
    print("=" * 68)
    print(f"Best model: {meta['best_model']}   test set: {len(test_df)} "
          f"(hard: {hard.sum()})")

    y_pred = best.predict(X_test)
    print("\n--- Classification report (best model) ---")
    print(classification_report(y_test, y_pred, labels=labels, digits=3, zero_division=0))

    # ---- confusion matrix figure ----
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    plt.figure(figsize=(11, 9))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels,
                yticklabels=labels, cbar=True, square=True, linewidths=0.5,
                linecolor="white", annot_kws={"size": 8})
    plt.xlabel("Predicted Tool")
    plt.ylabel("Actual Tool")
    plt.title(f"AgentLens Cyber - Tool Prediction Confusion Matrix ({meta['best_model']})")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    CM_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(CM_PATH, dpi=150)
    plt.close()
    print(f"Confusion matrix -> {CM_PATH.relative_to(ROOT)}")

    # ---- LLM baseline on the same test rows ----
    llm_overall = accuracy_score(y_test, test_df[BASELINE_COL])
    llm_hard = accuracy_score(y_test[hard], test_df.loc[hard, BASELINE_COL])
    llm_ms = _llm_ms()

    # ---- all four classifiers on the same split ----
    clf_rows = []
    for name, model in _models().items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        clf_rows.append((name, accuracy_score(y_test, pred),
                         accuracy_score(y_test[hard], pred[hard.values])))

    # ---- the paper's results table ----
    print("\n" + "=" * 60)
    print("PAPER RESULTS TABLE")
    print("=" * 60)
    print(f"{'Method':15}| {'Overall Acc':>11} | {'Hard Acc':>8} | {'Latency':>8}")
    print(f"{'-'*15}|{'-'*13}|{'-'*10}|{'-'*9}")
    print(f"{'LLM Baseline':15}| {llm_overall*100:>10.1f}% | {llm_hard*100:>7.1f}% | {llm_ms:>6.0f}ms")
    for name, overall, h in clf_rows:
        print(f"{name:15}| {overall*100:>10.1f}% | {h*100:>7.1f}% | {CLF_LATENCY_MS:>6.1f}ms")

    print(f"\nBest classifier ({meta['best_model']}) vs LLM: "
          f"overall {max(c[1] for c in clf_rows)*100:.1f}% vs {llm_overall*100:.1f}%, "
          f"hard {max(c[2] for c in clf_rows)*100:.1f}% vs {llm_hard*100:.1f}%")


if __name__ == "__main__":
    main()
