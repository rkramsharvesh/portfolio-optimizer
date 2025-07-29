"""
Utility functions for the portfolio optimiser app.

This module contains helpers for parsing uploaded CSV files into
price series, aligning returns, and other small conveniences.
"""

from __future__ import annotations

import os
from typing import Dict, Tuple, List, IO

import pandas as pd


def parse_ticker_from_filename(filename: str) -> str:
    """
    Extract the ticker from a filename of the form ``TICKER_prices.csv``.

    Parameters
    ----------
    filename : str
        The name of the uploaded file.

    Returns
    -------
    str
        The ticker symbol.

    Notes
    -----
    The function is case sensitive and assumes that the ticker does not
    contain underscores beyond the suffix ``_prices``.
    """
    base = os.path.basename(filename)
    name, _ = os.path.splitext(base)
    if name.lower().endswith('_prices'):
        return name[:-7]  # remove '_prices'
    return name


def load_price_file(file_obj: IO[bytes], filename: str) -> pd.Series:
    """
    Load a price CSV file into a pandas Series.

    Parameters
    ----------
    file_obj : file-like
        File object returned by Streamlit's file uploader.
    filename : str
        The original filename, used to extract the ticker.

    Returns
    -------
    Series
        Time series of prices indexed by datetime. The series name is the ticker.

    Raises
    ------
    ValueError
        If the file does not contain a recognised price column or date format.
    """
    ticker = parse_ticker_from_filename(filename)
    df = pd.read_csv(file_obj)

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Identify the price column (Close/Adj Close/Price)
    price_col = None
    for candidate in ['Price', 'Adj Close', 'Adj close', 'AdjClose', 'Close', 'close', 'Adj Close*', 'Adj_Close']:
        if candidate in df.columns:
            price_col = candidate
            break
    if price_col is None:
        raise ValueError(f"File {filename} does not contain a 'Close', 'Adj Close', or 'Price' column.")

    # Parse dates using multiple formats
    if 'Date' not in df.columns:
        raise ValueError(f"File {filename} does not contain a 'Date' column.")
    try:
        df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    except Exception:
        try:
            df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
        except Exception:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')

    # Drop rows with unrecognized dates
    df = df.dropna(subset=['Date'])
    if df.empty:
        raise ValueError(f"Could not parse dates in file {filename}. Please use YYYY-MM-DD or DD-MM-YYYY format.")

    # Sort by date and extract the price series
    df[price_col] = df[price_col].astype(str).str.replace(',', '', regex=False).astype(float)
    series = df.set_index('Date')[price_col]

    series.name = ticker

    return series


def align_price_series(series_list: List[pd.Series]) -> pd.DataFrame:
    """
    Align multiple price series on their intersection of dates.

    Parameters
    ----------
    series_list : list of Series
        List of price series to align.

    Returns
    -------
    DataFrame
        DataFrame of aligned prices (dates as index, tickers as columns).
    """
    if not series_list:
        return pd.DataFrame()
    df = pd.concat(series_list, axis=1, join='inner')
    return df
