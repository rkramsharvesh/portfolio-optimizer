"""
Data loader for country‑specific risk premia and default risk‑free rates.

This module encapsulates all logic for retrieving market assumptions
required by the portfolio optimiser.  Since direct network access is
restricted in the execution environment, the data here is based on
Professor Aswath Damodaran’s January 2025 country risk premium table
(scraped manually into this file)【90480415847186†L0-L34】.  For each
supported country we store the equity risk premium (ERP), the country
risk premium (CRP) and a reasonable default risk‑free rate (Rf).

The mature market equity risk premium (ERP) is assumed to be constant
across countries (4.33 %)【90480415847186†L21-L33】.  The CRP varies by
country.  Risk‑free rates are approximate 2025 10‑year government bond
yields for each country and may be overridden by the user in the UI.

Usage:

>>> from data_loader import get_country_data, list_countries
>>> params = get_country_data('India')
>>> params['crp']  # 2.93
>>> list_countries()

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CountryRiskData:
    """Container for market assumptions for a single country."""
    country: str
    erp: float  # equity risk premium (mature + country)
    crp: float  # country risk premium (CRP)
    rf: float   # default risk‑free rate (can be overridden)

    @property
    def mature_erp(self) -> float:
        """Return the mature market ERP (equity risk premium minus CRP)."""
        return self.erp - self.crp


# ---------------------------------------------------------------------------
# Static table of country risk premia.  Values are taken from the January
# 2025 update of Professor Damodaran’s country risk premium table.  Each
# entry contains the total equity risk premium (ERP), the country risk
# premium (CRP) and a default risk‑free rate.  The mature ERP is obtained
# by subtracting CRP from ERP【90480415847186†L21-L34】.
_COUNTRY_DATA: Dict[str, CountryRiskData] = {
    # North America / Mature markets
    'United States': CountryRiskData('United States', erp=4.33, crp=0.00, rf=4.21),  # 【325874986942418†L6480-L6484】
    'Canada':        CountryRiskData('Canada',        erp=4.33, crp=0.00, rf=3.10),
    'Mexico':        CountryRiskData('Mexico',        erp=7.67, crp=3.34, rf=9.00),
    # Europe
    'United Kingdom': CountryRiskData('United Kingdom', erp=5.13, crp=0.80, rf=4.50),  # 【325874986942418†L6472-L6476】
    'Germany':       CountryRiskData('Germany',       erp=4.33, crp=0.00, rf=2.50),  # 【325874986942418†L5501-L5504】
    'France':        CountryRiskData('France',        erp=4.86, crp=0.53, rf=2.60),
    'Italy':         CountryRiskData('Italy',         erp=7.26, crp=2.93, rf=4.00),  # same CRP as India
    'Spain':         CountryRiskData('Spain',         erp=5.46, crp=1.13, rf=3.20),
    'Netherlands':   CountryRiskData('Netherlands',   erp=4.86, crp=0.53, rf=2.50),
    'Switzerland':   CountryRiskData('Switzerland',   erp=5.13, crp=0.80, rf=1.00),
    'Russia':        CountryRiskData('Russia',        erp=16.35, crp=12.02, rf=9.00),
    # Asia
    'India':         CountryRiskData('India',         erp=7.26, crp=2.93, rf=6.92),  # 【325874986942418†L5622-L5625】
    'China':         CountryRiskData('China',         erp=5.27, crp=0.94, rf=2.70),  # 【325874986942418†L5622-L5625】
    'Japan':         CountryRiskData('Japan',         erp=5.27, crp=0.94, rf=0.35),  # 【325874986942418†L5702-L5705】
    'Australia':     CountryRiskData('Australia',     erp=4.33, crp=0.00, rf=3.80),
    'Singapore':     CountryRiskData('Singapore',     erp=4.99, crp=0.66, rf=3.10),
    'South Korea':   CountryRiskData('South Korea',   erp=6.87, crp=2.54, rf=3.30),
    'Indonesia':     CountryRiskData('Indonesia',     erp=6.87, crp=2.54, rf=7.00),
    # South America
    'Brazil':        CountryRiskData('Brazil',        erp=7.67, crp=3.34, rf=10.00),  # 【325874986942418†L5501-L5504】
    'Argentina':     CountryRiskData('Argentina',     erp=20.35, crp=16.02, rf=35.00),
    'Chile':         CountryRiskData('Chile',         erp=5.46, crp=1.13, rf=4.00),
    # Africa
    'South Africa':  CountryRiskData('South Africa',  erp=13.01, crp=8.68, rf=11.00),
    'Egypt':         CountryRiskData('Egypt',         erp=14.34, crp=10.01, rf=15.00),
    # Middle East
    'United Arab Emirates': CountryRiskData('United Arab Emirates', erp=4.99, crp=0.66, rf=3.40),
    'Saudi Arabia':  CountryRiskData('Saudi Arabia',  erp=5.27, crp=0.94, rf=4.50),
    'Turkey':        CountryRiskData('Turkey',        erp=16.35, crp=12.02, rf=25.00),
}


def list_countries() -> List[str]:
    """Return a sorted list of country names available in the data set."""
    return sorted(_COUNTRY_DATA.keys())


def get_country_data(country: str) -> CountryRiskData:
    """
    Retrieve the risk data for a given country.

    Parameters
    ----------
    country : str
        The name of the country (case sensitive).  Must be one of the
        values returned by ``list_countries()``.

    Returns
    -------
    CountryRiskData
        A dataclass instance containing the ERP, CRP and default Rf.

    Raises
    ------
    KeyError
        If the country is not recognised.
    """
    if country not in _COUNTRY_DATA:
        raise KeyError(f"Unknown country: {country}. Available: {list_countries()}")
    return _COUNTRY_DATA[country]


def mature_market_erp() -> float:
    """
    Return the mature market equity risk premium.  This value is assumed
    constant across countries and equals the ERP of a country with zero
    country risk premium【90480415847186†L21-L34】.
    """
    # Pick the United States entry as representative; ERP minus CRP yields 4.33 %.
    us = _COUNTRY_DATA['United States']
    return us.mature_erp
