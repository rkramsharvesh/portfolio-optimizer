"""
Monte Carlo portfolio optimisation utilities.

This module provides functions to compute asset returns from uploaded price
data, determine the sampling frequency, run a Monte Carlo simulation of
randomly weighted portfolios and identify the optimum portfolios based
on Sharpe ratio and volatility.

The simulation uses historical mean returns and covariance to estimate
expected annualised returns and volatilities.  Sharpe ratios are
calculated against a risk‑free rate supplied by the caller.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Tuple


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Compute percentage returns from price data.

    Parameters
    ----------
    prices : DataFrame
        DataFrame of prices indexed by date.  Each column represents a
        ticker.  Dates should be sorted ascending.

    Returns
    -------
    DataFrame
        DataFrame of percentage returns (rows = dates, columns = tickers).
    """
    returns = prices.pct_change().dropna()
    return returns


def infer_periods_per_year(index: pd.DatetimeIndex) -> float:
    """
    Infer the number of periods per year from a DatetimeIndex.

    Uses `pandas.infer_freq` to guess the frequency.  If the frequency is
    daily or business daily, returns 252; weekly returns 52; monthly
    returns 12.  Defaults to 252 if the frequency cannot be inferred.

    Parameters
    ----------
    index : DatetimeIndex
        Date index of the return series.

    Returns
    -------
    float
        Number of periods per year.
    """
    try:
        freq = pd.infer_freq(index)
    except Exception:
        freq = None
    if not freq:
        return 252.0
    freq = freq.upper()
    if freq.startswith(('B', 'D')):
        return 252.0
    if freq.startswith('W'):
        return 52.0
    if freq.startswith('M'):
        return 12.0
    # Fallback
    return 252.0


def simulate_portfolios(
    returns: pd.DataFrame,
    rf_rate: float,
    n_portfolios: int = 500,
    random_state: int | None = None,
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
    """
    Generate random portfolios and compute their statistics.

    Parameters
    ----------
    returns : DataFrame
        DataFrame of percentage returns for each asset.
    rf_rate : float
        Risk‑free rate expressed as a decimal (e.g., 0.0421 for 4.21 %).
    n_portfolios : int, optional
        Number of random portfolios to simulate, by default 500.
    random_state : int or None, optional
        Seed for the random number generator.

    Returns
    -------
    (DataFrame, Dict[str, Dict[str, float]])
        A tuple containing the simulated portfolios (with columns
        'Return', 'Volatility', 'Sharpe' and one column per ticker for
        weights) and a dictionary with details of the maximum Sharpe and
        minimum volatility portfolios.  Each entry in the dictionary has
        keys 'return', 'volatility', 'sharpe' and 'weights' (mapping
        tickers to weights).
    """
    rng = np.random.default_rng(random_state)
    tickers = returns.columns.tolist()
    n_assets = len(tickers)
    periods = infer_periods_per_year(returns.index)
    mean_returns = returns.mean() * periods
    cov_matrix = returns.cov() * periods

    results = np.zeros((n_portfolios, 3 + n_assets))
    for i in range(n_portfolios):
        # Random weights sum to 1 using Dirichlet distribution
        weights = rng.dirichlet(np.ones(n_assets))
        # Expected return and volatility
        port_return = float(np.dot(weights, mean_returns))
        port_variance = float(np.dot(weights.T, np.dot(cov_matrix, weights)))
        port_vol = np.sqrt(port_variance)
        # Sharpe ratio
        sharpe = (port_return - rf_rate) / port_vol if port_vol > 0 else 0.0
        # Store results: Return, Volatility, Sharpe, weights...
        results[i, 0] = port_return
        results[i, 1] = port_vol
        results[i, 2] = sharpe
        results[i, 3:] = weights

    # Build DataFrame
    columns = ['Return', 'Volatility', 'Sharpe'] + tickers
    df = pd.DataFrame(results, columns=columns)

    # Identify optimal portfolios
    max_sharpe_idx = df['Sharpe'].idxmax()
    min_vol_idx = df['Volatility'].idxmin()

    def extract_portfolio(row: pd.Series) -> Dict[str, float]:
        return {ticker: row[ticker] for ticker in tickers}

    optimal = {
        'max_sharpe': {
            'return': df.loc[max_sharpe_idx, 'Return'],
            'volatility': df.loc[max_sharpe_idx, 'Volatility'],
            'sharpe': df.loc[max_sharpe_idx, 'Sharpe'],
            'weights': extract_portfolio(df.loc[max_sharpe_idx])
        },
        'min_vol': {
            'return': df.loc[min_vol_idx, 'Return'],
            'volatility': df.loc[min_vol_idx, 'Volatility'],
            'sharpe': df.loc[min_vol_idx, 'Sharpe'],
            'weights': extract_portfolio(df.loc[min_vol_idx])
        }
    }
    return df, optimal
