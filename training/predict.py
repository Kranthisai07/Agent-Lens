"""Phase 4.9 — inference helper for the trained tool policy.

Run: python training/predict.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np

MODELS_DIR = ROOT / "models"
CONFIDENCE_THRESHOLD = 0.7

_model = None
_vec = None
_meta = None


def _load():
    global _model, _vec, _meta
    if _model is None:
        for f in ("policy_model.pkl", "tfidf_vectorizer.pkl", "label_classes.json"):
            if not (MODELS_DIR / f).exists():
                raise SystemExit(f"Missing models/{f}. Run training/train.py first.")
        _model = joblib.load(MODELS_DIR / "policy_model.pkl")
        _vec = joblib.load(MODELS_DIR / "tfidf_vectorizer.pkl")
        _meta = json.loads(
            (MODELS_DIR / "label_classes.json").read_text(encoding="utf-8"))
    return _model, _vec, _meta


def _class_probabilities(model, X):
    """Probabilities over classes. Falls back to a softmax over
    decision_function for models without predict_proba (e.g. plain SVC)."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[0]
    scores = np.atleast_2d(model.decision_function(X))[0]
    shifted = np.exp(scores - scores.max())
    return shifted / shifted.sum()


def predict_tool(query: str) -> dict:
    """Predict which tool to use for a query.

    Returns {"tool": <tool name>, "confidence": <float 0-1>}.
    """
    model, vec, _ = _load()
    probs = _class_probabilities(model, vec.transform([str(query)]))
    idx = int(np.argmax(probs))
    return {"tool": str(model.classes_[idx]), "confidence": float(probs[idx])}


# (query, is_known_hard_case)
TEST_QUERIES = [
    ("What is 25 multiplied by 48?", False),
    ("Who invented the telephone?", False),
    ("Summarize the sales data", False),
    ("Calculate the average revenue in the dataset", True),
    ("How many records are in the dataset?", True),
    ("What is the population of Mexico?", True),
    ("Define photosynthesis", True),
    ("What is 15% of 200?", False),
]


def main():
    _, _, meta = _load()
    print("=" * 84)
    print(f"AgentLens - predict_tool()   [model: {meta['best_model']}]")
    print("=" * 84)
    print(f"{'query':46} {'predicted':17} {'conf':>6}  flags")
    print("-" * 84)
    uncertain = 0
    for query, hard in TEST_QUERIES:
        result = predict_tool(query)
        flags = []
        if result["confidence"] < CONFIDENCE_THRESHOLD:
            flags.append("UNCERTAIN")
            uncertain += 1
        if hard:
            flags.append("hard-case")
        print(f"{query[:44]:46} {result['tool']:17} "
              f"{result['confidence']:6.3f}  {' '.join(flags)}")
    print("-" * 84)
    print(f"{uncertain}/{len(TEST_QUERIES)} predictions below confidence "
          f"threshold {CONFIDENCE_THRESHOLD}")


if __name__ == "__main__":
    main()
