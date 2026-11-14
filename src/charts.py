"""Static README charts from the pipeline outputs."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
CH = OUT / "charts"

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
SERIES = {"UA": "#2a78d6", "DL": "#eb6834"}
NAMES = {"WN": "Southwest", "B6": "JetBlue", "UA": "United", "DL": "Delta"}
METRIC = {"rpm": "RPMs", "asm": "ASMs", "passengers": "Passengers"}


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def stage_chart(comp: pd.DataFrame):
    d = comp[(comp.metric == "rpm") & (comp.quarter == 2) & comp.airline.isin(SERIES)]
    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    style(ax)
    stages = sorted(d.stage.unique())
    labels = ["Mainline\nonly", "+ wholly-owned\nregionals", "+ sole-contract\nregionals", "+ hub-allocated\nshared regionals"]
    w = 0.36
    for i, (code, color) in enumerate(SERIES.items()):
        g = d[d.airline == code].set_index("stage").loc[stages]
        xs = [s + (i - 0.5) * (w + 0.04) for s in stages]
        ax.bar(xs, g.gap_pct, width=w, color=color, label=NAMES[code], edgecolor=SURFACE, linewidth=1)
        for x, v in zip(xs, g.gap_pct):
            ax.text(x, v - 0.25, f"{v:.1f}%", ha="center", va="top", fontsize=8, color=INK2)
    ax.axhline(0, color=INK2, linewidth=1)
    ax.set_xticks(stages, labels, fontsize=8.5, color=INK2)
    ax.set_ylim(-7.5, 0.8)
    ax.set_ylabel("Estimate vs reported RPMs (%)", color=INK2, fontsize=9)
    ax.set_title("Attributing regional flying closes most of the gap (Q2 2024 RPMs)", loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(CH / "01_gap_by_attribution_stage.png", dpi=150)


def final_chart(final: pd.DataFrame):
    d = final[final.quarter == 2].copy()
    d["label"] = d.airline.map(NAMES) + " · " + d.metric.map(METRIC)
    d = d.sort_values("gap_pct")
    fig, ax = plt.subplots(figsize=(8, 4.4), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.axvspan(-1, 1, color="#eeede9", zorder=0)
    ax.text(0, -0.9, "±1% match band", ha="center", fontsize=8, color=INK2)
    ax.set_ylim(-1.2, len(d) - 0.4)
    ax.barh(d.label, d.gap_pct, color="#2a78d6", height=0.6)
    for y, v in enumerate(d.gap_pct):
        ax.text(v + (0.12 if v >= 0 else -0.12), y, f"{v:+.2f}%", va="center",
                ha="left" if v >= 0 else "right", fontsize=8, color=INK2)
    ax.axvline(0, color=INK2, linewidth=1)
    ax.set_xlim(-7, 3)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_xlabel("Final estimate vs reported (%)", color=INK2, fontsize=9)
    ax.set_title("Final estimates vs reported figures, Q2 2024", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(CH / "02_final_gap_q2.png", dpi=150)


def growth_chart(growth: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6, 5), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    lim = (0, 23)
    ax.plot(lim, lim, color=INK2, linewidth=1, linestyle="--", zorder=1)
    ax.text(21.5, 22.6, "perfect tracking", fontsize=8, color=INK2, ha="right")
    ax.scatter(growth.reported_qoq_growth_pct, growth.estimated_qoq_growth_pct, s=60,
               color="#2a78d6", edgecolor=SURFACE, linewidth=2, zorder=2)
    for _, r in growth.iterrows():
        left = (r.airline, r.metric) == ("B6", "rpm")
        ax.annotate(f"{NAMES[r.airline]} {METRIC[r.metric]}", (r.reported_qoq_growth_pct, r.estimated_qoq_growth_pct),
                    xytext=(-6 if left else 6, 2 if left else -3), textcoords="offset points", fontsize=7.5,
                    color=INK2, ha="right" if left else "left")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Reported Q1→Q2 growth (%)", color=INK2, fontsize=9)
    ax.set_ylabel("Estimated Q1→Q2 growth (%)", color=INK2, fontsize=9)
    ax.set_title("The proxy tracks the trend even where levels are off", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(CH / "03_growth_tracking.png", dpi=150)


if __name__ == "__main__":
    CH.mkdir(parents=True, exist_ok=True)
    stage_chart(pd.read_csv(OUT / "estimate_vs_reported_by_stage.csv"))
    final_chart(pd.read_csv(OUT / "final_estimate_vs_reported.csv"))
    growth_chart(pd.read_csv(OUT / "growth_check.csv"))
