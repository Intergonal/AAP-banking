"""Math and data-analysis tools for the agent (category: math).

Pure computation over numeric arrays plus a safe AST-based expression
evaluator. Price series come from get_price_series (in stock_data.py) or are
passed directly by the model as JSON arrays.
"""

import ast
import json
import math

import numpy as np
import pandas as pd

from .registry import tool

MAX_EXPR_LENGTH = 500
MAX_POW_EXPONENT = 100
MAX_CALL_DEPTH = 20

MATH_FUNCTIONS = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "floor": math.floor,
    "ceil": math.ceil,
    "fabs": math.fabs,
    "hypot": math.hypot,
    "degrees": math.degrees,
    "radians": math.radians,
    "isfinite": math.isfinite,
    "isnan": math.isnan,
    "isinf": math.isinf,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
}

MATH_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)
_ALLOWED_CMP = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
_ALLOWED_BOOLOPS = (ast.And, ast.Or)


def _contains_pow(node) -> bool:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        return True
    return any(_contains_pow(child) for child in ast.iter_child_nodes(node))


def _fold_constant(node):
    """Evaluate a Pow-free subtree with no names and no builtins."""
    try:
        return eval(
            compile(ast.Expression(body=node), "<const>", "eval"),
            {"__builtins__": {}},
            {},
        )
    except Exception:
        return None


def _check_op(op, allowed):
    if not isinstance(op, allowed):
        raise ValueError(f"operator {type(op).__name__} is not allowed")


def _check_node(node, variables, depth):
    if depth > MAX_CALL_DEPTH:
        raise ValueError("expression is too deeply nested")

    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, bool)):
            raise ValueError("only numeric constants are allowed")
        return

    if isinstance(node, ast.BinOp):
        _check_op(node.op, _ALLOWED_BINOPS)
        _check_node(node.left, variables, depth + 1)
        _check_node(node.right, variables, depth + 1)
        if isinstance(node.op, ast.Pow):
            if _contains_pow(node.right):
                raise ValueError("nested exponentiation is not allowed")
            exponent = _fold_constant(node.right)
            if (
                exponent is None
                or not isinstance(exponent, (int, float))
                or abs(exponent) > MAX_POW_EXPONENT
            ):
                raise ValueError(
                    f"exponent must be a numeric constant with |value| <= {MAX_POW_EXPONENT}"
                )
        return

    if isinstance(node, ast.UnaryOp):
        _check_op(node.op, _ALLOWED_UNARY)
        _check_node(node.operand, variables, depth + 1)
        return

    if isinstance(node, ast.Compare):
        for op in node.ops:
            _check_op(op, _ALLOWED_CMP)
        _check_node(node.left, variables, depth + 1)
        for comparator in node.comparators:
            _check_node(comparator, variables, depth + 1)
        return

    if isinstance(node, ast.BoolOp):
        _check_op(node.op, _ALLOWED_BOOLOPS)
        for value in node.values:
            _check_node(value, variables, depth + 1)
        return

    if isinstance(node, ast.IfExp):
        _check_node(node.test, variables, depth + 1)
        _check_node(node.body, variables, depth + 1)
        _check_node(node.orelse, variables, depth + 1)
        return

    if isinstance(node, ast.Name):
        if not isinstance(node.ctx, ast.Load):
            raise ValueError("unsupported name context")
        if node.id not in variables and node.id not in MATH_CONSTANTS:
            raise ValueError(
                f"unknown variable '{node.id}' — pass it in the variables argument"
            )
        return

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("only direct function calls are allowed")
        if node.func.id not in MATH_FUNCTIONS:
            raise ValueError(f"function '{node.func.id}' is not allowed")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed")
        if not 1 <= len(node.args) <= 3:
            raise ValueError("function calls must have 1 to 3 arguments")
        for arg in node.args:
            _check_node(arg, variables, depth + 1)
        return

    raise ValueError(f"unsupported construct: {type(node).__name__}")


def _safe_eval(expression: str, variables: dict) -> float:
    if len(expression) > MAX_EXPR_LENGTH:
        raise ValueError(f"expression too long (max {MAX_EXPR_LENGTH} characters)")
    tree = ast.parse(expression, mode="eval")
    _check_node(tree.body, variables, 0)
    namespace = dict(MATH_CONSTANTS)
    namespace.update(MATH_FUNCTIONS)
    namespace.update(variables)
    return eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, namespace)


def _format_number(value) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return str(value)
    return f"{value:.6f}".rstrip("0").rstrip(".")


