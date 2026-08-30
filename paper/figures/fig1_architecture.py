"""Generate Figure 1 — AgentLens system architecture.

Three stages left to right: Data Collection -> Policy Learning -> Deployment,
matching paper/agentlens_draft.md section 3.1. Grayscale, academic style, safe
for IEEE two-column black-and-white printing.

Run: python paper/figures/fig1_architecture.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent / "fig1_architecture.png"

EDGE = "black"
FILL = "white"
GRAY = "#d9d9d9"          # emphasis boxes (baseline comparison)
CONTAINER = "#888888"     # stage container outline


def box(ax, cx, cy, w, h, text, fontsize=9, fill=FILL, weight="normal"):
    """Draw a rounded box centred at (cx, cy); return (top, bottom) y edges."""
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.1, edgecolor=EDGE, facecolor=fill, zorder=3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize,
            fontweight=weight, zorder=4, linespacing=1.35)
    return cy + h / 2, cy - h / 2


def v_arrow(ax, cx, y_from, y_to):
    """Downward arrow between two stacked boxes."""
    ax.annotate("", xy=(cx, y_to), xytext=(cx, y_from),
                arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=1.3,
                                shrinkA=0, shrinkB=0), zorder=2)


def h_arrow(ax, x_from, x_to, y, label):
    ax.annotate("", xy=(x_to, y), xytext=(x_from, y),
                arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=1.6,
                                shrinkA=0, shrinkB=0), zorder=2)
    ax.text((x_from + x_to) / 2, y + 0.30, label, ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", style="italic")


def stage_container(ax, x0, x1, y0, y1, title):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False,
                           edgecolor=CONTAINER, linewidth=1.2, linestyle=(0, (5, 4)),
                           zorder=1))
    ax.text((x0 + x1) / 2, y1 - 0.32, title, ha="center", va="center",
            fontsize=11, fontweight="bold")


def main():
    fig, ax = plt.subplots(figsize=(14, 7.4))
    ax.set_xlim(0, 14)
    ax.set_ylim(2, 9.7)
    ax.axis("off")

    # ---- Stage 1: Data Collection ----
    stage_container(ax, 0.45, 4.55, 2.55, 9.15, "1. Data Collection")
    cx1 = 2.5
    a_t, a_b = box(ax, cx1, 8.15, 3.9, 0.66, "LLM Agent  (Llama 3.2 3B)",
                   fontsize=10, weight="bold")
    tools_txt = (
        r"$\bf{Attacker}$: NmapScan, PortScan, SSHConnect, CheckVulnerability" "\n"
        r"$\bf{Defender}$: ReadAuthLog, ListeningPorts, BlockIP," "\n"
        "               CheckFailedLogins, ListProcesses\n"
        r"$\bf{Shared}$: GetSystemInfo, ReadSyslog")
    t_t, t_b = box(ax, cx1, 6.75, 4.0, 1.9, tools_txt, fontsize=7.4)
    w_t, w_b = box(ax, cx1, 4.95, 3.6, 0.66, "logging_tool wrapper", fontsize=9.5)
    l_t, l_b = box(ax, cx1, 3.35, 3.9, 1.0,
                   "Trajectory Logs\n(prompt, tool, difficulty, category)", fontsize=8.5)
    v_arrow(ax, cx1, a_b, t_t)
    v_arrow(ax, cx1, t_b, w_t)
    v_arrow(ax, cx1, w_b, l_t)

    # ---- Stage 2: Policy Learning ----
    stage_container(ax, 5.35, 9.05, 3.95, 9.15, "2. Policy Learning")
    cx2 = 7.2
    f_t, f_b = box(ax, cx2, 7.85, 3.3, 0.8, "TF-IDF Vectorizer\n(1,2)-gram", fontsize=9)
    c_t, c_b = box(ax, cx2, 6.25, 3.3, 0.66, "Policy Classifier (SVM)",
                   fontsize=9.5, weight="bold")
    v_t, v_b = box(ax, cx2, 4.75, 3.3, 0.66, "5-fold Cross-Validation", fontsize=9)
    v_arrow(ax, cx2, f_b, c_t)
    v_arrow(ax, cx2, c_b, v_t)

    # ---- Stage 3: Deployment ----
    stage_container(ax, 9.85, 13.55, 3.95, 9.15, "3. Deployment")
    cx3 = 11.7
    p_t, p_b = box(ax, cx3, 7.85, 3.3, 0.66, "predict_tool(query)",
                   fontsize=9.5, weight="bold")
    s_t, s_b = box(ax, cx3, 6.25, 3.3, 0.66, "Tool Selection  (0.3 ms)", fontsize=9.5)
    n_t, n_b = box(ax, cx3, 4.75, 3.3, 0.66, "vs LLM Routing  (209 ms)",
                   fontsize=9, fill=GRAY)
    v_arrow(ax, cx3, p_b, s_t)
    v_arrow(ax, cx3, s_b, n_t)

    # ---- inter-stage arrows ----
    h_arrow(ax, 4.55, 5.35, 6.2, "Train")
    h_arrow(ax, 9.05, 9.85, 6.2, "Deploy")

    fig.tight_layout()
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT.relative_to(Path(__file__).resolve().parent.parent.parent)}")


if __name__ == "__main__":
    main()
