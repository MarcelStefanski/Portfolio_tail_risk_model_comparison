"""Compare historical, normal, EWMA, and GARCH VaR and ES forecasts."""

from math import erfc, exp, log, pi, sqrt
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd
from arch import arch_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "portfolio_returns.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
WINDOW_SIZE = 1_000
SENSITIVITY_WINDOW_SIZES = (500, 1_000, 1_500)
CONFIDENCE_LEVELS = (0.95, 0.99)
EWMA_DECAY_FACTOR = 0.94
EWMA_INITIALIZATION_SIZE = 20
REGIME_VOLATILITY_WINDOW = 20
REGIME_HIGH_VOLATILITY_QUANTILE = 0.75
GARCH_REFIT_INTERVAL = 21
MODELS = ("historical", "normal", "ewma_fhs", "garch")


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


def make_forecasts(
    portfolio_returns: pd.Series, window_size: int = WINDOW_SIZE
) -> pd.DataFrame:
    """Make one-day forecasts using only the preceding rolling window."""
    prior_returns = portfolio_returns.shift(1)
    rolling = prior_returns.rolling(window_size, min_periods=window_size)
    forecasts = pd.DataFrame({"portfolio_return": portfolio_returns})
    rolling_mean = rolling.mean()
    rolling_standard_deviation = rolling.std()
    return_values = portfolio_returns.to_numpy()
    ewma_estimates = {
        f"ewma_fhs_{kind}_{int(level * 100)}": np.full(len(return_values), np.nan)
        for level in CONFIDENCE_LEVELS
        for kind in ("var", "es")
    }
    garch_mean_estimates = np.full(len(return_values), np.nan)
    garch_variance_estimates = np.full(len(return_values), np.nan)
    garch_parameters = None
    garch_variance_pct_squared = None

    for position in range(window_size, len(return_values)):
        prior_window = return_values[position - window_size : position]
        for key, value in ewma_filtered_risk(prior_window).items():
            ewma_estimates[key][position] = value

        should_refit_garch = (position - window_size) % GARCH_REFIT_INTERVAL == 0
        if should_refit_garch:
            fitted_garch = arch_model(
                prior_window * 100,
                mean="Constant",
                vol="GARCH",
                p=1,
                o=0,
                q=1,
                dist="normal",
                rescale=False,
            ).fit(update_freq=0, disp="off")
            if fitted_garch.convergence_flag != 0:
                raise RuntimeError(
                    f"GARCH(1,1) estimation did not converge at "
                    f"{portfolio_returns.index[position]} (window={window_size})."
                )
            parameters = fitted_garch.params
            garch_parameters = (
                float(parameters["mu"]),
                float(parameters["omega"]),
                float(parameters["alpha[1]"]),
                float(parameters["beta[1]"]),
            )
            garch_variance_pct_squared = float(
                fitted_garch.forecast(horizon=1, reindex=False)
                .residual_variance.iloc[-1, 0]
            )
        else:
            mean_pct, omega, alpha, beta = garch_parameters
            latest_innovation_pct = return_values[position - 1] * 100 - mean_pct
            garch_variance_pct_squared = (
                omega
                + alpha * latest_innovation_pct**2
                + beta * garch_variance_pct_squared
            )

        garch_mean_estimates[position] = garch_parameters[0] / 100
        garch_variance_estimates[position] = garch_variance_pct_squared / 10_000

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

        garch_mean = pd.Series(garch_mean_estimates, index=forecasts.index)
        garch_standard_deviation = pd.Series(
            np.sqrt(garch_variance_estimates), index=forecasts.index
        )
        garch_var = -(garch_mean + normal_quantile * garch_standard_deviation)
        garch_expected_shortfall = -(
            garch_mean
            - garch_standard_deviation * normal_density / tail_probability
        )
        forecasts[f"garch_var_{level}"] = garch_var
        forecasts[f"garch_es_{level}"] = garch_expected_shortfall
        forecasts[f"garch_exception_{level}"] = (
            portfolio_returns < -garch_var
        ).where(garch_var.notna())

    return forecasts


def log_likelihood(counts: tuple[int, ...], probabilities: tuple[float, ...]) -> float:
    """Calculate a binomial log likelihood, including zero-count terms safely."""
    total = 0.0
    for count, probability in zip(counts, probabilities):
        if count == 0:
            continue
        if probability <= 0:
            return -np.inf
        total += count * log(probability)
    return total