@tool(category="math")
def calculate(expression: str, variables: str = "{}") -> str:
    """Evaluate a mathematical expression safely. Supports + - * / // % **, parentheses, comparisons (<, >, <=, >=, ==, !=), and/or, ternary (x if cond else y), and math functions: sqrt, log, log10, log2, exp, sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, floor, ceil, fabs, hypot, degrees, radians, isfinite, isnan, isinf, abs, round, min, max. Constants: pi, e, tau. Pass numeric variables as a JSON object string, e.g. '{\"principal\": 10000, \"rate\": 0.07}'. Example: (10000 * (1 + 0.07/12) ** (12 * 5))."""
    try:
        if isinstance(variables, str) and variables.strip():
            parsed = json.loads(variables)
        else:
            parsed = {}
        if not isinstance(parsed, dict):
            return 'Error: variables must be a JSON object like {"x": 1.5}'
        for key, value in parsed.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return f"Error: variable '{key}' must be numeric"
        result = _safe_eval(expression, parsed)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError, SyntaxError) as e:
        return f"Error: {e}"
    return _format_number(result)


def _as_array(values, label="prices") -> np.ndarray:
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except json.JSONDecodeError:
            raise ValueError(f"{label} must be a JSON array of numbers")
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{label} must be a non-empty 1-D array of numbers")
    if not np.isfinite(arr).all():
        raise ValueError(f"{label} contains non-finite values")
    return arr


@tool(category="math")
def calculate_returns(prices: str) -> str:
    """Calculate return statistics for a series of prices. prices is a JSON array of numbers (e.g. from get_price_series). Returns total return, mean and std of per-period returns, latest return, and max drawdown."""
    try:
        arr = _as_array(prices)
        if arr.size < 2:
            return "Error: need at least 2 prices"
    except ValueError as e:
        return f"Error: {e}"

    rets = np.diff(arr) / arr[:-1]
    total = arr[-1] / arr[0] - 1
    peak = np.maximum.accumulate(arr)
    drawdown = (arr - peak) / peak

    return (
        f"Total return: {total:.4%}\n"
        f"Per-period returns: mean {rets.mean():.4%}, std {rets.std():.4%}\n"
        f"Latest return: {rets[-1]:.4%}\n"
        f"Max drawdown: {drawdown.min():.4%}"
    )


@tool(category="math")
def moving_average(prices: str, window: int = 20) -> str:
    """Calculate the simple moving average (SMA) of a price series. prices is a JSON array of numbers; window is the number of periods (default 20). Returns the latest SMA, whether price is above or below it, and a preview of the SMA series."""
    try:
        arr = _as_array(prices)
        if not 1 <= window <= len(arr):
            return f"Error: window must be between 1 and {len(arr)}"
    except ValueError as e:
        return f"Error: {e}"

    sma = np.convolve(arr, np.ones(window) / window, mode="valid")
    above = "above" if arr[-1] >= sma[-1] else "below"
    preview = ", ".join(f"{v:.2f}" for v in sma[-10:])
    return (
        f"SMA-{window}: latest {sma[-1]:.4f}\n"
        f"Price vs SMA: {arr[-1]:.4f} is {above} SMA {sma[-1]:.4f}\n"
        f"Recent SMA series: [{preview}]"
    )


@tool(category="math")
def volatility(prices: str, window: int = 20) -> str:
    """Calculate rolling and annualized volatility of a price series. prices is a JSON array of numbers; window is the rolling window in periods (default 20)."""
    try:
        arr = _as_array(prices)
        if not 2 <= window <= len(arr):
            return f"Error: window must be between 2 and {len(arr)}"
    except ValueError as e:
        return f"Error: {e}"

    rets = np.diff(arr) / arr[:-1]
    rolling = pd.Series(rets).rolling(window).std()
    annualized = rets.std() * np.sqrt(252)
    return (
        f"Latest {window}-period rolling std: {rolling.iloc[-1]:.4%}\n"
        f"Series std: {rets.std():.4%}\n"
        f"Annualized (x sqrt(252)): {annualized:.4%}"
    )


@tool(category="math")
def correlation(tickers: str, period: str = "1mo") -> str:
    """Compute the pairwise correlation of daily returns between tickers. tickers is a JSON array of 2-8 ticker symbols (e.g. [\"AAPL\", \"MSFT\"]); period options: 5d, 1mo, 3mo, 6mo, 1y, 5y. Fetches price series from Yahoo Finance."""
    try:
        symbols = json.loads(tickers) if isinstance(tickers, str) else tickers
        if not isinstance(symbols, list) or not 2 <= len(symbols) <= 8:
            return "Error: tickers must be a JSON array of 2-8 symbols"
    except json.JSONDecodeError:
        return "Error: tickers must be a JSON array of symbols"

    from .stock_data import get_price_series

    series = {}
    for symbol in symbols:
        raw = get_price_series(symbol, period=period, interval="1d")
        try:
            series[symbol] = np.asarray(json.loads(raw), dtype=np.float64)
        except (json.JSONDecodeError, ValueError):
            return f"Error: could not fetch a price series for {symbol}"

    n = min(len(v) for v in series.values())
    closes = np.stack([v[:n] for v in series.values()])
    rets = np.diff(closes, axis=1) / closes[:, :-1]
    corr = np.corrcoef(rets)

    lines = [f"Pairwise return correlation ({period}):", ""]
    lines.append("        " + "  ".join(f"{s:>8}" for s in symbols))
    for i, symbol in enumerate(symbols):
        row = "  ".join(f"{corr[i, j]:8.3f}" for j in range(len(symbols)))
        lines.append(f"{symbol:>7}  {row}")
    lines.append("")
    lines.append("Source: Yahoo Finance")
    return "\n".join(lines)


