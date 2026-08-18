import json

import yfinance as yf

from .registry import tool

YAHOO_BASE = "https://finance.yahoo.com/quote"


@tool()
def get_price_series(ticker: str, period: str = "1mo", interval: str = "1d") -> str:
    """Get a JSON array of closing prices for a ticker for numeric analysis. Period options: 5d, 1mo, 3mo, 6mo, 1y, 5y. Interval options: 1d, 1wk, 1mo, 1h, 30m, 15m, 5m (intraday is only available for recent periods). Returns only closing prices; feed the result to the math tools (moving_average, volatility, calculate_returns, linear_trend)."""
    valid_periods = {"5d", "1mo", "3mo", "6mo", "1y", "5y"}
    if period not in valid_periods:
        return f"Invalid period '{period}'. Choose from: {', '.join(sorted(valid_periods))}"

    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if hist.empty:
            return f"No price data available for {ticker}."
        closes = [round(float(v), 4) for v in hist["Close"].tolist()]
        return json.dumps(closes)
    except Exception as e:
        return f"Error fetching price series for {ticker}: {e}"


@tool()
def get_stock_price(ticker: str) -> str:
    """Get the current stock price, daily change, and volume for a ticker symbol (e.g. AAPL, MSFT, GOOGL)."""
    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose")
        name = info.get("shortName") or ticker
        source = f"{YAHOO_BASE}/{ticker}"

        if price is None:
            return f"No price data available for {ticker}. Source: {source}"

        change = price - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None
        volume = info.get("volume")

        parts = [f"{name} ({ticker})", f"Price: ${price:.2f}"]
        if change is not None and change_pct is not None:
            sign = "+" if change >= 0 else ""
            parts.append(f"Change: {sign}${change:.2f} ({sign}{change_pct:.1f}%)")
        else:
            parts.append("Change: N/A")
        if volume:
            parts.append(f"Volume: {volume:,}")
        parts.append(f"Source: {source}")
        return " | ".join(parts)
    except Exception as e:
        return f"Error fetching price for {ticker}: {e}"


@tool()
def get_stock_history(ticker: str, period: str = "1mo") -> str:
    """Get historical OHLCV price data for a ticker. Period options: 5d, 1mo, 3mo, 6mo, 1y, 5y, max."""
    valid_periods = {"5d", "1mo", "3mo", "6mo", "1y", "5y", "max"}
    if period not in valid_periods:
        return f"Invalid period '{period}'. Choose from: {', '.join(sorted(valid_periods))}"

    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return f"No historical data available for {ticker}."

        start_price = hist["Close"].iloc[0]
        end_price = hist["Close"].iloc[-1]
        high = hist["High"].max()
        low = hist["Low"].min()
        volume = hist["Volume"].sum()
        change_pct = ((end_price - start_price) / start_price) * 100
        sign = "+" if change_pct >= 0 else ""

        source = f"{YAHOO_BASE}/{ticker}/history"

        return (
            f"{ticker} — {period} performance:\n"
            f"  Start: ${start_price:.2f}  |  End: ${end_price:.2f}\n"
            f"  Change: {sign}{change_pct:.1f}%\n"
            f"  High: ${high:.2f}  |  Low: ${low:.2f}\n"
            f"  Volume: {volume:,.0f}\n"
            f"  Source: {source}"
        )
    except Exception as e:
        return f"Error fetching history for {ticker}: {e}"


