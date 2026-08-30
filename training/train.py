"""Phase 4 — train the tool-selection policy on collected trajectories.

Trains on `tool_ground_truth` (the true label from queries.json), NOT on
`tool_predicted` (the LLM's choice). Training on the LLM's choice would
distil its error rate and cap the classifier at the baseline it is meant
to replace.

Run: python training/train.py
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

LOGS_PATH = ROOT / "data" / "trajectories" / "logs.csv"
MODELS_DIR = ROOT / "models"
COMPARISON_PATH = ROOT / "data" / "model_comparison.csv"

TEXT_COL = "prompt"
LABEL_COL = "tool_ground_truth"
BASELINE_COL = "tool_predicted"
RANDOM_STATE = 42
TEST_SIZE = 0.2


def load_data():
    """Load trajectories. Returns the dataframe with required columns validated."""
    if not LOGS_PATH.exists():
        raise SystemExit(f"No trajectories at {LOGS_PATH}. Run agents/crew_agent.py first.")
    df = pd.read_csv(LOGS_PATH)
    missing = {TEXT_COL, LABEL_COL, BASELINE_COL} - set(df.columns)
    if missing:
        raise SystemExit(
            f"{LOGS_PATH} is missing columns {sorted(missing)}. "
            "It may predate the ground-truth schema (see logs_schema_v1.csv)."
        )
    df = df.dropna(subset=[TEXT_COL, LABEL_COL])
    df[TEXT_COL] = df[TEXT_COL].astype(str)
    return df


def build_split(df):
    """Deterministic stratified 80/20 split. Shared with evaluate.py so both
    scripts see byte-identical train/test sets."""
    return train_test_split(
        df,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=df[LABEL_COL],
    )


def build_models():
    return {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "SVM(linear)": SVC(kernel="linear", random_state=RANDOM_STATE),
        "MLP(64,32)": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500,
                                    random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE),
    }


def main():
    df = load_data()
    labels = sorted(df[LABEL_COL].unique())

    print("=" * 68)
    print("AgentLens - Phase 4: Tool Policy Training")
    print("=" * 68)
    print(f"Trajectories: {len(df)}  from {LOGS_PATH.relative_to(ROOT)}")
    print(f"Runs included: {', '.join(map(str, df['run_id'].unique()))}"
          if "run_id" in df.columns else "")

    print("\n--- Class distribution (tool_ground_truth) ---")
    counts = df[LABEL_COL].value_counts()
    for tool in labels:
        n = counts[tool]
        print(f"  {tool:18} {n:4}  ({n/len(df):6.1%})  {'#' * int(40 * n / len(df))}")
    imbalance = counts.max() / counts.min()
    print(f"  imbalance ratio (max/min): {imbalance:.2f}x"
          f"{'  - balanced' if imbalance < 1.5 else '  - WARNING: imbalanced'}")

    train_df, test_df = build_split(df)
    print(f"\nSplit: {len(train_df)} train / {len(test_df)} test "
          f"(stratified, random_state={RANDOM_STATE})")

    vec = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    X_train = vec.fit_transform(train_df[TEXT_COL])
    X_test = vec.transform(test_df[TEXT_COL])
    y_train, y_test = train_df[LABEL_COL], test_df[LABEL_COL]
    print(f"TF-IDF: ngram_range=(1,2), max_features=5000 -> {X_train.shape[1]} features")

    rows, fitted = [], {}
    print("\n--- Model comparison ---")
    for name, model in build_models().items():
        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        train_ms = (time.perf_counter() - t0) * 1000
        pred = model.predict(X_test)
        acc = accuracy_score(y_test, pred)
        f1m = f1_score(y_test, pred, average="macro")
        per_class = f1_score(y_test, pred, average=None, labels=labels)
        fitted[name] = model
        row = {"model": name, "accuracy": round(acc, 4), "f1_macro": round(f1m, 4),
               "train_time_ms": round(train_ms, 1)}
        for tool, f1c in zip(labels, per_class):
            row[f"f1_{tool}"] = round(f1c, 4)
        rows.append(row)

        print(f"\n  {name}")
        print(f"    accuracy      : {acc:.4f}")
        print(f"    F1 (macro)    : {f1m:.4f}")
        print(f"    F1 (per class): " +
              "  ".join(f"{t}={f:.4f}" for t, f in zip(labels, per_class)))
        print(f"    train time    : {train_ms:.1f} ms")

    comparison = pd.DataFrame(rows).sort_values("f1_macro", ascending=False)
    COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(COMPARISON_PATH, index=False)

    print("\n--- Comparison table (also written to data/model_comparison.csv) ---")
    print(comparison.to_string(index=False))

    best_name = comparison.iloc[0]["model"]
    best_model = fitted[best_name]
    print(f"\nBest model by macro F1: {best_name}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODELS_DIR / "policy_model.pkl")
    joblib.dump(vec, MODELS_DIR / "tfidf_vectorizer.pkl")
    (MODELS_DIR / "label_classes.json").write_text(
        json.dumps({"classes": labels, "best_model": best_name,
                    "random_state": RANDOM_STATE, "test_size": TEST_SIZE}, indent=2),
        encoding="utf-8")

    print(f"Saved models/policy_model.pkl, models/tfidf_vectorizer.pkl, "
          f"models/label_classes.json")


if __name__ == "__main__":
    main()
