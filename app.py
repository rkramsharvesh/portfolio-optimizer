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

from data_loader import list_countries, get_country_data, mature_market_erp
from utils import load_price_file, align_price_series, parse_ticker_from_filename
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
    st.sidebar.write(f'Equity Risk Premium (ERP): {country_data.erp:.2f}%')
    st.sidebar.write(f'Country Risk Premium (CRP): {country_data.crp:.2f}%')
    # Dynamically calculate Mature ERP = ERP - CRP
    # Dr. Damodaran’s ERP = Mature ERP + CRP → So we derive Mature ERP = ERP - CRP
    derived_mature_erp = country_data.erp - country_data.crp
    st.sidebar.write(f'Mature ERP (derived): {derived_mature_erp:.2f}%')
    rf_input = st.sidebar.number_input('Risk-Free Rate (%)', min_value=0.0, max_value=100.0,
                                       value=float(country_data.rf), step=0.01,
                                       help='Override the default risk-free rate for your country (if needed).')

    # Monte Carlo settings
    st.sidebar.subheader('Simulation Settings')
    n_portfolios = st.sidebar.number_input('Number of Portfolios to simulate', min_value=100, max_value=5000,
                                           value=500, step=100)
    seed = st.sidebar.number_input('Random Seed (optional)', min_value=0, max_value=2**31-1,
                                    value=0, step=1
                                    help='Set a random number to get the same simulation results every time. Leave as 0 for random results on each run.')

    st.subheader('Upload Historical Price Data')
    st.write('Upload one CSV file per ticker (minimum of 3 and a maximum of 10). Files must be named **TICKER_prices.csv** and \
contain a `Date` column (YYYY‑MM‑DD) and a `Close` or `Adj Close` price column.')
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
                    # Compute returns and run simulation when user clicks button
                    if st.button('Run Monte Carlo Simulation'):
                        with st.spinner('Running simulation...'):
                            returns = compute_returns(prices_df)
                            sim_df, optimal_dict = simulate_portfolios(
                                returns,
                                rf_rate=rf_input / 100.0,
                                n_portfolios=int(n_portfolios),
                                random_state=int(seed) if seed else None,
                            )
                        # Show summary
                        max_sharpe = optimal_dict['max_sharpe']
                        min_vol = optimal_dict['min_vol']
                        st.subheader('Optimal Portfolios')
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric('Max Sharpe Return', f'{max_sharpe["return"]:.2%}')
                            st.metric('Max Sharpe Volatility', f'{max_sharpe["volatility"]:.2%}')
                            st.metric('Max Sharpe Ratio', f'{max_sharpe["sharpe"]:.2f}')
                        with col2:
                            st.metric('Min Volatility Return', f'{min_vol["return"]:.2%}')
                            st.metric('Min Volatility', f'{min_vol["volatility"]:.2%}')
                            st.metric('Min Vol Sharpe Ratio', f'{min_vol["sharpe"]:.2f}')
                        # Efficient frontier plot
                        st.subheader('Efficient Frontier')
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(8, 6))
                        scatter = ax.scatter(sim_df['Volatility'], sim_df['Return'], c=sim_df['Sharpe'], cmap='viridis', s=10)
                        ax.scatter(max_sharpe['volatility'], max_sharpe['return'], marker='*', color='red', s=150, label='Max Sharpe')
                        ax.scatter(min_vol['volatility'], min_vol['return'], marker='X', color='blue', s=100, label='Min Volatility')
                        ax.set_xlabel('Volatility')
                        ax.set_ylabel('Expected Return')
                        ax.set_title('Efficient Frontier')
                        ax.legend()
                        cbar = fig.colorbar(scatter, ax=ax)
                        cbar.set_label('Sharpe Ratio')
                        st.pyplot(fig)
                        # Portfolio allocation table
                        st.subheader('Portfolio Allocation (Max Sharpe)')
                        allocation_df = pd.DataFrame.from_dict(max_sharpe['weights'], orient='index', columns=['Weight'])
                        allocation_df['Weight'] = allocation_df['Weight'].map(lambda x: f'{x:.2%}')
                        st.table(allocation_df.T)
                        # Download buttons
                        csv_data = sim_df.to_csv(index=False).encode('utf-8')
                        st.download_button('📄 Download Simulation CSV', data=csv_data,
                                           file_name='simulation_results.csv', mime='text/csv')
                        # Generate PDF report on the fly
                        buffer = io.BytesIO()
                        user_profile = {
                            'name': name,
                            'country': country,
                            'risk_tolerance': risk_tolerance,
                            'goal': investment_goal,
                            'horizon': investment_horizon,
                        }
                        market_data = {
                            'rf': rf_input / 100.0,
                            'erp': country_data.mature_erp / 100.0,  # mature ERP as decimal
                            'crp': country_data.crp / 100.0,
                        }
                        generate_pdf_report(buffer, user_profile, market_data, max_sharpe, sim_df, int(n_portfolios))
                        st.download_button('📑 Download PDF Report', data=buffer.getvalue(),
                                           file_name='portfolio_report.pdf', mime='application/pdf')
    # Footer citation
    st.markdown('---')
    st.markdown(
        'Data source for equity and country risk premium: Aswath Damodaran’s January 2025 update '
    )


if __name__ == '__main__':
    main()
