"""Local inference over the LSTM model artifact hosted on the Hugging Face Hub.

The multi-stock LSTM (best_5m_lstm.keras) lives in the model repo
240673J/Stock_Pred as the canonical unzipped Keras layout (config.json +
metadata.json + model.weights.h5). It is fetched at runtime via
keras.saving.load_model("hf://...") so the artifact is remotely hosted while
inference runs in-process on Keras 3 with the PyTorch backend (CPU).
"""

import logging
import os
import threading
import time

os.environ.setdefault("KERAS_BACKEND", "torch")

from .preprocess import FEATURE_COUNT, TIME_STEPS  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_MODEL_URI = "hf://240673J/Stock_Pred"
WARMUP_DELAY_S = float(os.getenv("LSTM_WARMUP_DELAY", "5"))

_model = None
_model_lock = threading.Lock()


class ModelUnavailableError(RuntimeError):
    """Raised when the LSTM model cannot be loaded or fails to run."""


def _asymmetric_focal_loss(keras, alpha_pos=1.0, alpha_neg=3.0, gamma=2.0):
    """Training loss from AAP/Notebooks/ml/Multi_LSTM_5m.ipynb.

    Required to deserialize the saved model; used only for weight loading.
    Keras is passed in so this module's import stays free of keras/torch.
    """

    def loss(y_true, y_pred):
        y_pred = keras.ops.clip(
            y_pred, keras.backend.epsilon(), 1 - keras.backend.epsilon()
        )
        pos_focal = keras.ops.power(1.0 - y_pred, gamma)
        neg_focal = keras.ops.power(y_pred, gamma)
        pos_loss = -y_true * alpha_pos * pos_focal * keras.ops.log(y_pred)
        neg_loss = -(1.0 - y_true) * alpha_neg * neg_focal * keras.ops.log(1.0 - y_pred)
        return keras.ops.mean(pos_loss + neg_loss)

    return loss


def model_uri() -> str:
    return (os.getenv("LSTM_MODEL_URI") or DEFAULT_MODEL_URI).strip()


def _load():
    uri = model_uri()
    try:
        import keras

        custom_objects = {"loss": _asymmetric_focal_loss(keras, 1.0, 3.0, 2.0)}
        if uri.startswith("hf://"):
            from huggingface_hub import snapshot_download

            repo_id = uri[len("hf://") :].rstrip("/")
            local_dir = snapshot_download(repo_id=repo_id)
            return keras.saving.load_model(local_dir, custom_objects=custom_objects)
        return keras.saving.load_model(uri, custom_objects=custom_objects)
    except Exception as e:
        raise ModelUnavailableError(f"failed to load LSTM model from {uri}: {e}") from e


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = _load()
    return _model


def _warmup():
    """Load the model in the background so the first /predict is fast."""
    try:
        if WARMUP_DELAY_S > 0:
            time.sleep(WARMUP_DELAY_S)
        _get_model()
        logger.info("LSTM model warmed up from %s", model_uri())
    except Exception:
        logger.exception(
            "LSTM model warm-up failed; will retry lazily on first use"
        )


threading.Thread(target=_warmup, name="lstm-model-warmup", daemon=True).start()


def predict(sequence) -> dict:
    """Send one (N, 30, 21) sequence and return {"predictions": [...], "probabilities": [...]}."""
    import numpy as np

    arr = np.asarray(sequence, dtype=np.float64)
    if arr.ndim != 3 or arr.shape[1:] != (TIME_STEPS, FEATURE_COUNT):
        raise ValueError(f"Expected shape (N, 30, 21), got {arr.shape}")
    try:
        model = _get_model()
        probs = model.predict(arr, verbose=0).flatten().tolist()
        preds = [1 if p > 0.5 else 0 for p in probs]
        return {"predictions": preds, "probabilities": probs}
    except ModelUnavailableError:
        raise
    except Exception as e:
        raise ModelUnavailableError(f"LSTM inference failed: {e}") from e