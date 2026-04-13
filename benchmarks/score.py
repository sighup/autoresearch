#!/usr/bin/env python3
"""Benchmark scorer for autoresearch.

Reads scores.json from a completed autoresearch run and outputs
a scorecard with convergence metrics. Use to compare plugin changes.

Usage:
    python benchmarks/score.py benchmarks/targets/fast-perf
    python benchmarks/score.py benchmarks/targets/fast-perf --save run-v1
    python benchmarks/score.py --compare run-v1 run-v2
"""

import json
import sys
from datetime import datetime
from pathlib import Path

RESULTS_DIR = ".autoresearch/results"
SCORES_FILE = f"{RESULTS_DIR}/scores.json"
SAVED_DIR = Path(__file__).parent / "results"


def score_target(target_dir: str) -> dict:
    """Read scores.json and compute benchmark metrics."""
    target = Path(target_dir)
    scores_path = target / SCORES_FILE
    if not scores_path.exists():
        print(f"ERROR: {scores_path} not found. Run autoresearch first.", file=sys.stderr)
        sys.exit(1)

    scores = json.loads(scores_path.read_text())
    if not scores:
        print("ERROR: scores.json is empty.", file=sys.stderr)
        sys.exit(1)

    baseline = scores[0]["pass_rate"]
    final = scores[-1]["pass_rate"]
    cycles = len(scores) - 1  # first entry is baseline

    # Time from first to last timestamp
    t0 = datetime.fromisoformat(scores[0]["timestamp"])
    t1 = datetime.fromisoformat(scores[-1]["timestamp"])
    wall_seconds = (t1 - t0).total_seconds()

    # Cycles to reach 90%
    cycles_to_target = None
    for i, s in enumerate(scores):
        if s["pass_rate"] >= 0.9:
            cycles_to_target = i  # 0 = baseline was already there
            break

    # Improvement per cycle
    improvements = 0
    for i in range(1, len(scores)):
        if scores[i]["pass_rate"] > scores[i - 1]["pass_rate"]:
            improvements += 1
    hit_rate = improvements / cycles if cycles > 0 else 0

    # Per-assertion trajectory
    assertion_names = sorted(scores[-1].get("assertion_pass_rates", {}).keys())
    assertion_baseline = scores[0].get("assertion_pass_rates", {})
    assertion_final = scores[-1].get("assertion_pass_rates", {})

    return {
        "target": target_dir,
        "baseline": baseline,
        "final": final,
        "lift": final - baseline,
        "cycles": cycles,
        "cycles_to_target": cycles_to_target,
        "wall_seconds": round(wall_seconds),
        "improvement_hit_rate": round(hit_rate, 2),
        "assertion_baseline": assertion_baseline,
        "assertion_final": assertion_final,
        "scores": [s["pass_rate"] for s in scores],
    }


def print_scorecard(metrics: dict):
    """Print a formatted scorecard."""
    print("=" * 60)
    print(f"BENCHMARK: {metrics['target']}")
    print("=" * 60)
    print(f"  Baseline:          {metrics['baseline']:.0%}")
    print(f"  Final:             {metrics['final']:.0%}")
    print(f"  Lift:              +{metrics['lift']:.0%}")
    print(f"  Cycles:            {metrics['cycles']}")
    if metrics["cycles_to_target"] is not None:
        print(f"  Cycles to 90%:     {metrics['cycles_to_target']}")
    else:
        print(f"  Cycles to 90%:     not reached")
    print(f"  Wall time:         {metrics['wall_seconds']}s")
    print(f"  Improvement rate:  {metrics['improvement_hit_rate']:.0%} of cycles improved")
    print(f"  Trajectory:        {' → '.join(f'{r:.0%}' for r in metrics['scores'])}")

    # Per-assertion
    if metrics["assertion_baseline"] or metrics["assertion_final"]:
        print(f"\n  Assertion breakdown:")
        all_names = sorted(set(list(metrics["assertion_baseline"].keys()) +
                               list(metrics["assertion_final"].keys())))
        for name in all_names:
            b = metrics["assertion_baseline"].get(name, 0)
            f = metrics["assertion_final"].get(name, 0)
            delta = f - b
            sign = "+" if delta >= 0 else ""
            print(f"    {name:40s} {b:.0%} → {f:.0%} ({sign}{delta:.0%})")

    print("=" * 60)


def save_scorecard(metrics: dict, name: str):
    """Save scorecard to benchmarks/results/ for later comparison."""
    SAVED_DIR.mkdir(parents=True, exist_ok=True)
    path = SAVED_DIR / f"{name}.json"
    path.write_text(json.dumps(metrics, indent=2))
    print(f"\nSaved to {path}")


def compare_scorecards(name1: str, name2: str):
    """Compare two saved scorecards side by side."""
    f1 = SAVED_DIR / f"{name1}.json"
    f2 = SAVED_DIR / f"{name2}.json"
    if not f1.exists() or not f2.exists():
        print(f"ERROR: need both {f1} and {f2}", file=sys.stderr)
        sys.exit(1)

    m1 = json.loads(f1.read_text())
    m2 = json.loads(f2.read_text())

    print("=" * 60)
    print(f"COMPARISON: {name1} vs {name2}")
    print("=" * 60)

    def row(label, v1, v2, fmt=".0%", lower_better=False):
        s1 = f"{v1:{fmt}}" if isinstance(v1, (int, float)) else str(v1)
        s2 = f"{v2:{fmt}}" if isinstance(v2, (int, float)) else str(v2)
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            diff = v2 - v1
            better = diff < 0 if lower_better else diff > 0
            sign = "+" if diff >= 0 else ""
            marker = " ✓" if better else (" ✗" if diff != 0 else "")
            delta = f"{sign}{diff:{fmt}}{marker}"
        else:
            delta = ""
        print(f"  {label:25s} {s1:>10s}  {s2:>10s}  {delta}")

    print(f"  {'':25s} {name1:>10s}  {name2:>10s}  {'delta':>10s}")
    print(f"  {'-' * 25} {'-' * 10}  {'-' * 10}  {'-' * 10}")
    row("Baseline", m1["baseline"], m2["baseline"])
    row("Final", m1["final"], m2["final"])
    row("Lift", m1["lift"], m2["lift"])
    row("Cycles", m1["cycles"], m2["cycles"], "d", lower_better=True)
    ct1 = m1["cycles_to_target"] if m1["cycles_to_target"] is not None else 999
    ct2 = m2["cycles_to_target"] if m2["cycles_to_target"] is not None else 999
    row("Cycles to 90%", ct1, ct2, "d", lower_better=True)
    row("Wall time (s)", m1["wall_seconds"], m2["wall_seconds"], "d", lower_better=True)
    row("Hit rate", m1["improvement_hit_rate"], m2["improvement_hit_rate"])
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--compare":
        if len(sys.argv) != 4:
            print("Usage: score.py --compare <run1> <run2>")
            sys.exit(1)
        compare_scorecards(sys.argv[2], sys.argv[3])
    else:
        target_dir = sys.argv[1]
        metrics = score_target(target_dir)
        print_scorecard(metrics)

        # Check for --save flag
        if len(sys.argv) >= 4 and sys.argv[2] == "--save":
            save_scorecard(metrics, sys.argv[3])
