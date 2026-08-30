"""Generate paper figures 3 and 4 from committed artifacts.

Fig 3 — per-category LLM accuracy (source: data/trajectories/cyber_logs.csv,
        the same collection run as the paper's Table I and the 79.4% baseline).
Fig 4 — routing latency, LLM vs classifier (source: data/llm_latency.json).

Run: python scripts/make_paper_figures.py
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "paper" / "figures"
LOGS = ROOT / "data" / "trajectories" / "cyber_logs.csv"
LAT = ROOT / "data" / "llm_latency.json"

GREEN = "#2ca02c"
RED = "#d62728"
BLUE = "#1f77b4"
THRESHOLD = 75.0          # acc >= 75% -> green, else red
LLM_BASELINE = 79.4       # overall LLM accuracy (collection run)


def fig3():
    df = pd.read_csv(LOGS)
    cats = ["direct", "ambiguous", "opposite", "multistep", "natural", "trick"]
    acc = {c: (df[df.category == c].eval("tool_predicted == tool_ground_truth")).mean() * 100
           for c in cats}
    # sort ascending so the highest bar sits at the top of a horizontal chart
    items = sorted(acc.items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    colors = [GREEN if v >= THRESHOLD else RED for v in vals]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.barh(names, vals, color=colors, edgecolor="black", linewidth=0.6)
    for b, v in zip(bars, vals):
        ax.text(v + 1.2, b.get_y() + b.get_height() / 2, f"{v:.1f}%",
                va="center", ha="left", fontsize=9)

    ax.axvline(LLM_BASELINE, ls="--", color="black", lw=1.2)
    ax.text(LLM_BASELINE + 0.5, -0.6, f"LLM overall {LLM_BASELINE:.1f}%",
            fontsize=8, color="black", rotation=0, va="top")

    ax.set_xlim(0, 100)
    ax.set_xlabel("Accuracy (%)")
    ax.set_ylabel("Query Category")
    ax.set_title("LLM Tool Selection Accuracy by Query Category")
    handles = [plt.Rectangle((0, 0), 1, 1, color=GREEN),
               plt.Rectangle((0, 0), 1, 1, color=RED)]
    ax.legend(handles, ["accuracy ≥ 75%", "accuracy < 75%"],
              loc="lower right", fontsize=8, frameon=True)
    ax.grid(axis="x", ls=":", alpha=0.4)
    fig.tight_layout()
    out = FIG_DIR / "fig3_category_accuracy.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}  ({dict((k, round(v,1)) for k,v in acc.items())})")


def fig4():
    lat = json.loads(LAT.read_text(encoding="utf-8"))
    labels = ["LLM mean", "LLM median", "Classifier"]
    vals = [round(lat["mean_ms"]), round(lat["median_ms"], 0), 0.3]
    colors = [BLUE, BLUE, GREEN]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(labels, vals, color=colors, edgecolor="black", linewidth=0.6,
                  width=0.6)
    ax.set_yscale("log")
    ax.set_ylim(0.1, 3000)
    for b, v in zip(bars, vals):
        label = f"{v:.1f} ms" if v < 10 else f"{v:.0f} ms"
        ax.text(b.get_x() + b.get_width() / 2, v * 1.25, label,
                ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Latency per query (ms, log scale)")
    ax.set_title("Tool Routing Latency: LLM vs Policy Classifier")
    # 700x annotation between LLM median and classifier
    ax.annotate("700× faster (median)",
                xy=(2, 0.3), xytext=(1.15, 18),
                fontsize=9, fontweight="bold", color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.4))
    ax.grid(axis="y", ls=":", alpha=0.4, which="both")
    fig.tight_layout()
    out = FIG_DIR / "fig4_latency.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out.relative_to(ROOT)}  (mean={vals[0]}ms median={vals[1]}ms clf={vals[2]}ms)")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig3()
    fig4()


if __name__ == "__main__":
    main()