def kupiec_uc_test(exceptions: np.ndarray, target_rate: float) -> tuple[float, float]:
    """Return Kupiec unconditional-coverage LR statistic and chi-square p-value."""
    count = int(exceptions.sum())
    total = len(exceptions)
    observed_rate = count / total
    null_log_likelihood = log_likelihood(
        (count, total - count), (target_rate, 1 - target_rate)
    )
    fitted_log_likelihood = log_likelihood(
        (count, total - count), (observed_rate, 1 - observed_rate)
    )
    statistic = max(0.0, 2 * (fitted_log_likelihood - null_log_likelihood))
    return statistic, erfc(sqrt(statistic / 2))


def christoffersen_independence_test(
    exceptions: np.ndarray,
) -> tuple[float, float]:
    """Return Christoffersen first-order independence LR statistic and p-value."""
    indicators = exceptions.astype(int)
    previous = indicators[:-1]
    current = indicators[1:]
    n00 = int(((previous == 0) & (current == 0)).sum())
    n01 = int(((previous == 0) & (current == 1)).sum())
    n10 = int(((previous == 1) & (current == 0)).sum())
    n11 = int(((previous == 1) & (current == 1)).sum())
    transition_count = n00 + n01 + n10 + n11
    if transition_count == 0:
        return np.nan, np.nan

    probability_01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    probability_11 = n11 / (n10 + n11) if n10 + n11 else 0.0
    probability_null = (n01 + n11) / transition_count
    alternative_log_likelihood = log_likelihood(
        (n00, n01, n10, n11),
        (1 - probability_01, probability_01, 1 - probability_11, probability_11),
    )
    null_log_likelihood = log_likelihood(
        (n00 + n10, n01 + n11),
        (1 - probability_null, probability_null),
    )
    statistic = max(
        0.0, 2 * (alternative_log_likelihood - null_log_likelihood)
    )
    return statistic, erfc(sqrt(statistic / 2))


def fz0_score(losses: np.ndarray, var: np.ndarray, es: np.ndarray, tail_rate: float) -> float:
    """Return the mean joint VaR-ES FZ0 score for positive loss forecasts."""
    if np.any(es <= 0):
        raise ValueError("FZ0 scoring requires positive expected-shortfall forecasts.")
    score = (
        (losses >= var) * (losses - var) / (tail_rate * es)
        + var / es
        + np.log(es)
        - 1
    )
    return float(score.mean())


