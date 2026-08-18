"""Faithful port of the preprocessing pipeline from AAP/Notebooks/ml/Multi_LSTM_5m.ipynb.

Builds a (1, 30, 21) feature sequence for the trained multi-stock LSTM from raw
5-minute OHLC bars, using the exact feature engineering and StandardScaler used
during training (SSA denoising, lags, rolling stats, momentum, hl_ratio, hour
encoding, ticker one-hot).
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from numpy import linalg

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

TICKERS = ["AAPL", "AMZN", "GOOG", "MSFT"]
TIME_STEPS = 30
SSA_WINDOW = 90
SSA_COMPONENTS = 12
FEATURE_COUNT = 21

_feature_names: list[str] | None = None
_scaler = None


def _load_artifacts():
    global _feature_names, _scaler
    if _scaler is None:
        with open(ARTIFACTS_DIR / "scaler.pkl", "rb") as f:
            _scaler = pickle.load(f)
        with open(ARTIFACTS_DIR / "feature_names.pkl", "rb") as f:
            _feature_names = pickle.load(f)
    return _feature_names, _scaler


def ssa_embed(series: np.ndarray, L: int) -> np.ndarray:
    N = len(series)
    K = N - L + 1
    X = np.zeros((L, K))
    for i in range(L):
        X[i, :] = series[i : i + K]
    return X


def ssa_denoise(series: np.ndarray, L: int, n_comp: int) -> np.ndarray:
    """Singular Spectrum Analysis denoising, matching the notebook exactly."""
    series = np.asarray(series, dtype=np.float64)
    N = len(series)
    if N < L + 1:
        return series
    X = ssa_embed(series, L)
    U, s, Vt = linalg.svd(X, full_matrices=False)
    X_k = U[:, :n_comp] @ np.diag(s[:n_comp]) @ Vt[:n_comp, :]
    y = np.zeros(N)
    count = np.zeros(N)
    for i in range(L):
        for j in range(X_k.shape[1]):
            idx = i + j
            if idx < N:
                y[idx] += X_k[i, j]
                count[idx] += 1
    return y / (count + 1e-10)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering cell (CELL 12) applied to a per-ticker frame."""
    d = df.copy().sort_values("datetime").reset_index(drop=True)
    den = d["pct_denoised"].values.astype(np.float64)

    for lag in [1, 2, 3, 4, 5, 6]:
        d[f"den_lag_{lag}"] = np.roll(den, lag)
        d.loc[d.index[:lag], f"den_lag_{lag}"] = 0.0
    for w in [6, 12, 24]:
        r = pd.Series(den).rolling(w, min_periods=1)
        d[f"den_ma_{w}"] = r.mean().values
        d[f"den_std_{w}"] = r.std().fillna(0).values
    for w in [6, 12]:
        d[f"den_mom_{w}"] = pd.Series(den).rolling(w, min_periods=1).sum().values

    d["hl_ratio"] = (d["high"] - d["low"]) / (d["close"] + 1e-10)
    h = d["datetime"].dt.hour
    d["hour_sin"] = np.sin(2 * np.pi * h / 24)
    d["hour_cos"] = np.cos(2 * np.pi * h / 24)
    d = d.replace([np.inf, -np.inf], 0).fillna(0)

    for t in TICKERS:
        d[f"ticker_{t}"] = (d["ticker"] == t).astype(float)

    return d


def build_sequence(bars: pd.DataFrame, ticker: str) -> np.ndarray:
    """Convert raw 5-minute OHLC bars into a (1, 30, 21) model input.

    bars must contain datetime, open, high, low, close columns and enough rows
    (>= ~120) for the SSA window. Returns the scaled sequence for the last
    TIME_STEPS bars. Raises ValueError when the input is too short.
    """
    ticker = ticker.upper()
    if ticker not in TICKERS:
        raise ValueError(f"ticker must be one of {TICKERS}")

    feature_names, scaler = _load_artifacts()

    df = pd.DataFrame(bars)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df["ticker"] = ticker

    if len(df) < SSA_WINDOW + TIME_STEPS:
        raise ValueError(
            f"need at least {SSA_WINDOW + TIME_STEPS} bars for ticker {ticker}, got {len(df)}"
        )

    pct = df["close"].pct_change().fillna(0).values * 100.0
    df["pct"] = pct
    df["pct_denoised"] = ssa_denoise(
        pct, min(SSA_WINDOW, len(pct) // 2), SSA_COMPONENTS
    )

    df = add_features(df)

    cols = [c for c in feature_names if c in df.columns]
    if len(cols) != FEATURE_COUNT:
        raise ValueError(f"feature mismatch: expected {FEATURE_COUNT}, built {len(cols)}")

    scaled = scaler.transform(df[feature_names].values.astype(np.float64))
    seq = scaled[-TIME_STEPS:, :]
    if seq.shape != (TIME_STEPS, FEATURE_COUNT):
        raise ValueError(f"bad sequence shape: {seq.shape}")
    return seq.reshape(1, TIME_STEPS, FEATURE_COUNT).astype(np.float64)


def fetch_5m_bars(ticker: str) -> pd.DataFrame:
    """Fetch the last ~60 days of 5-minute OHLC bars for a ticker from Yahoo Finance.

    Returns bars with columns datetime/open/high/low/close, or an empty
    DataFrame when no data is available. Raises on network/fetch errors.
    """
    import yfinance as yf

    df = yf.Ticker(ticker).history(period="60d", interval="5m", auto_adjust=True)
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    bars = df.reset_index()[["Datetime", "Open", "High", "Low", "Close"]]
    return bars.rename(
        columns={
            "Datetime": "datetime",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
        }
    )


def ticker_ohe_expected() -> list[str]:
    """The ticker one-hot order the model was trained with."""
    return TICKERS
