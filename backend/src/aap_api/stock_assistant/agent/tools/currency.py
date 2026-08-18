import yfinance as yf

from .registry import tool


@tool(category="enhanced")
def get_currency_exchange(from_currency: str, to_currency: str) -> str:
    """Get current exchange rate between two currencies. Use ISO 4217 currency codes (e.g. USD, EUR, GBP, JPY, CAD, AUD, CHF)."""
    pair = f"{from_currency}{to_currency}=X".upper()
    try:
        t = yf.Ticker(pair)
        info = t.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        name = info.get("shortName") or f"{from_currency}/{to_currency}"
        source = f"https://finance.yahoo.com/quote/{pair}"

        if price is None:
            return f"Exchange rate not available for {from_currency}/{to_currency}. Source: {source}"

        prev_close = info.get("previousClose")
        change = price - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None

        parts = [f"{name}: {price:.6f}"]
        if change is not None and change_pct is not None:
            sign = "+" if change >= 0 else ""
            parts.append(f"({sign}{change:.6f}, {sign}{change_pct:.3f}%)")
        parts.append(f"Source: {source}")
        return " | ".join(parts)
    except Exception as e:
        return f"Error fetching exchange rate for {from_currency}/{to_currency}: {e}"
