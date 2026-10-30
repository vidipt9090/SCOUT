"""Regenerate results/summary.md and the figures from the pilot. `make report`."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import kruskal  # noqa: E402

from eval.score import main as score  # noqa: E402

OUT = Path("results")
LATENCY_TARGET_S = 30
INK, MUTED, RULE = "#1f2933", "#616e7c", "#d9dde1"
SERIES = "#2f6db5"


def p95(s: pd.Series) -> float:
    return s.quantile(0.95)


def by_factor(df: pd.DataFrame, factor: str) -> pd.DataFrame:
    g = df.groupby(factor)
    return pd.DataFrame(
        {
            "runs": g.size(),
            "median_s": g["latency_excl_wait_s"].median().round(1),
            "p95_s": g["latency_excl_wait_s"].apply(p95).round(1),
            "over_30s": g["latency_excl_wait_s"].apply(lambda s: (s > LATENCY_TARGET_S).mean()).round(2),
            "proposed_correct": g["proposed_correct"].mean().round(2),
            "resolved_correct": g["resolved_correct"].mean().round(2),
            "guardrail_fired": g["guardrail_fired"].mean().round(2),
            "degraded": g["degraded"].sum(),
            "mean_calls": g["model_calls"].mean().round(1),
            "mean_cost_usd": g["estimated_cost_usd"].mean().round(5),
        }
    ).reset_index()


def kw(df: pd.DataFrame, factor: str) -> str:
    groups = [g["latency_excl_wait_s"].to_numpy() for _, g in df.groupby(factor)]
    if len(groups) < 2 or min(len(g) for g in groups) < 2:
        return f"{factor}: too few runs"
    h, p = kruskal(*groups)
    return f"{factor}: H = {h:.2f}, p = {p:.3f}, groups {[len(g) for g in groups]}"


def md(frame: pd.DataFrame) -> str:
    head = "| " + " | ".join(map(str, frame.columns)) + " |"
    sep = "|" + "---|" * len(frame.columns)
    body = ["| " + " | ".join(map(str, row)) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([head, sep, *body])


def latency_figure(core: pd.DataFrame, paired: pd.DataFrame) -> None:
    panels = [("Architecture", core, "architecture"), ("Planner strategy", core, "planner_strategy"), ("Messaging", paired, "comm_mode")]
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 3.4), sharey=True)
    for ax, (title, frame, factor) in zip(axes, panels):
        levels = sorted(frame[factor].unique())
        for i, level in enumerate(levels):
            values = frame[frame[factor] == level]["latency_excl_wait_s"]
            ax.scatter([i] * len(values), values, s=26, color=SERIES, alpha=0.45, linewidths=0)
            ax.plot([i - 0.22, i + 0.22], [values.median()] * 2, color=INK, linewidth=2)
            ax.text(i + 0.27, values.median(), f"{values.median():.0f}", va="center", fontsize=9, color=INK)
        ax.axhline(LATENCY_TARGET_S, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
        ax.set_xticks(range(len(levels)), levels, color=INK, fontsize=9)
        ax.set_xlim(-0.6, len(levels) - 0.3)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.tick_params(axis="y", colors=MUTED, length=0, labelsize=9)
        ax.tick_params(axis="x", length=0)
        ax.grid(axis="y", color=RULE, linewidth=0.7)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(RULE)
    axes[0].set_ylabel("Seconds per run, excluding rate-limit wait", fontsize=9, color=MUTED)
    axes[0].text(-0.55, LATENCY_TARGET_S + 1, "30 s target", fontsize=8, color=MUTED)
    fig.tight_layout()
    fig.savefig(OUT / "latency_by_factor.png", dpi=160)
    plt.close(fig)


def main():
    df = score()
    core = df[df["block"] == "core"]
    done_keys = ["disruption_type", "severity", "persona"]
    base = core[(core["architecture"] == "sequential") & (core["planner_strategy"] == "react")]
    paired = pd.concat([base, df[df["block"] == "messaging"]])
    prompt_runs = pd.concat([base[base["persona"] == "plant"], df[df["block"] == "prompt_variance"]])
    persona = df[df["severity"].isin(["low", "medium"])]
    crosstab = pd.crosstab([persona["severity"], persona["persona"]], persona["final_action"].fillna("none")).reset_index()
    crosstab.columns = [str(c) for c in crosstab.columns]

    n, wall = len(df), df["total_latency_s"].sum()
    lines = [
        "# Pilot results",
        "",
        f"Runs: {n} of 48 planned. One replicate per condition, on one LLM backbone (gemini-3.1-flash-lite).",
        f"Degraded runs: {int(df['degraded'].sum())}, counted in every denominator.",
        f"Total model calls: {int(df['model_calls'].sum())}. Rate-limit wait: {df['rate_wait_s'].sum():.0f} s of {wall:.0f} s.",
        f"Estimated cost at list price: {df['estimated_cost_usd'].sum():.4f} USD in total (free tier in practice).",
        "",
        "Latency below excludes rate-limit wait. These scenarios were also used to tune prompts, so accuracy is not an independent measure.",
        "`proposed_correct` means the Planner's own action matched the answer key. `resolved_correct` means the final action matched and did not need a human.",
        "",
        "## Sensing",
        "",
        f"Severity matched the intended level in {df['severity_correct'].mean():.0%} of runs. Mean vote agreement {df['vote_agreement'].mean():.2f}.",
        "",
        md(df.groupby(["severity", "assessed_severity"], dropna=False).size().reset_index(name="runs")),
        "",
        "## Core grid by factor",
        "",
    ]
    for factor in ("architecture", "planner_strategy", "persona", "severity", "disruption_type"):
        lines += [f"### {factor}", "", md(by_factor(core, factor)), ""]
    lines += ["## Blackboard vs direct hand-off (paired conditions)", "", md(by_factor(paired, "comm_mode")), ""]
    lines += ["## Scout prompt, CoT vs few-shot (paired conditions)", "", md(by_factor(prompt_runs, "scout_prompt")), ""]
    lines += ["## Persona divergence (final action at low and medium severity)", "", md(crosstab), ""]
    lines += [
        "## Guardrail",
        "",
        md(df.groupby(["decision", "checker"], dropna=False).size().reset_index(name="runs")),
        "",
        f"Violated rules seen: {sorted({r for v in df['violated_rules'].dropna() for r in str(v).split(',') if r})}.",
        f"Final quantity within limits: {df['quantity_ok'].dropna().astype(bool).mean():.0%} of {df['quantity_ok'].notna().sum()} ordering plans.",
        f"Citations a subset of retrieved documents: {df['citations_ok'].mean():.0%} of runs.",
        "",
        "## Kruskal-Wallis on latency",
        "",
        "With about 40 runs these tests are underpowered and descriptive. They do not establish causes.",
        "",
        f"- {kw(core, 'architecture')}",
        f"- {kw(core, 'planner_strategy')}",
        f"- {kw(paired, 'comm_mode')}",
        "",
        "![Latency by factor](latency_by_factor.png)",
    ]
    if not core.empty and not paired.empty:
        latency_figure(core, paired)
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote results/summary.md", "; key groups", done_keys)


if __name__ == "__main__":
    main()
