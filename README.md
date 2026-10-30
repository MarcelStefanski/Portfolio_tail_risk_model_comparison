# Portfolio Tail Risk Model Comparison

## Project overview

This project compares statistical methods for estimating large losses in an investment portfolio. It asks how reliably different models estimate portfolio Value at Risk (VaR) and Expected Shortfall (ES), especially during volatile markets.

## Research question

**Which tail-risk model gives the most reliable out-of-sample estimates for a portfolio, and how does performance change in calm and turbulent periods?**

## Initial scope

The first version will use daily historical asset returns to build a simple portfolio and compare a small set of approaches. The initial data and portfolio assumptions are:

- Daily adjusted prices for SPY (US equities) and TLT (long-term US Treasury bonds), downloaded with `yfinance`
- Portfolio weights of 60% SPY and 40% TLT, rebalanced daily
- Data starting on 2007-01-01 and continuing through the latest available date

The models to compare are:

1. Historical simulation
2. A parametric model with normally distributed returns
3. Filtered historical simulation with EWMA volatility

For each method, the project will estimate 95% and 99% VaR and ES. The estimates will be tested against returns that were not used to fit the models. The comparison will consider how often losses exceed VaR, the size of losses beyond VaR, and how results differ across market conditions.

## First model comparison

The first comparison uses the previous 1,000 trading days of portfolio returns to forecast one-day 95% and 99% VaR and ES. It compares:

- Historical simulation, which estimates the tail from observed returns
- A normal model, which estimates the tail from the rolling mean and standard deviation
- EWMA filtered historical simulation, which rescales past returns by their estimated volatility before estimating the tail

Each day's forecast uses only earlier returns. All models use a 1,000-day window. The EWMA model uses a daily decay factor of 0.94, following the [RiskMetrics technical document](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a). The script saves forecasts and a summary of VaR exceptions for each model.

The summary also reports Kupiec unconditional-coverage tests and Christoffersen independence and conditional-coverage tests for VaR exceptions. For joint VaR-ES comparison, it reports the mean FZ0 score, where a lower score is better. The [initial findings](reports/initial_findings.md) explain the results and their limitations; the tests follow [Kupiec](https://fedinprint.org/item/fedgfe/34596/original), [Christoffersen](https://users.ssc.wisc.edu/~bhansen/718/Christoffersen1998.pdf), and the joint scoring framework of [Fissler, Ziegel, and Gneiting](https://arxiv.org/abs/1507.00244).

The same script compares forecasts in lower- and high-volatility regimes. It classifies each date from annualized volatility over the prior 20 trading days, with the high-volatility cutoff set to the 75th percentile of the initial 1,000-day training period. This regime summary is saved as `var_es_regime_summary.csv` in `data/processed/`.

It also compares 500-, 1,000-, and 1,500-day estimation windows on a shared evaluation period, so the results are not driven by different market dates. Those results are saved as `var_es_window_sensitivity.csv` in `data/processed/`.

Run it after downloading the data:

```bash
python3 src/backtest_var_es.py
```

It writes `var_es_forecasts.csv` and `var_es_summary.csv` to `data/processed/`.

Generate the 99% VaR/ES comparison chart after the model script:

```bash
python3 src/plot_var_es.py
```

The chart is saved to `reports/figures/var_es_99_backtest.png`.

![Out-of-sample 99% VaR and ES forecasts with exceptions highlighted](reports/figures/var_es_99_backtest.png)

## Planned outputs

- Reproducible analysis code
- Charts comparing model estimates with realized portfolio losses
- Backtesting results and a discussion of model limitations
- A concise report explaining the methods and findings

See [the initial findings](reports/initial_findings.md) for the first exception-rate comparison and its limitations.

## Skills demonstrated

- Financial mathematics and portfolio return calculations
- Statistical modeling of extreme losses
- Time-series analysis and out-of-sample evaluation
- Data analysis and clear communication of quantitative results

## Project status

The data pipeline, three rolling VaR/ES models, VaR exception diagnostics, joint VaR-ES scoring, volatility-regime and rolling-window comparisons, an out-of-sample 99% chart, and an initial findings report are in place. The current findings are specific to this portfolio and sample; a useful next step is to add and compare a GARCH volatility model.
