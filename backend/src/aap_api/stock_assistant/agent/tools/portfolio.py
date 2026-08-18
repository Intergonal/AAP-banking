import json
from pathlib import Path

import yfinance as yf

from ....stock_assistant.trading import get_account
from .registry import tool
from .user_context import get_user_id

DEFAULT_PORTFOLIO = str(Path(__file__).resolve().parent.parent / "data" / "portfolio.json")


def _real_portfolio():
    """The authenticated user's actual trading account (positions + cash)."""
    user_id = get_user_id()
    if user_id is None:
        return None
    account = get_account(user_id)
    return {
        "cash": account["cash"],
        "positions": [
            {
                "ticker": pos["ticker"],
                "quantity": pos["quantity"],
                "avg_price": pos["avg_price"],
            }
            for pos in account["positions"]
        ],
    }


def _portfolio_from_file(filepath):
    with open(filepath) as f:
        data = json.load(f)
    return {
        "cash": None,
        "positions": [
            {
                "ticker": h["ticker"],
                "quantity": h["quantity"],
                "avg_price": h["purchase_price"],
            }
            for h in data.get("portfolio", [])
        ],
    }


def _load_portfolio():
    real = _real_portfolio()
    if real is not None:
        return real
    try:
        return _portfolio_from_file(DEFAULT_PORTFOLIO)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


@tool()
def read_portfolio() -> str:
    """Read the user's investment portfolio from their trading account. Returns holdings with ticker, quantity, purchase price, and cash balance."""
    data = _load_portfolio()
    if data is None:
        return "Portfolio is empty."

    holdings = data["positions"]
    lines = ["Portfolio Holdings:"]
    if data["cash"] is not None:
        lines.append(f"  Cash: ${data['cash']:,.2f}")
    if not holdings:
        lines.append("  (no open positions)")
    for h in holdings:
        lines.append(
            f"  {h['ticker']}: {h['quantity']} shares @ ${h['avg_price']:.2f}"
        )
    return "\n".join(lines)


@tool()
def get_portfolio_summary() -> str:
    """Calculate total portfolio value, gain/loss per holding, and sector allocation using current market prices from Yahoo Finance. Includes the cash balance."""
    data = _load_portfolio()
    if data is None:
        return "Portfolio is empty."

    holdings = data["positions"]
    cash = data["cash"] or 0.0

    total_cost = 0.0
    total_value = float(cash)
    details = []
    sectors = {}

    for h in holdings:
        ticker = h["ticker"]
        qty = h["quantity"]
        cost = h["avg_price"]
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
    sign = "+" if total_gain >= 0 else ""

    lines = [
        "Portfolio Summary (source: Yahoo Finance)",
        f"  Total Cost:  ${total_cost:.2f}",
        f"  Cash:        ${float(cash):,.2f}",
        f"  Total Value: ${total_value:.2f}",
    ]
    if total_cost:
        lines.append(f"  Total P&L:   ${total_gain:.2f} ({sign}{total_gain / total_cost * 100:.1f}%)")
    lines.append("")
    lines.append("Holdings:")
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
