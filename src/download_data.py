"""Download market data and calculate returns for the example portfolio.

The portfolio holds 60% SPY and 40% TLT, rebalanced to those weights each day.
Prices are adjusted by yfinance for distributions and splits.
"""

from pathlib import Path

import pandas as pd
import yfinance as yf


START_DATE = "2007-01-01"
PORTFOLIO_WEIGHTS = {"SPY": 0.60, "TLT": 0.40}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def download_adjusted_close() -> pd.DataFrame:
    """Download adjusted daily closing prices for the portfolio assets."""
    downloaded = yf.download(
        tickers=list(PORTFOLIO_WEIGHTS),
        start=START_DATE,
        interval="1d",
        auto_adjust=True,
        group_by="column",
        progress=False,
    )

    if downloaded is None or downloaded.empty:
        raise RuntimeError("No price data was returned. Check the connection and tickers.")

    if isinstance(downloaded.columns, pd.MultiIndex):
        close_prices = None
        for level in range(downloaded.columns.nlevels):
            if "Close" in downloaded.columns.get_level_values(level):
                close_prices = downloaded.xs("Close", axis=1, level=level)
                break
        if close_prices is None:
            raise ValueError("The downloaded data did not contain closing prices.")
    elif "Close" in downloaded.columns:
        # This branch supports a single-ticker response if the asset list changes.
        ticker = next(iter(PORTFOLIO_WEIGHTS))
        close_prices = downloaded[["Close"]].rename(columns={"Close": ticker})
    else:
        raise ValueError("The downloaded data did not contain closing prices.")

    missing_tickers = set(PORTFOLIO_WEIGHTS).difference(close_prices.columns)
    if missing_tickers:
        raise ValueError(f"Missing price data for: {', '.join(sorted(missing_tickers))}")

    return close_prices.loc[:, list(PORTFOLIO_WEIGHTS)].dropna(how="any")


def main() -> None:
    """Save adjusted prices and asset/portfolio returns as CSV files."""
    adjusted_close = download_adjusted_close()
    asset_returns = adjusted_close.pct_change(fill_method=None).dropna()
    weights = pd.Series(PORTFOLIO_WEIGHTS)
    portfolio_returns = asset_returns.mul(weights).sum(axis=1).rename("portfolio_return")
    returns = asset_returns.join(portfolio_returns)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    prices_path = RAW_DATA_DIR / "adjusted_close.csv"
    returns_path = PROCESSED_DATA_DIR / "portfolio_returns.csv"
    adjusted_close.to_csv(prices_path, index_label="date")
    returns.to_csv(returns_path, index_label="date")

    print(f"Saved {len(adjusted_close)} daily price rows to {prices_path}")
    print(f"Saved {len(returns)} daily return rows to {returns_path}")
    print(f"Date range: {returns.index.min().date()} to {returns.index.max().date()}")


if __name__ == "__main__":
    main()
