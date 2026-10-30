"""Compare rolling historical and normal-model VaR and ES forecasts."""

from math import exp, pi, sqrt
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "portfolio_returns.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
WINDOW_SIZE = 1_000
CONFIDENCE_LEVELS = (0.95, 0.99)
EWMA_DECAY_FACTOR = 0.94
EWMA_INITIALIZATION_SIZE = 20
MODELS = ("historical", "normal", "ewma_fhs")


def historical_es(window_returns: np.ndarray, tail_probability: float) -> float:
    """Return positive expected shortfall from the lower tail of returns."""
    tail_cutoff = np.quantile(window_returns, tail_probability)
    tail_returns = window_returns[window_returns <= tail_cutoff]
    return -float(tail_returns.mean())


def ewma_filtered_risk(window_returns: np.ndarray) -> dict[str, float]:
    """Estimate tail risk from EWMA-standardized returns in one window."""
    mean_return = float(window_returns.mean())
    residuals = window_returns - mean_return
    initial_residuals = residuals[:EWMA_INITIALIZATION_SIZE]
    variance = float(np.var(initial_residuals, ddof=1))

    if not np.isfinite(variance) or variance <= 0:
        raise ValueError("EWMA volatility could not be initialized from this window.")

    standardized_residuals = []
    for residual in residuals[EWMA_INITIALIZATION_SIZE:]:
        standardized_residuals.append(residual / sqrt(variance))
        variance = (
            EWMA_DECAY_FACTOR * variance
            + (1 - EWMA_DECAY_FACTOR) * residual**2
        )

    next_day_volatility = sqrt(variance)
    shocks = np.asarray(standardized_residuals)
    estimates = {}

    for confidence in CONFIDENCE_LEVELS:
        level = int(confidence * 100)
        tail_probability = 1 - confidence
        shock_cutoff = np.quantile(shocks, tail_probability)
        tail_shocks = shocks[shocks <= shock_cutoff]
        shock_es = float(tail_shocks.mean())

        estimates[f"ewma_fhs_var_{level}"] = -(
            mean_return + next_day_volatility * shock_cutoff
        )
        estimates[f"ewma_fhs_es_{level}"] = -(
            mean_return + next_day_volatility * shock_es
        )

    return estimates


def make_forecasts(portfolio_returns: pd.Series) -> pd.DataFrame:
    """Make one-day forecasts using only the preceding rolling window."""
    prior_returns = portfolio_returns.shift(1)
    rolling = prior_returns.rolling(WINDOW_SIZE, min_periods=WINDOW_SIZE)
    forecasts = pd.DataFrame({"portfolio_return": portfolio_returns})
    rolling_mean = rolling.mean()
    rolling_standard_deviation = rolling.std()
    return_values = portfolio_returns.to_numpy()
    ewma_estimates = {
        f"ewma_fhs_{kind}_{int(level * 100)}": np.full(len(return_values), np.nan)
        for level in CONFIDENCE_LEVELS
        for kind in ("var", "es")
    }

    for position in range(WINDOW_SIZE, len(return_values)):
        prior_window = return_values[position - WINDOW_SIZE : position]
        for key, value in ewma_filtered_risk(prior_window).items():
            ewma_estimates[key][position] = value

    for confidence in CONFIDENCE_LEVELS:
        level = int(confidence * 100)
        tail_probability = 1 - confidence

        historical_var = -rolling.quantile(tail_probability)
        historical_expected_shortfall = rolling.apply(
            historical_es,
            raw=True,
            args=(tail_probability,),
        )
        forecasts[f"historical_var_{level}"] = historical_var
        forecasts[f"historical_es_{level}"] = historical_expected_shortfall
        forecasts[f"historical_exception_{level}"] = (
            portfolio_returns < -historical_var
        ).where(historical_var.notna())

        normal_quantile = NormalDist().inv_cdf(tail_probability)
        normal_density = exp(-0.5 * normal_quantile**2) / sqrt(2 * pi)
        normal_var = -(
            rolling_mean + normal_quantile * rolling_standard_deviation
        )
        normal_expected_shortfall = -(
            rolling_mean
            - rolling_standard_deviation * normal_density / tail_probability
        )
        forecasts[f"normal_var_{level}"] = normal_var
        forecasts[f"normal_es_{level}"] = normal_expected_shortfall
        forecasts[f"normal_exception_{level}"] = (
            portfolio_returns < -normal_var
        ).where(normal_var.notna())

        ewma_var = pd.Series(ewma_estimates[f"ewma_fhs_var_{level}"], index=forecasts.index)
        ewma_es = pd.Series(ewma_estimates[f"ewma_fhs_es_{level}"], index=forecasts.index)
        forecasts[f"ewma_fhs_var_{level}"] = ewma_var
        forecasts[f"ewma_fhs_es_{level}"] = ewma_es
        forecasts[f"ewma_fhs_exception_{level}"] = (
            portfolio_returns < -ewma_var
        ).where(ewma_var.notna())

    return forecasts


def summarize_forecasts(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Summarize forecast coverage and the frequency of VaR exceptions."""
    rows = []

    for model in MODELS:
        for confidence in CONFIDENCE_LEVELS:
            level = int(confidence * 100)
            var_column = f"{model}_var_{level}"
            es_column = f"{model}_es_{level}"
            exception_column = f"{model}_exception_{level}"
            scored = forecasts.dropna(subset=[var_column, es_column])
            exceptions = scored[exception_column].astype(bool)
            realized_losses = -scored["portfolio_return"]

            rows.append(
                {
                    "model": model,
                    "confidence_level": confidence,
                    "window_size_days": WINDOW_SIZE,
                    "forecast_count": len(scored),
                    "expected_exception_rate": 1 - confidence,
                    "exception_count": int(exceptions.sum()),
                    "observed_exception_rate": float(exceptions.mean()),
                    "mean_var": float(scored[var_column].mean()),
                    "mean_es": float(scored[es_column].mean()),
                    "mean_loss_on_exceptions": (
                        float(realized_losses[exceptions].mean())
                        if exceptions.any()
                        else np.nan
                    ),
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    """Load portfolio returns and save forecasts and comparison summary."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run src/download_data.py first."
        )

    returns = pd.read_csv(INPUT_PATH, parse_dates=["date"], index_col="date")
    if "portfolio_return" not in returns.columns:
        raise ValueError(f"Expected a portfolio_return column in {INPUT_PATH}.")

    portfolio_returns = returns["portfolio_return"].dropna()
    forecasts = make_forecasts(portfolio_returns)
    summary = summarize_forecasts(forecasts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    forecasts_path = OUTPUT_DIR / "var_es_forecasts.csv"
    summary_path = OUTPUT_DIR / "var_es_summary.csv"
    forecasts.to_csv(forecasts_path, index_label="date")
    summary.to_csv(summary_path, index=False)

    print(f"Saved forecasts to {forecasts_path}")
    print(f"Saved comparison summary to {summary_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
