"""
Streamlit application for portfolio optimisation using Monte Carlo simulation.

The app collects an investor profile, accepts uploaded price CSV files for
each asset, computes returns, runs a Monte Carlo simulation of random
portfolio allocations and displays the efficient frontier.  Users can
download the simulation results as CSV and a personalised PDF report.
"""

from __future__ import annotations

import io
from typing import List

import streamlit as st
import pandas as pd

from data_loader import list_countries, get_country_data
from utils import load_price_file, align_price_series
from monte_carlo import compute_returns, simulate_portfolios
from pdf_report import generate_pdf_report


def main() -> None:
    st.set_page_config(page_title='Portfolio Optimiser', layout='wide')
    st.title('Portfolio Optimisation using Monte Carlo Simulation')

    # Sidebar: investor profile
    st.sidebar.header('Investor Profile')
    name = st.sidebar.text_input('Name (optional)')
    countries = list_countries()
    default_country_index = countries.index('India') if 'India' in countries else 0
    country = st.sidebar.selectbox('Country', countries, index=default_country_index)
    risk_tolerance = st.sidebar.selectbox('Risk Tolerance', ['Low', 'Moderate', 'High'])
    investment_goal = st.sidebar.selectbox('Investment Goal', [
        'Long-Term Growth', 'Capital Preservation', 'Balanced', 'High Risk-High Return'
    ])
    investment_horizon = st.sidebar.selectbox('Investment Horizon', ['1Y', '3Y', '5Y', '10+Y'])

    # Market assumptions
    country_data = get_country_data(country)
    st.sidebar.subheader('Market Assumptions')
    st.sidebar.write(f'Mature ERP (derived): {country_data.mature_erp:.2f}%')
    st.sidebar.write(f'Country Risk Premium (CRP): {country_data.crp:.2f}%')
    st.sidebar.write(f'Equity Risk Premium (ERP): {country_data.erp:.2f}%')
    rf_input = st.sidebar.number_input(
        'Risk-Free Rate (%)',
        min_value=0.0, max_value=100.0,
        value=float(country_data.rf), step=0.01,
        help='Override the default risk-free rate for your country (if needed).'
    )

    # Monte Carlo settings
    st.sidebar.subheader('Simulation Settings')
    n_portfolios = st.sidebar.number_input(
        'Number of Portfolios to simulate',
        min_value=100, max_value=5000,
        value=500, step=100
    )
    seed = st.sidebar.number_input(
        'Random Seed (optional)',
        min_value=0, max_value=2**31 - 1,
        value=0, step=1,
        help='Set a random number to get the same simulation results every time. '
             'Leave as 0 for random results on each run.'
    )

    st.subheader('Upload Historical Price Data')
    st.write(
        "Upload one CSV file per ticker (min 3, max 10). "
        "Files must be named **TICKER_prices.csv** and contain a `Date` column "
        "(YYYY-MM-DD or DD-MM-YYYY) and a `Close`, `Adj Close` or `Price` column."
    )
    uploaded_files = st.file_uploader('Upload CSV files', type=['csv'], accept_multiple_files=True)

    if uploaded_files:
        tickers: List[str] = []
        price_series = []
        error_files = []

        for file in uploaded_files:
            try:
                series = load_price_file(file, file.name)
                tickers.append(series.name)
                price_series.append(series)
            except Exception as e:
                error_files.append((file.name, str(e)))

        if error_files:
            st.error('Some files could not be processed:')
            for fname, err in error_files:
                st.write(f'• {fname}: {err}')

        if price_series:
            if not (3 <= len(price_series) <= 10):
                st.warning('Please upload between 3 and 10 tickers.')
            else:
                prices_df = align_price_series(price_series)
                if prices_df.empty:
                    st.error('No overlapping dates found across the uploaded files.')
                else:
                    st.success('Price data loaded successfully!')
                    st.write(f'Aligned data contains {prices_df.shape[0]} observations.')

                    if st.button('Run Monte Carlo Simulation'):
                        with st.spinner('Running simulation...'):
                            returns = compute_returns(prices_df)
                            sim_df, optimal_dict = simulate_portfolios(
                                returns,
                                rf_rate=rf_input / 100.0,
                                n_portfolios=int(n_portfolios),
                                random_state=int(seed) if seed else None,
                            )

                        # === Horizon Scaling ===
                        try:
                            h = int(investment_horizon.rstrip('Y').rstrip('+'))
                        except ValueError:
                            h = 1
                        sim_df['Return_h'] = (1 + sim_df['Return']) ** h - 1
                        sim_df['Volatility_h'] = sim_df['Volatility'] * (h ** 0.5)
                        rf_rate = rf_input / 100.0
                        sim_df['Sharpe_h'] = (
                            sim_df['Return_h'] - rf_rate * h
                        ) / sim_df['Volatility_h']

                        # === Apply Risk Tolerance Filter ===
                        if risk_tolerance == 'Low':
                            vol_thresh = sim_df['Volatility_h'].quantile(0.25)
                            candidate_df = sim_df[sim_df['Volatility_h'] <= vol_thresh]
                            rt_label = 'Low Risk'
                        elif risk_tolerance == 'High':
                            candidate_df = sim_df
                            rt_label = 'High Risk'
                        else:  # Moderate
                            candidate_df = sim_df
                            rt_label = 'Moderate Risk'

                        # === Select by Investment Goal within candidate_df ===
                        if investment_goal == 'Capital Preservation':
                            idx = candidate_df['Volatility_h'].idxmin()
                            goal_label = 'Min Volatility'
                        elif investment_goal == 'High Risk-High Return':
                            idx = candidate_df['Return_h'].idxmax()
                            goal_label = 'High Return'
                        elif investment_goal == 'Long-Term Growth':
                            idx = candidate_df['Sharpe_h'].idxmax()
                            goal_label = 'Max Sharpe'
                        else:  # Balanced
                            med_vol = candidate_df['Volatility_h'].median()
                            idx = (candidate_df['Volatility_h'] - med_vol).abs().idxmin()
                            goal_label = 'Balanced'

                        row = sim_df.loc[idx]
                        chosen = {
                            'weights': {t: row[t] for t in tickers},
                            'return': row['Return_h'],
                            'volatility': row['Volatility_h'],
                            'sharpe': row['Sharpe_h'],
                        }

                        # === Display Recommended Portfolio ===
                        st.subheader(f'Recommended Portfolio ({rt_label} + {goal_label})')
                        c1, c2 = st.columns(2)
                        with c1:
                            st.metric('Return', f'{chosen["return"]:.2%}')
                            st.metric('Volatility', f'{chosen["volatility"]:.2%}')
                        with c2:
                            st.metric('Sharpe Ratio', f'{chosen["sharpe"]:.2f}')

                        # === Efficient Frontier (Horizon-Scaled) ===
                        st.subheader('Efficient Frontier')
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(8, 6))
                        sc = ax.scatter(
                            sim_df['Volatility_h'], sim_df['Return_h'],
                            c=sim_df['Sharpe_h'], cmap='viridis', s=10
                        )
                        ax.scatter(
                            chosen['volatility'], chosen['return'],
                            marker='*', color='red', s=150,
                            label=f'Chosen ({rt_label}+{goal_label})'
                        )
                        ax.set_xlabel('Volatility (horizon scaled)')
                        ax.set_ylabel('Return (horizon scaled)')
                        ax.set_title('Efficient Frontier')
                        ax.legend()
                        cbar = fig.colorbar(sc, ax=ax)
                        cbar.set_label('Sharpe Ratio (horizon scaled)')
                        st.pyplot(fig)

                        # === Allocation Table ===
                        st.subheader('Portfolio Allocation')
                        alloc_df = pd.DataFrame.from_dict(
                            chosen['weights'], orient='index', columns=['Weight']
                        )
                        alloc_df['Weight'] = alloc_df['Weight'].map(lambda x: f'{x:.2%}')
                        st.table(alloc_df.T)

                        # === Download Simulation CSV ===
                        csv_data = sim_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            '📄 Download Simulation CSV',
                            data=csv_data,
                            file_name='simulation_results.csv',
                            mime='text/csv'
                        )

                        # === Generate PDF Report ===
                        buffer = io.BytesIO()
                        user_profile = {
                            'name': name,
                            'country': country,
                            'risk_tolerance': risk_tolerance,
                            'goal': investment_goal,
                            'horizon': investment_horizon,
                        }
                        market_data = {
                            'rf': rf_rate,
                            'erp': country_data.erp / 100.0,
                            'crp': country_data.crp / 100.0,
                        }
                        generate_pdf_report(
                            buffer, user_profile, market_data,
                            chosen, sim_df, int(n_portfolios)
                        )
                        st.download_button(
                            '📑 Download PDF Report',
                            data=buffer.getvalue(),
                            file_name='portfolio_report.pdf',
                            mime='application/pdf'
                        )

    # Footer citation
    st.markdown('---')
    st.markdown(
        'Data source for equity and country risk premiums: Aswath Damodaran’s January 2025 update.'
    )


if __name__ == '__main__':
    main()