@tool(category="math")
def portfolio_stats(returns_arrays: str, weights: str, rf: float = 0.0) -> str:
    """Calculate portfolio expected return, volatility, and Sharpe ratio from per-asset return series. returns_arrays is a JSON array where each element is a JSON array of per-period returns for one asset (e.g. [[0.01, -0.005, 0.002], [0.003, ...]]); weights is a JSON array of asset weights summing to 1 (e.g. [0.5, 0.5]); rf is the risk-free rate per period (default 0.0)."""
    try:
        raw_arrays = json.loads(returns_arrays) if isinstance(returns_arrays, str) else returns_arrays
        if not isinstance(raw_arrays, list) or len(raw_arrays) < 1:
            return "Error: returns_arrays must be a JSON array of return arrays"
        arrays = [_as_array(a, "returns_arrays element") for a in raw_arrays]
        w = _as_array(weights, "weights")
        if len(arrays) != w.size:
            return "Error: weights must match the number of return arrays"
        if not np.isclose(w.sum(), 1.0, atol=0.05):
            return "Error: weights must sum to 1.0"
    except ValueError as e:
        return f"Error: {e}"

    n = min(len(a) for a in arrays)
    R = np.stack([a[:n] for a in arrays])
    expected = float(w @ R.mean(axis=1))
    variance = float(w @ np.cov(R) @ w)
    std = math.sqrt(variance) if variance >= 0 else float("nan")
    sharpe = (expected - rf) / std if std and std > 0 else float("nan")

    return (
        f"Portfolio expected return (per period): {expected:.4%}\n"
        f"Portfolio volatility: {std:.4%}\n"
        f"Sharpe ratio (rf={rf:.4f}): {sharpe:.4f}"
    )


@tool(category="math")
def time_value(present: float, rate: float, years: float, compounding: int = 12) -> str:
    """Calculate the future value of money with compound interest. present: current amount; rate: annual interest rate as a decimal (e.g. 0.07 for 7%); years: number of years; compounding: compounding periods per year (default 12 = monthly). Returns future value, growth, and doubling time. Use a negative rate to discount to present value."""
    if present <= 0:
        return "Error: present must be positive"
    if rate <= -1:
        return "Error: rate must be greater than -1"
    if compounding < 1:
        return "Error: compounding must be at least 1"
    if years < 0:
        return "Error: years must be non-negative"

    fv = present * (1 + rate / compounding) ** (compounding * years)
    growth = fv / present - 1
    if rate > 0:
        doubling = math.log(2) / math.log(1 + rate)
        doubling_line = f"Doubling time at {rate:.2%}: {doubling:.2f} years"
    else:
        doubling_line = "Doubling time: not applicable (non-positive rate)"

    return (
        f"Future value: ${fv:,.2f}\n"
        f"Growth: {growth:.4%} over {years:.2f} years\n"
        f"{doubling_line}"
    )


@tool(category="math")
def cagr(start_value: float, end_value: float, years: float) -> str:
    """Calculate the compound annual growth rate (CAGR) between two values. start_value: beginning amount; end_value: ending amount; years: number of years. Returns CAGR as a percentage and total growth."""
    if start_value <= 0:
        return "Error: start_value must be positive"
    if end_value <= 0:
        return "Error: end_value must be positive"
    if years <= 0:
        return "Error: years must be positive"

    cagr_value = (end_value / start_value) ** (1 / years) - 1
    return (
        f"CAGR: {cagr_value:.4%} over {years:.2f} years\n"
        f"Total growth: {(end_value / start_value - 1):.4%}"
    )


@tool(category="math")
def linear_trend(prices: str) -> str:
    """Fit a linear trend to a price series. prices is a JSON array of numbers. Returns the slope per period, the approximate trend over the whole window, the intercept, and the R-squared coefficient."""
    try:
        arr = _as_array(prices)
        if arr.size < 3:
            return "Error: need at least 3 prices"
    except ValueError as e:
        return f"Error: {e}"

    x = np.arange(arr.size, dtype=np.float64)
    slope, intercept = np.polyfit(x, arr, 1)
    predicted = slope * x + intercept
    ss_res = float(((arr - predicted) ** 2).sum())
    ss_tot = float(((arr - arr.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0

    return (
        f"Slope: {slope:.4f} per period (approx {slope * arr.size / arr[0]:.4%} over the window)\n"
        f"Intercept: {intercept:.4f}\n"
        f"R-squared: {r2:.4f}"
    )