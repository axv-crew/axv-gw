from __future__ import annotations
from typing import Optional
from prometheus_client import Gauge, REGISTRY

_BUILD_METRIC: Optional[Gauge] = None
_METRIC_NAME = "axv_gw_build_info"

def ensure_build_metric() -> Gauge:
    """
    Idempotentnie zwraca Gauge:
      - jeśli już zarejestrowany → zwróć istniejący
      - w przeciwnym razie utwórz i zapamiętaj
    """
    global _BUILD_METRIC
    if _BUILD_METRIC is not None:
        return _BUILD_METRIC

    try:
        existing = getattr(REGISTRY, "_names_to_collectors", {}).get(_METRIC_NAME)
        if isinstance(existing, Gauge):
            _BUILD_METRIC = existing
            return _BUILD_METRIC
    except Exception:
        pass

    _BUILD_METRIC = Gauge(_METRIC_NAME, "Build info", ["version", "name"])
    return _BUILD_METRIC
