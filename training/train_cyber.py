"""Phase 9 — train the tool policy on CYBER trajectories.

Separate from training/train.py (which stays for the general 3-tool dataset).
Trains on tool_ground_truth over the 11-tool cyber task, with a stratified
split on difficulty so hard queries appear in both train and test, and reports
a per-difficulty (easy vs hard) accuracy breakdown per model.

Run: python training/train_cyber.py
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

LOGS_PATH = ROOT / "data" / "trajectories" / "cyber_logs.csv"
MODELS_DIR = ROOT / "models"
COMPARISON_PATH = ROOT / "data" / "cyber_model_comparison.csv"
SPLIT_PATH = ROOT / "data" / "cyber_test_index.json"  # shared with evaluate_cyber.py

TEXT_COL = "prompt"
LABEL_COL = "tool_ground_truth"
BASELINE_COL = "tool_predicted"
RANDOM_STATE = 42
TEST_SIZE = 0.2


def load_data():
    if not LOGS_PATH.exists():
        raise SystemExit(f"No cyber trajectories at {LOGS_PATH}. Run agents/cyber_agent.py first.")
    df = pd.read_csv(LOGS_PATH).dropna(subset=[TEXT_COL, LABEL_COL])
    df[TEXT_COL] = df[TEXT_COL].astype(str)
    return df.reset_index(drop=True)


def build_split(df):
    """Stratified 80/20 split on DIFFICULTY so easy and hard are both represented
    in train and test. Returns (train_df, test_df). Persists the test row ids so
    evaluate_cyber.py scores exactly the same test set."""
    train_df, test_df = train_test_split(
        df, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=df["difficulty"])
    SPLIT_PATH.write_text(json.dumps(sorted(test_df.index.tolist())), encoding="utf-8")
    return train_df, test_df


def build_models():
    return {
        "LogReg": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "SVM": SVC(kernel="linear", random_state=RANDOM_STATE),
        "MLP": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE),
    }


def main():
    df = load_data()
    labels = sorted(df[LABEL_COL].unique())

    print("=" * 68)
    print("AgentLens - Phase 9: Cyber Tool Policy Training")
    print("=" * 68)
    print(f"Trajectories: {len(df)}  |  tools: {len(labels)}  |  {LOGS_PATH.relative_to(ROOT)}")
    print("Difficulty mix:", dict(df["difficulty"].value_counts()))

    train_df, test_df = build_split(df)
    print(f"Split: {len(train_df)} train / {len(test_df)} test "
          f"(stratified on difficulty, random_state={RANDOM_STATE})")
    print("  test difficulty mix:", dict(test_df["difficulty"].value_counts()))

    vec = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    X_train = vec.fit_transform(train_df[TEXT_COL])
    X_test = vec.transform(test_df[TEXT_COL])
    y_train, y_test = train_df[LABEL_COL], test_df[LABEL_COL]
    print(f"TF-IDF (1,2)-gram, max_features=5000 -> {X_train.shape[1]} features")

    test_easy = test_df["difficulty"] == "easy"
    test_hard = test_df["difficulty"] == "hard"

    rows, fitted = [], {}
    print("\n--- Model comparison ---")
    for name, model in build_models().items():
        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        train_ms = (time.perf_counter() - t0) * 1000
        pred = model.predict(X_test)
        acc = accuracy_score(y_test, pred)
        f1m = f1_score(y_test, pred, average="macro")
        easy_acc = accuracy_score(y_test[test_easy], pred[test_easy.values])
        hard_acc = accuracy_score(y_test[test_hard], pred[test_hard.values])
        fitted[name] = model
        rows.append({"model": name, "accuracy": round(acc, 4), "f1_macro": round(f1m, 4),
                     "easy_acc": round(easy_acc, 4), "hard_acc": round(hard_acc, 4),
                     "train_time_ms": round(train_ms, 1)})
        print(f"  {name:13} acc={acc:.4f}  f1={f1m:.4f}  "
              f"easy={easy_acc:.4f}  hard={hard_acc:.4f}  ({train_ms:.0f} ms)")

    comparison = pd.DataFrame(rows).sort_values("f1_macro", ascending=False)
    COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(COMPARISON_PATH, index=False)
    print(f"\nComparison -> {COMPARISON_PATH.relative_to(ROOT)}")
    print(comparison.to_string(index=False))

    best_name = comparison.iloc[0]["model"]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted[best_name], MODELS_DIR / "cyber_policy_model.pkl")
    joblib.dump(vec, MODELS_DIR / "cyber_tfidf_vectorizer.pkl")
    (MODELS_DIR / "cyber_label_classes.json").write_text(
        json.dumps({"classes": labels, "best_model": best_name,
                    "random_state": RANDOM_STATE, "test_size": TEST_SIZE}, indent=2),
        encoding="utf-8")
    print(f"\nBest by macro F1: {best_name} -> models/cyber_policy_model.pkl "
          f"(+ vectorizer, label classes)")


if __name__ == "__main__":
    main()
