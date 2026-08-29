"""Phase 5 — evaluate the saved policy against the LLM baseline.

Reuses train.py's split helper so the test set is byte-identical to the
one the model was held out from.

Run: python training/evaluate.py
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
import seaborn as sns
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score)

from train import BASELINE_COL, LABEL_COL, TEXT_COL, build_split, load_data

MODELS_DIR = ROOT / "models"
CM_PATH = ROOT / "data" / "confusion_matrix.png"
LATENCY_PATH = ROOT / "data" / "llm_latency.json"

# Used only if data/llm_latency.json is absent.
LLM_MS_PER_QUERY_FALLBACK = 2500.0


def llm_latency_ms():
    """Measured LLM routing latency if available, else a documented assumption.

    Returns (mean_ms, median_ms, note). The distribution is heavily right-skewed
    by cold starts, so the median is the fairer per-query figure and the mean is
    the fairer figure for routing a whole batch.
    """
    if LATENCY_PATH.exists():
        d = json.loads(LATENCY_PATH.read_text(encoding="utf-8"))
        note = (f"measured n={d['n']}, median {d['median_ms']:.0f} ms, "
                f"min {d['min_ms']:.0f} / max {d['max_ms']:.0f} ms")
        return d["mean_ms"], d["median_ms"], note
    return (LLM_MS_PER_QUERY_FALLBACK, LLM_MS_PER_QUERY_FALLBACK,
            "ASSUMED ~2-3 s/query, NOT measured")


def main():
    for f in ("policy_model.pkl", "tfidf_vectorizer.pkl", "label_classes.json"):
        if not (MODELS_DIR / f).exists():
            raise SystemExit(f"Missing models/{f}. Run training/train.py first.")

    model = joblib.load(MODELS_DIR / "policy_model.pkl")
    vec = joblib.load(MODELS_DIR / "tfidf_vectorizer.pkl")
    meta = json.loads((MODELS_DIR / "label_classes.json").read_text(encoding="utf-8"))
    labels = meta["classes"]

    df = load_data()
    _, test_df = build_split(df)
    X_test = vec.transform(test_df[TEXT_COL])
    y_test = test_df[LABEL_COL]
    y_pred = model.predict(X_test)

    print("=" * 68)
    print("AgentLens - Phase 5: Evaluation")
    print("=" * 68)
    print(f"Model: {meta['best_model']}   test set: {len(test_df)} queries")

    print("\n--- Classification report ---")
    print(classification_report(y_test, y_pred, labels=labels, digits=4,
                                zero_division=0))

    clf_acc = accuracy_score(y_test, y_pred)
    clf_f1 = f1_score(y_test, y_pred, average="macro")
    print(f"Accuracy : {clf_acc:.4f}")
    print(f"F1 macro : {clf_f1:.4f}")

    # ---- confusion matrix heatmap ----
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels, yticklabels=labels, cbar=True,
                square=True, linewidths=0.5, linecolor="white")
    plt.xlabel("Predicted Tool")
    plt.ylabel("Actual Tool")
    plt.title("AgentLens - Tool Prediction Confusion Matrix")
    plt.tight_layout()
    CM_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(CM_PATH, dpi=150)
    plt.close()
    print(f"\nConfusion matrix saved -> {CM_PATH.relative_to(ROOT)}")
    print("Matrix (rows=actual, cols=predicted):")
    header = " " * 20 + "".join(f"{lab:>18}" for lab in labels)
    print(header)
    for lab, row in zip(labels, cm):
        print(f"    {lab:16}" + "".join(f"{v:>18}" for v in row))

    # ---- baselines ----
    n_tools = len(labels)
    random_acc = 1 / n_tools
    majority_acc = y_test.value_counts().iloc[0] / len(y_test)
    llm_test_acc = accuracy_score(y_test, test_df[BASELINE_COL])
    llm_full_acc = (df[BASELINE_COL] == df[LABEL_COL]).mean()

    print("\n--- Baseline comparison ---")
    print(f"  Random guessing (1/{n_tools})       : {random_acc:.4f}")
    print(f"  Majority class                  : {majority_acc:.4f}")
    print(f"  LLM (llama3.2:3b), full set     : {llm_full_acc:.4f}")
    print(f"  LLM (llama3.2:3b), test split   : {llm_test_acc:.4f}")
    print(f"  Trained classifier, test split  : {clf_acc:.4f}")
    gain = (clf_acc - llm_test_acc) * 100
    print(f"\n  Improvement over LLM baseline   : {gain:+.2f} percentage points")
    print(f"  Improvement over random         : {(clf_acc-random_acc)*100:+.2f} pp")
    denom = max(1 - llm_test_acc, 1e-9)
    print(f"  Relative error reduction        : {((1-llm_test_acc)-(1-clf_acc))/denom:.1%}")

    # ---- latency ----
    print("\n--- Latency ---")
    model.predict(vec.transform(["warmup"]))
    sample = test_df[TEXT_COL].tolist()
    sample = (sample * (100 // len(sample) + 1))[:100]

    t0 = time.perf_counter()
    for q in sample:
        model.predict(vec.transform([q]))
    clf_ms = (time.perf_counter() - t0) / 100 * 1000

    t0 = time.perf_counter()
    model.predict(vec.transform(sample))
    batch_ms = (time.perf_counter() - t0) / 100 * 1000

    llm_ms, llm_median_ms, llm_note = llm_latency_ms()
    print(f"  Classifier (per query, 100 runs): {clf_ms:.3f} ms")
    print(f"  Classifier (batched, per query) : {batch_ms:.3f} ms")
    print(f"  LLM routing, mean               : {llm_ms:.1f} ms")
    print(f"  LLM routing, median             : {llm_median_ms:.1f} ms")
    print(f"    [{llm_note}]")
    print(f"  Speedup (vs LLM median)         : {llm_median_ms/clf_ms:,.0f}x")
    print(f"  Speedup (vs LLM mean)           : {llm_ms/clf_ms:,.0f}x")
    print(f"  Route all 518: classifier {clf_ms*518/1000:.2f} s "
          f"vs LLM {llm_ms*518/1000:.0f} s")

    print("\n--- Summary for paper ---")
    for k, v in [("classifier accuracy", f"{clf_acc:.4f}"),
                 ("classifier macro F1", f"{clf_f1:.4f}"),
                 ("LLM baseline accuracy (test)", f"{llm_test_acc:.4f}"),
                 ("gain (percentage points)", f"{gain:+.2f}"),
                 ("classifier ms/query", f"{clf_ms:.3f}"),
                 ("LLM ms/query (mean)", f"{llm_ms:.0f}"),
                 ("LLM ms/query (median)", f"{llm_median_ms:.0f}"),
                 ("speedup (vs median)", f"{llm_median_ms/clf_ms:,.0f}x")]:
        print(f"  {k:32} {v:>12}")


if __name__ == "__main__":
    main()
