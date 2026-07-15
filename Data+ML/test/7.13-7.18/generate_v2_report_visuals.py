#!/usr/bin/env python3
"""Create reproducible report figures from one forecast-v2 evidence directory."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _title(title: str, data_mode: str) -> str:
    return f"{title}\nforecast-v2 | data mode: {data_mode}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--data-mode", required=True)
    args = parser.parse_args()
    root = args.evidence_dir
    figures = root / "figures"
    figures.mkdir(exist_ok=True)
    curve = pd.read_csv(root / "prediction_curve_v2.csv")
    metrics = pd.read_csv(root / "forecast_v2_model_metrics.csv")
    predictions = pd.read_csv(root / "forecast_v2_test_predictions.csv")

    pivot = curve.pivot_table(index="venue_id", columns="offset_hours", values="predicted_score", aggfunc="mean")
    fig, axis = plt.subplots(figsize=(10, max(4, len(pivot) * 0.22)))
    image = axis.imshow(pivot, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)
    axis.set_title(_title("Venue busyness forecast heatmap", args.data_mode))
    axis.set_xlabel("Forecast offset (hours)")
    axis.set_ylabel("Venue")
    axis.set_yticks(range(len(pivot.index)))
    axis.set_yticklabels(pivot.index, fontsize=6)
    fig.colorbar(image, ax=axis, label="Predicted busyness score (0–100)")
    fig.tight_layout()
    fig.savefig(figures / "venue_busyness_heatmap.png", dpi=180)
    plt.close(fig)

    selected = metrics[metrics["split"] == "test"].sort_values("mae")
    fig, axis = plt.subplots(figsize=(8, 4.5))
    axis.bar(selected["model_name"], selected["mae"], color="#2563eb")
    axis.set_title(_title("Test MAE by model", args.data_mode))
    axis.set_ylabel("MAE")
    axis.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(figures / "model_test_mae.png", dpi=180)
    plt.close(fig)

    best_name = selected.iloc[0]["model_name"]
    subset = predictions[predictions["model_name"] == best_name]
    fig, axis = plt.subplots(figsize=(5.5, 5.5))
    axis.scatter(subset["label_score"], subset["predicted_score"], alpha=0.55, color="#059669")
    axis.plot([0, 100], [0, 100], "--", color="#64748b")
    axis.set(xlim=(0, 100), ylim=(0, 100), xlabel="Actual proxy label", ylabel="Predicted score")
    axis.set_title(_title(f"Actual vs predicted ({best_name})", args.data_mode))
    fig.tight_layout()
    fig.savefig(figures / "actual_vs_predicted.png", dpi=180)
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
