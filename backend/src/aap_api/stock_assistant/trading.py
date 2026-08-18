"""Paper-trading engine (DB-backed).

Per-user trading accounts: cash, positions, and a trade history, all in
PostgreSQL. The account model matches a real implementation; trades execute at
live Yahoo Finance prices but no real money is moved (demo).
"""

from decimal import Decimal, ROUND_HALF_UP

import psycopg
import yfinance as yf

from ..db import get_conn_string

STARTING_CASH = Decimal("100000.00")

QUANTITY_ERR = "quantity must be a positive whole number"


def _round_money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_price(symbol: str) -> Decimal:
    """Live price for a symbol; raises ValueError when unavailable."""
    try:
        info = yf.Ticker(symbol).fast_info
        price = info.get("last_price") or info.get("lastPrice")
    except Exception as e:
        raise ValueError(f"could not fetch price for {symbol}: {e}") from e
    if price is None:
        raise ValueError(f"no live price available for {symbol}")
    return Decimal(str(float(price)))


def ensure_account(user_id: int) -> None:
    """Create the user's account with starting cash on first access."""
    with psycopg.connect(get_conn_string()) as conn:
        conn.execute(
            "INSERT INTO trading_accounts (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (user_id,),
        )


def get_account(user_id: int) -> dict:
    """Return the account's cash, positions, and recent transactions."""
    ensure_account(user_id)
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cash FROM trading_accounts WHERE user_id = %s", (user_id,)
            )
            row = cur.fetchone()
            cash = _round_money(row[0]) if row else STARTING_CASH

            cur.execute(
                "SELECT ticker, quantity, avg_price FROM positions "
                "WHERE user_id = %s ORDER BY ticker",
                (user_id,),
            )
            positions = [
                {"ticker": r[0], "quantity": int(r[1]), "avg_price": float(r[2])}
                for r in cur.fetchall()
            ]

            cur.execute(
                "SELECT ticker, side, quantity, price, total, created_at "
                "FROM transactions WHERE user_id = %s "
                "ORDER BY created_at DESC LIMIT 20",
                (user_id,),
            )
            transactions = [
                {
                    "ticker": r[0],
                    "side": r[1],
                    "quantity": int(r[2]),
                    "price": float(r[3]),
                    "total": float(r[4]),
                    "timestamp": r[5].isoformat(),
                }
                for r in cur.fetchall()
            ]

    return {"user_id": user_id, "cash": float(cash), "positions": positions, "transactions": transactions}


