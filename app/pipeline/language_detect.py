import os
import threading

import requests

from app.config import get_settings

_settings = get_settings()
_model = None
_model_lock = threading.Lock()

FASTTEXT_MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"


def _download_model(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    response = requests.get(FASTTEXT_MODEL_URL, timeout=60, stream=True)
    response.raise_for_status()
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    os.rename(tmp_path, path)


def _get_model():
    """Lazily load (downloading if needed) the fasttext lid.176 model, once per process."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        import fasttext

        path = _settings.fasttext_model_path
        if not os.path.exists(path):
            _download_model(path)
        _model = fasttext.load_model(path)
        return _model


def detect_language_fasttext(text: str) -> tuple[str, float]:
    """Primary language detection. Returns (language_code, confidence 0-1)."""
    model = _get_model()
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "unknown", 0.0
    labels, probs = model.predict(cleaned, k=1)
    lang_code = labels[0].replace("__label__", "")
    return lang_code, float(probs[0])
