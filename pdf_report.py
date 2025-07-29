"""
PDF report generation using matplotlib.

The report is assembled into a multi-page PDF using
``matplotlib.backends.backend_pdf.PdfPages``.  Each page is created
explicitly and contains text, tables or charts relevant to the
portfolio analysis.  This module is designed to operate without
external PDF libraries, making it suitable for restricted
environments.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


def _create_cover_page(pdf: PdfPages, user_name: str | None, country: str) -> None:
    """Generate the cover page of the report."""
    fig = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
    fig.patch.set_facecolor('white')
    title = 'Portfolio Optimisation Report'
    subtitle = f'Country: {country}'
    date_str = datetime.now().strftime('%B %d, %Y')

    y_pos = 0.8
    fig.text(0.5, y_pos, title, fontsize=28, ha='center', va='center', weight='bold')
    y_pos -= 0.08
    fig.text(0.5, y_pos, subtitle, fontsize=18, ha='center', va='center')
    y_pos -= 0.08
    if user_name:
        fig.text(0.5, y_pos, f'Prepared for: {user_name}', fontsize=14, ha='center', va='center')
        y_pos -= 0.05
    fig.text(0.5, y_pos, f'Date: {date_str}', fontsize=12, ha='center', va='center')
    # Decorative line
    ax = fig.add_axes([0, 0, 1, 1], frameon=False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.plot([0.2, 0.8], [y_pos - 0.05, y_pos - 0.05], color='gray')
    pdf.savefig(fig)
    plt.close(fig)


def _create_summary_page(
    pdf: PdfPages,
    country: str,
    rf: float,
    erp: float,
    crp: float,
    n_portfolios: int,
    tickers: List[str]
) -> None:
    """Generate the executive summary page."""
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor('white')
    y = 0.9
    fig.text(0.5, y, 'Executive Summary', fontsize=20, ha='center', weight='bold')
    y -= 0.06
    summary = (
        f'Based on your selected country {country}, the model used a risk-free rate of '
        f'{rf:.2%}, a mature market ERP of {erp:.2%} and a country risk premium of '
        f'{crp:.2%}. The simulation evaluated {n_portfolios} portfolios using your '
        f'selected assets ({", ".join(tickers)}) to identify the most optimal allocation.'
    )
    fig.text(0.1, y, summary, fontsize=12, va='top', wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def _create_personalized_notes_page(
    pdf: PdfPages,
    user_profile: Dict[str, str]
) -> None:
    """
    Generate a personalized notes page based on risk tolerance,
    investment goal, and investment horizon. Each combination
    yields a unique narrative.
    """
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor('white')
    y = 0.9
    fig.text(0.5, y, 'Personalized Notes', fontsize=20, ha='center', weight='bold')
    y -= 0.06

    # Extract profile fields
    risk = user_profile.get('risk_tolerance', 'Moderate')
    goal = user_profile.get('goal', 'Balanced')
    horizon = user_profile.get('horizon', '1Y')

    # Mapping dictionaries for distinct phrasing
    risk_phrases = {
        'Low':    'You prefer a cautious approach',
        'Moderate':'You are comfortable with a balanced risk profile',
        'High':   'You embrace an aggressive risk stance'
    }
    goal_phrases = {
        'Capital Preservation': 'focus on safeguarding your capital',
        'Long-Term Growth':     'seek sustained growth over time',
        'Balanced':             'aim for a blend of growth and stability',
        'High Risk-High Return':'are targeting high returns despite volatility'
    }
    horizon_phrases = {
        '1Y':   'over a short 1-year horizon',
        '3Y':   'over the next 3 years',
        '5Y':   'over the next 5 years',
        '10+Y': 'over a long-term horizon exceeding 10 years'
    }

    # Build the unique, combined narrative
    line = (
        f"{risk_phrases[risk]} and {goal_phrases[goal]}, "
        f"{horizon_phrases[horizon]}. "
        "The recommended portfolio is designed to honor these preferences by "
        "selecting assets that align with the desired risk-return balance."
    )

    # Write the narrative on the figure
    fig.text(0.1, y, line, fontsize=12, va='top', wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def _create_recommendation_page(
    pdf: PdfPages,
    optimal: Dict[str, float],
    market_data: Dict[str, float]
) -> None:
    """Generate the portfolio recommendation page with a table and pie chart."""
    fig, ax = plt.subplots(2, 1, figsize=(8.27, 11.69), gridspec_kw={'height_ratios': [1, 2]})
    fig.patch.set_facecolor('white')
    fig.suptitle('Portfolio Recommendation', fontsize=20, weight='bold')

    # Top: summary table
    table_data = [
        ['Expected Return', f'{optimal["return"]:.2%}'],
        ['Volatility', f'{optimal["volatility"]:.2%}'],
        ['Sharpe Ratio', f'{optimal["sharpe"]:.2f}'],
        ['Risk-Free Rate', f'{market_data["rf"]:.2%}'],
        ['Mature ERP', f'{market_data["erp"]:.2%}'],
        ['Country RP', f'{market_data["crp"]:.2%}'],
    ]
    table = ax[0].table(
        cellText=table_data,
        colLabels=['Metric', 'Value'],
        cellLoc='left',
        loc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(2)))
    ax[0].axis('off')

    # Bottom: pie chart of allocations
    weights = optimal['weights']
    labels = list(weights.keys())
    values = list(weights.values())
    ax[1].pie(values, labels=labels, autopct=lambda p: f'{p:.1f}%')
    ax[1].set_title('Asset Allocation', fontsize=14)
    pdf.savefig(fig)
    plt.close(fig)


def _create_chart_page(
    pdf: PdfPages,
    sim_df: pd.DataFrame,
    optimal: Dict[str, float]
) -> None:
    """Generate a page with the efficient frontier chart."""
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    fig.patch.set_facecolor('white')
    ax.set_title('Efficient Frontier (colour = Sharpe ratio)', fontsize=16)
    scatter = ax.scatter(sim_df['Volatility'], sim_df['Return'], c=sim_df['Sharpe'], cmap='viridis', s=10)
    # Mark the optimal point
    ax.scatter(optimal['volatility'], optimal['return'], marker='*', color='red', s=150, label='Chosen Portfolio')
    ax.set_xlabel('Volatility')
    ax.set_ylabel('Expected Return')
    fig.colorbar(scatter, ax=ax, label='Sharpe Ratio')
    ax.legend()
    pdf.savefig(fig)
    plt.close(fig)


def generate_pdf_report(
    buffer: io.BytesIO,
    user_profile: Dict[str, str],
    market_data: Dict[str, float],
    optimal: Dict[str, float],
    sim_df: pd.DataFrame,
    n_portfolios: int,
) -> None:
    """
    Create a PDF report and write it into a bytes buffer.

    Parameters
    ----------
    buffer : BytesIO
        The buffer to which the PDF will be written.
    user_profile : dict
        Contains 'name', 'country', 'risk_tolerance', 'goal', 'horizon'.
    market_data : dict
        Contains 'rf', 'erp', 'crp'.
    optimal : dict
        The recommended portfolio with keys 'return', 'volatility', 'sharpe', 'weights'.
    sim_df : DataFrame
        DataFrame with simulation results.
    n_portfolios : int
        Number of portfolios simulated.
    """
    user_name = user_profile.get('name') or None
    country = user_profile.get('country', '')

    pdf = PdfPages(buffer)
    try:
        _create_cover_page(pdf, user_name, country)
        _create_summary_page(
            pdf, country,
            market_data['rf'], market_data['erp'], market_data['crp'],
            n_portfolios, list(sim_df.columns[3:])
        )
        _create_personalized_notes_page(pdf, user_profile)
        _create_recommendation_page(pdf, optimal, market_data)
        _create_chart_page(pdf, sim_df, optimal)
    finally:
        pdf.close()
    buffer.seek(0)
