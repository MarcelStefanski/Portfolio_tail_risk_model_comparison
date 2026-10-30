# Initial Findings: Portfolio Tail-Risk Models

## Setup

The comparison uses one-day returns for a daily rebalanced portfolio holding 60% SPY and 40% TLT. Each model is estimated from the previous 1,000 trading days and then forecasts the next day. The out-of-sample period runs from 2010-12-22 through 2026-10-29, covering 3,987 forecast dates.

An exception occurs when the realized loss is greater than that day's VaR forecast. A correctly calibrated 95% VaR should have an exception rate near 5%; a 99% VaR should be near 1% over a sufficiently long sample.

## VaR exception rates

| Model | 95% exceptions | 95% observed rate | 99% exceptions | 99% observed rate |
| --- | ---: | ---: | ---: | ---: |
| Historical simulation | 199 / 3,987 | 4.99% | 40 / 3,987 | 1.00% |
| Normal model | 184 / 3,987 | 4.62% | 65 / 3,987 | 1.63% |
| EWMA filtered historical simulation | 201 / 3,987 | 5.04% | 46 / 3,987 | 1.15% |

At the 99% level, the normal model records more exceptions than its 1% target. Its average 99% VaR is 1.51% and average ES is 1.74%, below the corresponding historical estimates of 1.79% VaR and 2.56% ES. This is consistent with the normal model understating tail risk in this sample.

The historical and EWMA models have aggregate 99% exception rates closer to 1%. That alone does not establish that either model is reliable: the exceptions are unevenly distributed through time.

## Exceptions by year at 99% VaR

| Year | Forecast days | Historical | Normal | EWMA filtered historical | Expected at 1% |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2015 | 252 | 7 | 8 | 4 | 2.5 |
| 2018 | 251 | 5 | 12 | 3 | 2.5 |
| 2020 | 253 | 11 | 13 | 6 | 2.5 |
| 2022 | 251 | 5 | 10 | 0 | 2.5 |

The normal model has clusters of exceptions in 2018, 2020, and 2022. Historical simulation also has a cluster in 2020. EWMA has fewer exceptions in those selected years, but had six in 2013 and four in 2014; a few selected years are not enough to rank the models.

## Visual comparison

![Out-of-sample 99% VaR and ES forecasts with exceptions highlighted](figures/var_es_99_backtest.png)

The EWMA model's VaR and ES rise quickly around large return shocks and then decline as those shocks receive less weight. Historical simulation changes in steps as observations enter or leave its rolling window. The normal model's forecasts change more smoothly.

## Limitations and next analysis

- These exception rates are descriptive. The comparison has not yet tested whether exceptions are statistically independent or whether conditional coverage is adequate.
- ES is estimated, but this analysis does not yet use a formal ES backtest. The average loss on VaR exception days is descriptive and should not be treated as an ES validation result.
- A 1,000-day window contains only about 10 observations beyond a 99% empirical quantile, so 99% historical and filtered-tail estimates are noisy.
- The results depend on this portfolio, daily rebalancing assumption, sample period, and data source. They do not identify a universal best model.

Next, add formal VaR exception diagnostics and a suitable ES scoring/backtesting method, then interpret how the models behave across calm and volatile periods.
