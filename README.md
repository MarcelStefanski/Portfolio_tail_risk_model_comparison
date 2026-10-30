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
3. A volatility-aware model, such as filtered historical simulation using GARCH

For each method, the project will estimate 95% and 99% VaR and ES. The estimates will be tested against returns that were not used to fit the models. The comparison will consider how often losses exceed VaR, the size of losses beyond VaR, and how results differ across market conditions.

## Planned outputs

- Reproducible analysis code
- Charts comparing model estimates with realized portfolio losses
- Backtesting results and a discussion of model limitations
- A concise report explaining the methods and findings

## Skills demonstrated

- Financial mathematics and portfolio return calculations
- Statistical modeling of extreme losses
- Time-series analysis and out-of-sample evaluation
- Data analysis and clear communication of quantitative results

## Project status

Initial data and portfolio scope selected. The model implementation and backtesting design will be developed next.
