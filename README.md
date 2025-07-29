# Portfolio Optimizer Web Application

This project implements an offline‑friendly Streamlit application for exploring
modern portfolio theory using Monte Carlo simulation.  The app uses the latest
country‑specific equity risk premia (ERP) and country risk premia (CRP)
from Professor Aswath Damodaran’s 2025 data set and combines them with user
supplied price histories to construct efficient frontiers and recommend
optimal allocations.  Because network access is limited in this environment,
all stock price data must be provided by the user as CSV files, and
reasonable default risk‑free rates are baked into the application and can be
overridden at run time.

## Features

* **User profile form** – Collects the investor’s name (optional), country,
  risk tolerance (Low/Moderate/High), investment goal and horizon.  Country
  selection drives the choice of ERP/CRP and the default risk‑free rate.
* **Price data upload** – Accepts one or more CSV files named
  `TICKER_prices.csv`.  Each file must contain at least a `Date` column
  (in ISO format, e.g. `YYYY‑MM‑DD`, `DD-MM-YYYY`) and a `Close` / `Adj Close` / `Price` column.  The
  app automatically computes percentage returns, aligns them on common dates
  and uses the resulting return matrix in the optimisation.
* **Market assumptions** – For the selected country the app displays the
  risk‑free rate (`Rf`), the mature market equity risk premium and the
  country risk premium.  These values are pulled from a static copy of
  Damodaran’s January 2025 data.  Users may override the risk‑free rate.
* **Monte Carlo simulation** – Simulates a configurable number of random
  portfolios.  For each portfolio the algorithm selects random weights,
  computes expected return (using historical returns for the supplied
  securities) and volatility (based on the covariance matrix).  Sharpe
  ratios are computed using the risk‑free rate.
* **Visualisation** – Displays an efficient frontier coloured by Sharpe ratio
  and identifies the maximum Sharpe and minimum volatility portfolios.  A
  summary table lists the key statistics and allocations for the optimal
  portfolio.
* **Personalised PDF report** – Generates a multi‑page PDF using
  `matplotlib`’s `PdfPages`.  The report includes a cover page, an
  executive summary with the selected country assumptions, a portfolio
  recommendation section with charts and tables, personalised notes based
  on the user’s profile and an interpretation of the results.
* **Downloads** – Users can download the simulated portfolio results as
  CSV and the generated PDF report.

## Running the application

**Web App**

*Live Demo:* [https://rkramsharvesh-portfolio-optimizer.streamlit.app/](https://rkramsharvesh-portfolio-optimizer.streamlit.app/)

**Running Locally**

1. Ensure the environment has Python 3.11 and the following libraries
   available: `streamlit`, `pandas`, `numpy`, and `matplotlib`.  These are
   included in the base environment used by this project.  No external
   network calls are required.
2. Launch the app from the root of the repository:

   ```bash
   streamlit run portfolio_optimizer/app.py
   ```

3. Use the sidebar to fill in your investor profile and upload your price
   history CSV files.  The app will parse the files, run the simulation and
   display the results.

## Project structure

```
portfolio_optimizer/
│
├── app.py                # Main Streamlit application
├── data_loader.py        # Loads Damodaran ERP/CRP and default risk‑free rates
├── monte_carlo.py        # Portfolio simulation functions
├── pdf_report.py         # PDF report generation using matplotlib
├── utils.py              # Helper functions
└── README.md             # This file
```

## Data files

Due to network restrictions the application does **not** fetch stock price
data from live APIs.  Instead the user must supply one CSV per ticker using
the naming convention `TICKER_prices.csv` (e.g. `AAPL_prices.csv`).  Each
CSV should contain a `Date` column (formatted as `YYYY‑MM‑DD`) and a
`Close` or `Adj Close` column.  Additional columns are ignored.  The app
computes returns using `pct_change()` and aligns dates across all uploaded
tickers.  Example structure:

```csv
Date,Close,Adj Close
2024-01-01,172.00,171.94
2024-01-02,175.35,175.30
...
```

If the date format in your files differs, please adjust it to ISO
(`YYYY‑MM‑DD`) before uploading.

## Risk‑free rates

Default risk‑free rates are embedded in `data_loader.py` for a handful of
countries based on Professor Damodaran’s January 2025 data.  For example

| Country          | Default Rf |
|------------------|-----------:|
| India            |     6.92 % |
| United States    |     4.21 % |
| United Kingdom   |     4.50 % |
| Germany          |     2.50 % |
| Japan            |     0.35 % |
| China            |     2.70 % |
| Canada           |     3.10 % |

These serve as starting values and may be overridden in the app’s user
interface.
