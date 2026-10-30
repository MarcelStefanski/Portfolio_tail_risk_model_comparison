"""Plot realized losses, VaR, ES, and exceptions for all models."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "var_es_forecasts.csv"
OUTPUT_PATH = PROJECT_ROOT / "reports" / "figures" / "var_es_99_backtest.png"
CONFIDENCE_LEVEL = 99
MODELS = (
    ("historical", "Historical simulation"),
    ("normal", "Normal model"),
    ("ewma_fhs", "EWMA filtered historical simulation"),
    ("garch", "GARCH(1,1) with normal innovations"),
)


def main() -> None:
    """Save a chart of realized losses and each model's 99% risk forecasts."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run src/backtest_var_es.py first."
        )

    forecasts = pd.read_csv(INPUT_PATH, parse_dates=["date"], index_col="date")
    required_columns = [
        f"{model}_{kind}_{CONFIDENCE_LEVEL}"
        for model, _ in MODELS
        for kind in ("var", "es", "exception")
    ]
    missing_columns = [column for column in required_columns if column not in forecasts]
    if missing_columns:
        raise ValueError(f"Forecast file is missing columns: {', '.join(missing_columns)}")

    scored = forecasts.dropna(
        subset=[f"{model}_var_{CONFIDENCE_LEVEL}" for model, _ in MODELS]
    )
    if scored.empty:
        raise ValueError("No out-of-sample risk forecasts are available to plot.")

    realized_losses = -scored["portfolio_return"] * 100
    fig, axes = plt.subplots(
        len(MODELS),
        1,
        figsize=(14, 12),
        sharex=True,
        sharey=True,
    )

    for axis, (model, label) in zip(axes, MODELS):
        var = scored[f"{model}_var_{CONFIDENCE_LEVEL}"] * 100
        es = scored[f"{model}_es_{CONFIDENCE_LEVEL}"] * 100
        exceptions = scored[f"{model}_exception_{CONFIDENCE_LEVEL}"].fillna(False).astype(bool)

        axis.plot(
            scored.index,
            realized_losses,
            color="#77808b",
            linewidth=0.45,
            alpha=0.55,
            label="Realized daily loss",
        )
        axis.plot(scored.index, var, color="#1769aa", linewidth=1.0, label="99% VaR")
        axis.plot(scored.index, es, color="#f28e2b", linewidth=1.0, label="99% ES")
        axis.scatter(
            scored.index[exceptions],
            realized_losses[exceptions],
            color="#c62828",
            s=10,
            label="VaR exception",
            zorder=3,
        )
        axis.set_title(label, loc="left", fontsize=10)
        axis.set_ylabel("Loss (%)")
        axis.axhline(0, color="#333333", linewidth=0.5, alpha=0.5)
        axis.grid(axis="y", color="#d9d9d9", linewidth=0.6)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=4,
        frameon=False,
    )
    fig.suptitle("Out-of-sample one-day 99% portfolio tail-risk forecasts", y=0.995)
    axes[-1].set_xlabel("Date")
    fig.tight_layout(rect=(0, 0, 1, 0.92))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved chart to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
