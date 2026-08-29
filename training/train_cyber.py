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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

LOGS_PATH = ROOT / "data" / "trajectories" / "cyber_logs.csv"
MODELS_DIR = ROOT / "models"
COMPARISON_PATH = ROOT / "data" / "cyber_model_comparison.csv"
SPLIT_PATH = ROOT / "data" / "cyber_test_index.json"  # shared with evaluate_cyber.py
CV_RESULTS_PATH = ROOT / "data" / "cyber_cv_results.csv"
CV_CM_PATH = ROOT / "data" / "cyber_confusion_matrix_cv.png"

TEXT_COL = "prompt"
LABEL_COL = "tool_ground_truth"
BASELINE_COL = "tool_predicted"
DIFF_COL = "difficulty"
RANDOM_STATE = 42
TEST_SIZE = 0.2
N_SPLITS = 5


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


def cross_validate(df, labels):
    """5-fold stratified CV on the full dataset, stratified on the combined
    tool+difficulty label so every (tool, difficulty) cell is represented in
    each fold. Vectorizer is fit inside each fold (no leakage). Returns the CV
    summary DataFrame and the winning model's aggregated out-of-fold predictions.
    """
    combined = df[LABEL_COL].astype(str) + "_" + df[DIFF_COL].astype(str)
    hard_mask = (df[DIFF_COL] == "hard").to_numpy()
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    names = list(build_models())
    per_fold = {n: {"overall": [], "hard": [], "f1": []} for n in names}
    oof_pred = {n: np.empty(len(df), dtype=object) for n in names}

    print(f"\n--- {N_SPLITS}-fold cross-validation "
          f"(stratified on tool+difficulty) ---")
    for k, (tr, te) in enumerate(skf.split(df[TEXT_COL], combined), 1):
        vec = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
        X_tr = vec.fit_transform(df.iloc[tr][TEXT_COL])
        X_te = vec.transform(df.iloc[te][TEXT_COL])
        y_tr, y_te = df.iloc[tr][LABEL_COL], df.iloc[te][LABEL_COL]
        te_hard = hard_mask[te]
        for name, model in build_models().items():   # fresh models each fold
            model.fit(X_tr, y_tr)
            pred = model.predict(X_te)
            oof_pred[name][te] = pred
            per_fold[name]["overall"].append(accuracy_score(y_te, pred))
            per_fold[name]["f1"].append(f1_score(y_te, pred, average="macro"))
            per_fold[name]["hard"].append(accuracy_score(y_te[te_hard], pred[te_hard]))
        print(f"  fold {k}/{N_SPLITS}  "
              + "  ".join(f"{n}={per_fold[n]['overall'][-1]:.3f}" for n in names))

    rows = []
    for name in names:
        o, h, f = (np.array(per_fold[name][k]) for k in ("overall", "hard", "f1"))
        rows.append({
            "model": name,
            "overall_acc_mean": round(o.mean(), 4), "overall_acc_std": round(o.std(), 4),
            "hard_acc_mean": round(h.mean(), 4), "hard_acc_std": round(h.std(), 4),
            "f1_macro_mean": round(f.mean(), 4), "f1_macro_std": round(f.std(), 4),
        })
    cv = pd.DataFrame(rows).sort_values("f1_macro_mean", ascending=False)
    cv.to_csv(CV_RESULTS_PATH, index=False)
    print(f"\nCV results -> {CV_RESULTS_PATH.relative_to(ROOT)}")
    print(cv.to_string(index=False))

    # ---- paper table with confidence intervals ----
    llm_overall = (df[BASELINE_COL] == df[LABEL_COL]).mean()
    llm_hard = (df.loc[hard_mask, BASELINE_COL] == df.loc[hard_mask, LABEL_COL]).mean()
    print("\n" + "=" * 66)
    print("PAPER RESULTS TABLE (5-fold CV, mean +/- std)")
    print("=" * 66)
    print(f"{'Method':13}| {'Overall Acc':>16} | {'Hard Acc':>16} | {'Latency':>7}")
    print(f"{'-'*13}|{'-'*18}|{'-'*18}|{'-'*8}")
    print(f"{'LLM Baseline':13}| {llm_overall*100:>7.1f}% (no CV)  | "
          f"{llm_hard*100:>7.1f}% (no CV)  | {'209ms':>7}")
    for _, r in cv.iterrows():  # f1-sorted order
        o = f"{r['overall_acc_mean']*100:.1f}% +/- {r['overall_acc_std']*100:.1f}%"
        h = f"{r['hard_acc_mean']*100:.1f}% +/- {r['hard_acc_std']*100:.1f}%"
        print(f"{r['model']:13}| {o:>16} | {h:>16} | {'0.3ms':>7}")

    best = cv.iloc[0]["model"]
    return cv, best, oof_pred[best]


def _cv_confusion(df, labels, best_name, oof):
    """Aggregated out-of-fold confusion matrix — every query predicted once."""
    cm = confusion_matrix(df[LABEL_COL], oof, labels=labels)
    plt.figure(figsize=(11, 9))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels,
                yticklabels=labels, cbar=True, square=True, linewidths=0.5,
                linecolor="white", annot_kws={"size": 8})
    plt.xlabel("Predicted Tool")
    plt.ylabel("Actual Tool")
    plt.title(f"AgentLens Cyber - Tool Prediction Confusion Matrix "
              f"(5-fold CV, {best_name})")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(CV_CM_PATH, dpi=150)
    plt.close()
    acc = (df[LABEL_COL].to_numpy() == oof).mean()
    print(f"\nAggregated OOF confusion matrix -> {CV_CM_PATH.relative_to(ROOT)}  "
          f"(pooled acc {acc:.1%}, n={len(df)})")


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

    # ---- cross-validation with confidence intervals (the honest estimate) ----
    cv, cv_best, oof = cross_validate(df, labels)
    _cv_confusion(df, labels, cv_best, oof)


if __name__ == "__main__":
    main()
