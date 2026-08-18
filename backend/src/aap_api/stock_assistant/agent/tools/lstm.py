"""LSTM next-bar prediction tool (category: ml).

Wraps the Gradio-hosted multi-stock LSTM: live 5-minute data -> preprocessing
pipeline -> model inference -> human-readable direction forecast.
"""

from ...ml import gateway
from ...ml.preprocess import TICKERS, build_sequence, fetch_5m_bars
from .registry import tool

MODEL_TICKERS = TICKERS


@tool(name="predict_next_bar", category="ml")
def predict_next_bar(ticker: str) -> str:
    """Predict whether the next 5-minute bar will close up or down using a trained LSTM model. Fetches live Yahoo Finance data itself. Only supports: AAPL, AMZN, GOOG, MSFT — the model was trained on 5-minute bars of these four stocks, so it cannot predict others. Returns the current price, the direction (UP/DOWN) with probability, and a confidence score. This is a statistical forecast, not financial advice."""
    ticker = (ticker or "").upper().strip()
    if ticker not in MODEL_TICKERS:
        return f"Error: prediction is only available for: {', '.join(MODEL_TICKERS)}"

    try:
        bars = fetch_5m_bars(ticker)
        if bars.empty:
            return f"Error: no market data available for {ticker}"
        sequence = build_sequence(bars, ticker)
        result = gateway.predict(sequence)
    except ValueError as e:
        return f"Error: {e}"
    except gateway.ModelUnavailableError as e:
        return f"Error: model unavailable — {e}"
    except Exception as e:
        return f"Error: prediction failed — {e}"

    probabilities = result.get("probabilities") or []
    if not probabilities:
        return "Error: model returned no probabilities"
    probability = float(probabilities[0])

    direction = "UP" if probability > 0.5 else "DOWN"
    confidence = probability if direction == "UP" else 1.0 - probability

    price = round(float(bars["close"].iloc[-1]), 2)
    dt = bars["datetime"].iloc[-1]

    return (
        f"{ticker} next-5-minute bar prediction (LSTM): {direction} with "
        f"{probability:.1%} probability (confidence {confidence:.1%}).\n"
        f"Current price: ${price} at {dt.isoformat()}.\n"
        f"Horizon: next 5 minutes. Trained on {', '.join(MODEL_TICKERS)} 5-minute "
        f"bars. Statistical forecast, not financial advice."
    )