def execute_trade(user_id: int, symbol: str, side: str, quantity: int) -> dict:
    """Execute a paper buy/sell at the live price in a single DB transaction."""
    symbol = (symbol or "").upper().strip()
    if not symbol:
        raise ValueError("symbol is required")
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise ValueError(QUANTITY_ERR) from None
    if quantity <= 0:
        raise ValueError(QUANTITY_ERR)

    price = get_price(symbol)
    total = _round_money(price * quantity)

    ensure_account(user_id)
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cash FROM trading_accounts WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("account not found")
            cash = Decimal(str(row[0]))

            if side == "buy":
                if total > cash:
                    raise ValueError(
                        f"insufficient cash: need ${total:,.2f} but only ${cash:,.2f} available"
                    )
                cur.execute(
                    "SELECT quantity, avg_price FROM positions "
                    "WHERE user_id = %s AND ticker = %s FOR UPDATE",
                    (user_id, symbol),
                )
                existing = cur.fetchone()
                if existing:
                    qty_held, avg_price = int(existing[0]), Decimal(str(existing[1]))
                    new_qty = qty_held + quantity
                    new_avg = (avg_price * qty_held + price * quantity) / new_qty
                    cur.execute(
                        "UPDATE positions SET quantity = %s, avg_price = %s "
                        "WHERE user_id = %s AND ticker = %s",
                        (new_qty, new_avg, user_id, symbol),
                    )
                else:
                    cur.execute(
                        "INSERT INTO positions (user_id, ticker, quantity, avg_price) "
                        "VALUES (%s, %s, %s, %s)",
                        (user_id, symbol, quantity, price),
                    )
                cur.execute(
                    "UPDATE trading_accounts SET cash = %s WHERE user_id = %s",
                    (cash - total, user_id),
                )
            else:
                cur.execute(
                    "SELECT quantity, avg_price FROM positions "
                    "WHERE user_id = %s AND ticker = %s FOR UPDATE",
                    (user_id, symbol),
                )
                existing = cur.fetchone()
                if existing is None:
                    raise ValueError(f"no position in {symbol}")
                qty_held, avg_price = int(existing[0]), Decimal(str(existing[1]))
                if quantity > qty_held:
                    raise ValueError(
                        f"insufficient shares: you hold {qty_held} of {symbol}, tried to sell {quantity}"
                    )
                new_qty = qty_held - quantity
                if new_qty == 0:
                    cur.execute(
                        "DELETE FROM positions WHERE user_id = %s AND ticker = %s",
                        (user_id, symbol),
                    )
                else:
                    cur.execute(
                        "UPDATE positions SET quantity = %s WHERE user_id = %s AND ticker = %s",
                        (new_qty, user_id, symbol),
                    )
                cur.execute(
                    "UPDATE trading_accounts SET cash = %s WHERE user_id = %s",
                    (cash + total, user_id),
                )

            cur.execute(
                "INSERT INTO transactions (user_id, ticker, side, quantity, price, total) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, symbol, side, quantity, price, total),
            )

    return get_account(user_id)


def transfer_cash(from_user_id: int, to_email: str, amount) -> dict:
    """Transfer cash between two users' trading accounts (atomic)."""
    to_email = (to_email or "").strip().lower()
    if not to_email:
        raise ValueError("recipient email is required")
    try:
        amount = _round_money(Decimal(str(amount)))
    except Exception:
        raise ValueError("amount must be a number") from None
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name FROM users WHERE email = %s AND NOT disabled",
                (to_email,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"no user found with email {to_email}")
            to_user_id, to_name = row
            if to_user_id == from_user_id:
                raise ValueError("you cannot transfer to your own account")

            ensure_account(from_user_id)
            ensure_account(to_user_id)

            cur.execute(
                "SELECT cash FROM trading_accounts WHERE user_id = %s FOR UPDATE",
                (from_user_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("account not found")
            cash = Decimal(str(row[0]))
            if amount > cash:
                raise ValueError(
                    f"insufficient cash: need ${amount:,.2f} but only ${cash:,.2f} available"
                )

            cur.execute(
                "SELECT cash FROM trading_accounts WHERE user_id = %s FOR UPDATE",
                (to_user_id,),
            )
            row = cur.fetchone()
            to_cash = Decimal(str(row[0])) if row else Decimal("0")

            cur.execute(
                "UPDATE trading_accounts SET cash = %s WHERE user_id = %s",
                (cash - amount, from_user_id),
            )
            cur.execute(
                "UPDATE trading_accounts SET cash = %s WHERE user_id = %s",
                (to_cash + amount, to_user_id),
            )
            cur.execute(
                "INSERT INTO transfers (from_user_id, to_user_id, amount) "
                "VALUES (%s, %s, %s)",
                (from_user_id, to_user_id, amount),
            )

    return {
        "to_name": to_name,
        "to_email": to_email,
        "amount": float(amount),
        "account": get_account(from_user_id),
    }


def reset_account(user_id: int) -> dict:
    """Reset the account to the starting state ($100k, no positions)."""
    ensure_account(user_id)
    with psycopg.connect(get_conn_string()) as conn:
        conn.execute(
            "UPDATE trading_accounts SET cash = %s WHERE user_id = %s",
            (STARTING_CASH, user_id),
        )
        conn.execute("DELETE FROM positions WHERE user_id = %s", (user_id,))
        conn.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
    return get_account(user_id)