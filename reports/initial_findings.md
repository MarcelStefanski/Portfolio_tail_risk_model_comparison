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

## Formal VaR diagnostics and joint VaR-ES scores

The summary now includes the Kupiec unconditional-coverage test, which checks whether the exception frequency matches its target, and Christoffersen's first-order independence and conditional-coverage tests, which check whether exceptions cluster over time. The likelihood-ratio p-values use their asymptotic chi-square distributions. At the 5% level, the results are:

### 95% VaR

| Model | UC p-value | Independence p-value | Conditional-coverage p-value | Mean FZ0 score |
| --- | ---: | ---: | ---: | ---: |
| Historical simulation | 0.980 | <0.001 | <0.001 | -4.172 |
| Normal model | 0.259 | <0.001 | <0.001 | -4.144 |
| EWMA filtered historical simulation | 0.905 | 0.018 | 0.060 | **-4.345** |

### 99% VaR

| Model | UC p-value | Independence p-value | Conditional-coverage p-value | Mean FZ0 score |
| --- | ---: | ---: | ---: | ---: |
| Historical simulation | 0.984 | <0.001 | <0.001 | -3.611 |
| Normal model | <0.001 | <0.001 | <0.001 | -3.373 |
| EWMA filtered historical simulation | 0.341 | 0.002 | 0.005 | **-3.894** |

At 95%, none of the models is rejected by the unconditional-coverage test, but historical and normal exceptions are strongly dependent. EWMA's independence test also rejects at 5%; its combined conditional-coverage p-value is 0.060, just above that cutoff. At 99%, historical and EWMA exception counts are consistent with their 1% target, while the normal model has too many exceptions. All three models show dependent exceptions, so none passes the combined conditional-coverage test.

The FZ0 column is the mean joint VaR-ES score for positive loss forecasts; a lower score is better. EWMA has the lowest score at both levels in this sample. This is a comparative score, not a standalone statistical acceptance test for ES, so it does not establish that EWMA is universally best. The score follows the joint VaR and ES scoring framework of [Fissler, Ziegel, and Gneiting](https://arxiv.org/abs/1507.00244). The coverage tests follow [Kupiec](https://fedinprint.org/item/fedgfe/34596/original) and [Christoffersen](https://users.ssc.wisc.edu/~bhansen/718/Christoffersen1998.pdf).

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

- The likelihood-ratio p-values are asymptotic. In particular, there are only 40 to 65 exceptions at 99%, so those test results should be interpreted cautiously.
- The mean FZ0 scores rank joint VaR-ES forecasts in this sample but do not test whether score differences are statistically significant.
- A 1,000-day window contains only about 10 observations beyond a 99% empirical quantile, so 99% historical and filtered-tail estimates are noisy.
- The results depend on this portfolio, daily rebalancing assumption, sample period, and data source. They do not identify a universal best model.

The next useful extension is to compare model performance across calm and volatile periods and to examine whether the conclusions are sensitive to the rolling-window length.
