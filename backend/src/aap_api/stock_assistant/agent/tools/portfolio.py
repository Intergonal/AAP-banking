import json
from pathlib import Path

import yfinance as yf

from .registry import tool

DEFAULT_PORTFOLIO = str(Path(__file__).resolve().parent.parent / "data" / "portfolio.json")


@tool()
def read_portfolio(filepath: str = DEFAULT_PORTFOLIO) -> str:
    """Read the user's investment portfolio from a JSON file. Returns holdings with ticker, quantity, purchase price, and purchase date."""
    try:
        with open(filepath) as f:
            data = json.load(f)
    except FileNotFoundError:
        return f"Portfolio file not found at {filepath}."
    except json.JSONDecodeError:
        return "Invalid portfolio JSON format."

    holdings = data.get("portfolio", [])
    if not holdings:
        return "Portfolio is empty."

    lines = ["Portfolio Holdings:"]
    for h in holdings:
        lines.append(
            f"  {h['ticker']}: {h['quantity']} shares @ ${h['purchase_price']:.2f} "
            f"on {h['purchase_date']}"
        )
    return "\n".join(lines)


@tool()
def get_portfolio_summary(filepath: str = DEFAULT_PORTFOLIO) -> str:
    """Calculate total portfolio value, gain/loss per holding, and sector allocation using current market prices from Yahoo Finance."""
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return f"Error reading portfolio: {e}"

    holdings = data.get("portfolio", [])
    if not holdings:
        return "Portfolio is empty."

    total_cost = 0.0
    total_value = 0.0
    details = []
    sectors = {}

    for h in holdings:
        ticker = h["ticker"]
        qty = h["quantity"]
        cost = h["purchase_price"]
        total_cost += qty * cost

        try:
            t = yf.Ticker(ticker)
            info = t.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            sector = info.get("sector", "Unknown")
        except Exception:
            price = None
            sector = "Unknown"

        if price is None:
            details.append(f"  {ticker}: {qty} shares — price unavailable")
            continue

        current_value = qty * price
        total_value += current_value
        gain = current_value - (qty * cost)
        gain_pct = (gain / (qty * cost)) * 100
        sign = "+" if gain >= 0 else ""
        sectors[sector] = sectors.get(sector, 0) + current_value
        details.append(
            f"  {ticker}: {qty} shares @ ${price:.2f} = ${current_value:.2f} "
            f"({sign}${gain:.2f}, {sign}{gain_pct:.1f}%)"
        )

    if total_value == 0:
        return "Could not calculate portfolio summary — prices unavailable."

    total_gain = total_value - total_cost
    total_gain_pct = (total_gain / total_cost) * 100
    sign = "+" if total_gain >= 0 else ""

    lines = [
        "Portfolio Summary (source: Yahoo Finance)",
        f"  Total Cost:  ${total_cost:.2f}",
        f"  Total Value: ${total_value:.2f}",
        f"  Total P&L:   ${total_gain:.2f} ({sign}{total_gain_pct:.1f}%)",
        "",
        "Holdings:",
    ]
    lines.extend(details)

    if sectors:
        lines.append("")
        lines.append("Sector Allocation:")
        for sector, value in sorted(sectors.items(), key=lambda x: -x[1]):
            pct = (value / total_value) * 100
            lines.append(f"  {sector}: {pct:.1f}%")
        lines.append("")
        lines.append("Source: Yahoo Finance — https://finance.yahoo.com")

    return "\n".join(lines)
