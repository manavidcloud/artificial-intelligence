"""Currency conversion utilities for FinOps Dashboard."""
import requests
import streamlit as st

# Fallback static rates (1 USD = X currency) — updated May 2025
_STATIC_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.93,
    "GBP": 0.79,
    "INR": 83.5,
    "TRY": 38.5,
    "AUD": 1.58,
    "CAD": 1.38,
    "CHF": 0.91,
    "JPY": 155.0,
    "SGD": 1.35,
    "AED": 3.67,
    "SAR": 3.75,
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "TRY": "₺",
    "AUD": "A$",
    "CAD": "C$",
    "CHF": "Fr",
    "JPY": "¥",
    "SGD": "S$",
    "AED": "AED ",
    "SAR": "SAR ",
}

CURRENCY_LABELS: dict[str, str] = {
    "USD": "USD — US Dollar",
    "EUR": "EUR — Euro",
    "GBP": "GBP — British Pound",
    "INR": "INR — Indian Rupee",
    "TRY": "TRY — Turkish Lira",
    "AUD": "AUD — Australian Dollar",
    "CAD": "CAD — Canadian Dollar",
    "CHF": "CHF — Swiss Franc",
    "JPY": "JPY — Japanese Yen",
    "SGD": "SGD — Singapore Dollar",
    "AED": "AED — UAE Dirham",
    "SAR": "SAR — Saudi Riyal",
}

DEFAULT_CURRENCY = "USD"


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_rates() -> dict[str, float]:
    """Fetch live rates from USD via frankfurter.app (free, no API key). 1-hour cache."""
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest?from=USD",
            timeout=5,
        )
        resp.raise_for_status()
        rates = resp.json().get("rates", {})
        rates["USD"] = 1.0
        return rates
    except Exception:
        return _STATIC_RATES.copy()


def convert(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert amount between currencies using USD as the base."""
    fc = (from_currency or "USD").upper()
    tc = (to_currency or "USD").upper()
    if fc == tc:
        return amount
    rates = _fetch_rates()
    # amount → USD → target
    in_usd = amount / rates.get(fc, 1.0)
    return in_usd * rates.get(tc, 1.0)


def fmt(amount: float, currency: str) -> str:
    """Format a monetary amount with its currency symbol."""
    symbol = CURRENCY_SYMBOLS.get(currency.upper(), currency + " ")
    if currency.upper() == "JPY":
        return f"{symbol}{amount:,.0f}"
    return f"{symbol}{amount:,.2f}"


def currency_selector(key: str = "_currency") -> str:
    """Render currency selector in sidebar. Returns selected currency code."""
    current = st.session_state.get(key, DEFAULT_CURRENCY)
    options = list(CURRENCY_LABELS.keys())
    idx = options.index(current) if current in options else 0
    selected = st.selectbox(
        "Display Currency",
        options,
        index=idx,
        format_func=lambda c: CURRENCY_LABELS[c],
        key=f"_currency_select_{key}",
    )
    st.session_state[key] = selected
    return selected