@tool()
def get_stock_info(ticker: str) -> str:
    """Get company fundamentals and profile for a ticker: market cap, PE ratio, EPS, dividend yield, sector, 52-week range, and more."""
    try:
        info = yf.Ticker(ticker).info
        source = f"{YAHOO_BASE}/{ticker}"

        fields = {
            "Company": info.get("longName") or ticker,
            "Sector": info.get("sector", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "Employees": f"{info.get('fullTimeEmployees', 'N/A'):,}" if isinstance(info.get('fullTimeEmployees'), int) else info.get('fullTimeEmployees', 'N/A'),
            "Market Cap": f"${info.get('marketCap', 'N/A'):,}" if isinstance(info.get('marketCap'), (int, float)) else info.get('marketCap', 'N/A'),
            "PE Ratio (TTM)": f"{info.get('trailingPE', 'N/A'):.2f}" if isinstance(info.get('trailingPE'), (int, float)) else info.get('trailingPE', 'N/A'),
            "Forward PE": f"{info.get('forwardPE', 'N/A'):.2f}" if isinstance(info.get('forwardPE'), (int, float)) else info.get('forwardPE', 'N/A'),
            "EPS (TTM)": f"${info.get('trailingEps', 'N/A'):.2f}" if isinstance(info.get('trailingEps'), (int, float)) else info.get('trailingEps', 'N/A'),
            "Dividend Yield": f"{info.get('dividendYield', 'N/A')*100:.2f}%" if isinstance(info.get('dividendYield'), (int, float)) else info.get('dividendYield', 'N/A'),
            "52W High": f"${info.get('fiftyTwoWeekHigh', 'N/A'):.2f}" if isinstance(info.get('fiftyTwoWeekHigh'), (int, float)) else info.get('fiftyTwoWeekHigh', 'N/A'),
            "52W Low": f"${info.get('fiftyTwoWeekLow', 'N/A'):.2f}" if isinstance(info.get('fiftyTwoWeekLow'), (int, float)) else info.get('fiftyTwoWeekLow', 'N/A'),
            "Beta": f"{info.get('beta', 'N/A'):.2f}" if isinstance(info.get('beta'), (int, float)) else info.get('beta', 'N/A'),
            "Avg Volume": f"{info.get('averageVolume', 'N/A'):,}" if isinstance(info.get('averageVolume'), int) else info.get('averageVolume', 'N/A'),
        }

        lines = [f"{info.get('longName', ticker)} Profile:", ""]
        for label, value in fields.items():
            lines.append(f"  {label}: {value}")
        lines.append("")
        lines.append(f"  Source: {source}")

        desc = info.get("longBusinessSummary")
        if desc:
            lines.append("")
            lines.append(f"  Business: {desc[:300]}{'...' if len(desc) > 300 else ''}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching info for {ticker}: {e}"


@tool()
def get_stock_news(ticker: str, count: int = 5) -> str:
    """Get recent news articles for a ticker. Returns article titles, publishers, and direct links."""
    try:
        t = yf.Ticker(ticker)
        news = t.news
        if not news:
            return f"No recent news found for {ticker}."

        lines = [f"Recent news for {ticker}:"]
        for article in news[:max(1, min(count, 20))]:
            title = article.get("title", "Untitled")
            publisher = article.get("publisher", "Unknown")
            link = article.get("link", "N/A")
            lines.append(f"  \u2022 {title} ({publisher})")
            lines.append(f"    {link}")
        lines.append(f"\nSource: Yahoo Finance — {YAHOO_BASE}/{ticker}/news")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching news for {ticker}: {e}"


@tool(category="enhanced")
def get_analyst_ratings(ticker: str) -> str:
    """Get analyst consensus ratings breakdown and average price target for a ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        source = f"{YAHOO_BASE}/{ticker}"

        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        rec = info.get("recommendationKey", "N/A")
        rec_mean = info.get("recommendationMean")

        lines = [f"Analyst Ratings for {info.get('longName', ticker)}:", ""]

        if rec and rec != "N/A":
            lines.append(f"  Consensus: {rec.upper()}")
        if rec_mean is not None:
            lines.append(f"  Rating Score: {rec_mean:.2f} (1=Strong Buy, 5=Strong Sell)")
        if target_mean:
            lines.append(f"  Avg Price Target: ${target_mean:.2f}")
        if target_high:
            lines.append(f"  High Target: ${target_high:.2f}")
        if target_low:
            lines.append(f"  Low Target: ${target_low:.2f}")

        current = info.get("currentPrice") or info.get("regularMarketPrice")
        if current and target_mean:
            upside = ((target_mean - current) / current) * 100
            sign = "+" if upside >= 0 else ""
            lines.append(f"  Upside to Target: {sign}{upside:.1f}%")

        try:
            recs = t.recommendations
            if recs is not None and not recs.empty:
                latest = recs.tail(1)
                lines.append("")
                lines.append(f"  Latest recommendation period: {latest.index[0].strftime('%Y-%m-%d') if hasattr(latest.index[0], 'strftime') else latest.index[0]}")
        except Exception:
            pass

        lines.append("")
        lines.append(f"  Source: {source}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching analyst ratings for {ticker}: {e}"


@tool(category="enhanced")
def get_earnings_calendar(ticker: str) -> str:
    """Get upcoming earnings date, EPS estimates, and last quarter's earnings surprise for a ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        source = f"{YAHOO_BASE}/{ticker}/calendar/earnings"

        name = info.get("longName", ticker)
        lines = [f"Earnings Calendar for {name}:", ""]

        try:
            cal = t.calendar
            if cal:
                earnings_date = cal.get("Earnings Date")
                if earnings_date is not None:
                    lines.append(f"  Next Earnings: {earnings_date}")
                else:
                    lines.append("  Next Earnings: Not available")
                est_eps = cal.get("Earnings Estimate")
                if est_eps is not None:
                    lines.append(f"  Est. EPS: ${est_eps:.2f}" if isinstance(est_eps, (int, float)) else f"  Est. EPS: {est_eps}")
                actual_eps = info.get("epsTrailingTwelveMonths")
                if actual_eps:
                    lines.append(f"  EPS (TTM): ${actual_eps:.2f}")
            else:
                lines.append("  Earnings calendar data not available.")
        except Exception:
            lines.append("  Earnings calendar data not available.")

        try:
            earnings = t.earnings_dates
            if earnings is not None and not earnings.empty:
                latest = earnings.head(1)
                lines.append("")
                lines.append("  Last Quarter:")
                for col in latest.columns:
                    val = latest[col].iloc[0]
                    lines.append(f"    {col}: {val}")
        except Exception:
            pass

        lines.append("")
        lines.append(f"  Source: {source}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching earnings for {ticker}: {e}"


@tool(category="enhanced")
def get_dividend_info(ticker: str) -> str:
    """Get dividend yield, ex-date, pay date, and history for a dividend-paying stock."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        source = f"{YAHOO_BASE}/{ticker}"

        name = info.get("longName", ticker)
        lines = [f"Dividend Info for {name}:", ""]

        div_yield = info.get("dividendYield")
        if div_yield is not None:
            lines.append(f"  Dividend Yield: {div_yield*100:.2f}%")

        div_rate = info.get("dividendRate")
        if div_rate is not None:
            lines.append(f"  Dividend Rate: ${div_rate:.2f}/share")

        payout_ratio = info.get("payoutRatio")
        if payout_ratio is not None:
            lines.append(f"  Payout Ratio: {payout_ratio*100:.1f}%")

        ex_date = info.get("exDividendDate")
        if ex_date:
            import datetime

            dt = datetime.datetime.fromtimestamp(ex_date)
            lines.append(f"  Ex-Dividend Date: {dt.strftime('%Y-%m-%d')}")

        lines.append("")
        divs = t.dividends
        if divs is not None and not divs.empty:
            lines.append(f"  Dividend History (last {min(5, len(divs))} payments):")
            for date, amount in divs.tail(5).items():
                d = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
                lines.append(f"    {d}: ${amount:.4f}")
        else:
            lines.append("  No dividend history found (may not pay dividends).")

        lines.append("")
        lines.append(f"  Source: {source}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching dividend info for {ticker}: {e}"


@tool(category="enhanced")
def get_market_indices() -> str:
    """Get current levels and daily change for major US market indices: S&P 500 (^GSPC), NASDAQ (^IXIC), and Dow Jones (^DJI)."""
    indices = {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ Composite",
        "^DJI": "Dow Jones Industrial Average",
    }

    lines = ["Major Market Indices (source: Yahoo Finance):", ""]
    for symbol, name in indices.items():
        try:
            info = yf.Ticker(symbol).info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev_close = info.get("previousClose")
            source = f"{YAHOO_BASE}/{symbol}"

            if price is None:
                lines.append(f"  {name}: N/A")
                continue

            change = price - prev_close if prev_close else None
            change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None

            parts = [f"{name}: {price:,.2f}"]
            if change is not None and change_pct is not None:
                sign = "+" if change >= 0 else ""
                parts.append(f"({sign}{change:,.2f}, {sign}{change_pct:.2f}%)")
            lines.append("  " + " ".join(parts))
        except Exception as e:
            lines.append(f"  {name}: Error — {e}")

    lines.append("")
    lines.append(f"  Source: https://finance.yahoo.com")
    return "\n".join(lines)
