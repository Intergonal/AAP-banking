"""Gateway to the LSTM model hosted as a free Gradio Space on Hugging Face.

Implements the Gradio 5 HTTP protocol: POST /gradio_api/call/predict then poll
GET /gradio_api/call/predict/{event_id} until the result is complete.
"""

import os
import time

import requests

REQUEST_TIMEOUT = 120.0
POLL_TIMEOUT = 240.0
POLL_INTERVAL = 2.0


class ModelUnavailableError(RuntimeError):
    """Raised when the model space is unreachable, misconfigured, or timing out."""


def get_space_url() -> str:
    url = (os.getenv("GRADIO_SPACE_URL") or "").strip().rstrip("/")
    if not url:
        raise ModelUnavailableError(
            "GRADIO_SPACE_URL is not set — the LSTM model space has not been configured."
        )
    return url


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    token = (os.getenv("HF_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def predict(sequence) -> dict:
    """Send one (1, 30, 21) sequence and return {"predictions": [...], "probabilities": [...]}."""
    url = get_space_url()
    data = sequence if isinstance(sequence, list) else sequence.tolist()

    try:
        resp = requests.post(
            f"{url}/gradio_api/call/predict",
            json={"data": [data]},
            headers=_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise ModelUnavailableError(
            f"Cannot reach the model space at {url} (it may be waking up from hibernation). Error: {e}"
        ) from e

    if resp.status_code == 404:
        raise ModelUnavailableError(
            f"Model space at {url} returned 404 — check that the Space is running and the app exposes a 'predict' function."
        )
    if resp.status_code != 200:
        raise ModelUnavailableError(f"Model space error {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    event_id = payload.get("event_id")
    if not event_id:
        raise ModelUnavailableError(f"Unexpected Gradio response: {payload}")

    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            poll = requests.get(
                f"{url}/gradio_api/call/predict/{event_id}",
                headers=_headers(),
                timeout=30,
            )
        except requests.RequestException as e:
            raise ModelUnavailableError(f"Error polling model space: {e}") from e

        if poll.status_code == 404:
            continue
        if poll.status_code != 200:
            raise ModelUnavailableError(f"Model space poll error {poll.status_code}: {poll.text[:300]}")

        body = poll.json()
        stage = body.get("status", {}).get("stage")
        if stage == "complete":
            output = body.get("data")
            if not output:
                raise ModelUnavailableError(f"Empty model output: {body}")
            result = output[0]
            if isinstance(result, str):
                try:
                    import json

                    result = json.loads(result)
                except json.JSONDecodeError:
                    pass
            if isinstance(result, dict) and "error" in result:
                raise ModelUnavailableError(str(result["error"]))
            return result
        if stage in ("error", "failed"):
            raise ModelUnavailableError(f"Model space failed: {body}")

    raise ModelUnavailableError("Model space did not respond in time — it may be waking up; try again shortly.")


def health() -> dict:
    """Basic reachability check against the Gradio info endpoint."""
    url = get_space_url()
    try:
        resp = requests.get(f"{url}/gradio_api/info", headers=_headers(), timeout=30)
    except requests.RequestException as e:
        return {"ok": False, "url": url, "error": str(e)}
    if resp.status_code != 200:
        return {"ok": False, "url": url, "status": resp.status_code}
    return {"ok": True, "url": url}