def summarize_forecasts(
    forecasts: pd.DataFrame, window_size: int = WINDOW_SIZE
) -> pd.DataFrame:
    """Summarize VaR coverage diagnostics and joint VaR-ES forecast scores."""
    rows = []

    for model in MODELS:
        for confidence in CONFIDENCE_LEVELS:
            level = int(confidence * 100)
            var_column = f"{model}_var_{level}"
            es_column = f"{model}_es_{level}"
            exception_column = f"{model}_exception_{level}"
            scored = forecasts.dropna(subset=[var_column, es_column])
            exceptions = scored[exception_column].astype(bool)
            exception_values = exceptions.to_numpy()
            realized_losses = -scored["portfolio_return"]
            uc_statistic, uc_p_value = kupiec_uc_test(
                exception_values, 1 - confidence
            )
            independence_statistic, independence_p_value = (
                christoffersen_independence_test(exception_values)
            )
            conditional_coverage_statistic = uc_statistic + independence_statistic
            conditional_coverage_p_value = exp(
                -conditional_coverage_statistic / 2
            )
            mean_fz0_score = fz0_score(
                realized_losses.to_numpy(),
                scored[var_column].to_numpy(),
                scored[es_column].to_numpy(),
                1 - confidence,
            )

            rows.append(
                {
                    "model": model,
                    "confidence_level": confidence,
                    "window_size_days": window_size,
                    "forecast_count": len(scored),
                    "expected_exception_rate": 1 - confidence,
                    "exception_count": int(exceptions.sum()),
                    "observed_exception_rate": float(exceptions.mean()),
                    "kupiec_uc_lr": uc_statistic,
                    "kupiec_uc_p_value": uc_p_value,
                    "christoffersen_ind_lr": independence_statistic,
                    "christoffersen_ind_p_value": independence_p_value,
                    "christoffersen_cc_lr": conditional_coverage_statistic,
                    "christoffersen_cc_p_value": conditional_coverage_p_value,
                    "mean_fz0_score": mean_fz0_score,
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


def summarize_by_volatility_regime(
    forecasts: pd.DataFrame, window_size: int = WINDOW_SIZE
) -> pd.DataFrame:
    """Compare forecasts when lagged volatility is below or above a training cutoff."""
    prior_volatility = (
        forecasts["portfolio_return"]
        .rolling(REGIME_VOLATILITY_WINDOW, min_periods=REGIME_VOLATILITY_WINDOW)
        .std()
        .shift(1)
        * sqrt(252)
    )
    training_volatility = prior_volatility.iloc[:window_size].dropna()
    threshold = float(
        training_volatility.quantile(REGIME_HIGH_VOLATILITY_QUANTILE)
    )
    regime_labels = pd.Series(
        np.where(prior_volatility > threshold, "high_volatility", "lower_volatility"),
        index=forecasts.index,
    )
    rows = []

    for model in MODELS:
        for confidence in CONFIDENCE_LEVELS:
            level = int(confidence * 100)
            var_column = f"{model}_var_{level}"
            es_column = f"{model}_es_{level}"
            exception_column = f"{model}_exception_{level}"
            scored = forecasts.dropna(subset=[var_column, es_column])

            for regime in ("lower_volatility", "high_volatility"):
                regime_scored = scored.loc[regime_labels.loc[scored.index] == regime]
                if regime_scored.empty:
                    continue
                exceptions = regime_scored[exception_column].astype(bool)
                realized_losses = -regime_scored["portfolio_return"].to_numpy()
                var_forecasts = regime_scored[var_column].to_numpy()
                es_forecasts = regime_scored[es_column].to_numpy()

                rows.append(
                    {
                        "model": model,
                        "confidence_level": confidence,
                        "volatility_regime": regime,
                        "forecast_count": len(regime_scored),
                        "exception_count": int(exceptions.sum()),
                        "observed_exception_rate": float(exceptions.mean()),
                        "mean_fz0_score": fz0_score(
                            realized_losses,
                            var_forecasts,
                            es_forecasts,
                            1 - confidence,
                        ),
                        "mean_prior_20d_volatility": float(
                            prior_volatility.loc[regime_scored.index].mean()
                        ),
                        "training_volatility_threshold": threshold,
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
    regime_summary = summarize_by_volatility_regime(forecasts, WINDOW_SIZE)
    common_evaluation_start = max(SENSITIVITY_WINDOW_SIZES)
    sensitivity_summaries = []
    for window_size in SENSITIVITY_WINDOW_SIZES:
        window_forecasts = (
            forecasts
            if window_size == WINDOW_SIZE
            else make_forecasts(portfolio_returns, window_size)
        )
        common_period_forecasts = window_forecasts.iloc[common_evaluation_start:]
        sensitivity_summaries.append(
            summarize_forecasts(common_period_forecasts, window_size)
        )
    sensitivity_summary = pd.concat(sensitivity_summaries, ignore_index=True)
    sensitivity_summary["evaluation_start_date"] = portfolio_returns.index[
        common_evaluation_start
    ]
    sensitivity_summary["evaluation_end_date"] = portfolio_returns.index[-1]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    forecasts_path = OUTPUT_DIR / "var_es_forecasts.csv"
    summary_path = OUTPUT_DIR / "var_es_summary.csv"
    regime_summary_path = OUTPUT_DIR / "var_es_regime_summary.csv"
    sensitivity_summary_path = OUTPUT_DIR / "var_es_window_sensitivity.csv"
    forecasts.to_csv(forecasts_path, index_label="date")
    summary.to_csv(summary_path, index=False)
    regime_summary.to_csv(regime_summary_path, index=False)
    sensitivity_summary.to_csv(sensitivity_summary_path, index=False)

    print(f"Saved forecasts to {forecasts_path}")
    print(f"Saved comparison summary to {summary_path}")
    print(f"Saved volatility-regime summary to {regime_summary_path}")
    print(f"Saved window-sensitivity summary to {sensitivity_summary_path}")
    print(summary.to_string(index=False))
    print(regime_summary.to_string(index=False))
    print(sensitivity_summary.to_string(index=False))


if __name__ == "__main__":
    main()
