
"""
Peeling Chain, Structuring & Forwarding Velocity Classifier.
Identifies algorithmic money laundering patterns used by cyber syndicates.
"""

from math import isfinite
from typing import List, Dict, Any, Optional


def _get_valid_amount(tx: Any) -> Optional[float]:
    """Extract a finite, non-negative transaction amount."""
    if not isinstance(tx, dict):
        return None

    raw_value = tx.get("usd_value")
    if raw_value is None:
        raw_value = tx.get("amount")

    if isinstance(raw_value, bool) or raw_value is None:
        return None

    try:
        value = float(raw_value)
    except (TypeError, ValueError, OverflowError):
        return None

    if not isfinite(value) or value < 0:
        return None

    return value


def _empty_peeling_result() -> Dict[str, Any]:
    return {
        "is_peeling_chain": False,
        "peel_confidence": 0.0,
        "peel_ratio": 0.0,
        "peeled_amount_usd": 0.0,
        "change_amount_usd": 0.0,
    }


def analyze_peeling_chain(
    incoming_transfers: List[Dict[str, Any]],
    outgoing_transfers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Detect a potential peeling pattern with 2 or 3 outgoing transfers.

    The smallest output is treated as the peeled amount.
    The largest output is treated as the change amount.

    The 1%-20% ratio is a heuristic, not proof of illicit activity.
    """
    if not isinstance(outgoing_transfers, list):
        return _empty_peeling_result()

    out_degree = len(outgoing_transfers)

    if out_degree not in (2, 3):
        return _empty_peeling_result()

    values = [_get_valid_amount(tx) for tx in outgoing_transfers]

    # Reject the entire candidate if any output is invalid or zero.
    if any(value is None or value <= 0 for value in values):
        return _empty_peeling_result()

    sorted_values = sorted(values)
    total = sum(sorted_values)

    if not isfinite(total) or total <= 0:
        return _empty_peeling_result()

    small_value = sorted_values[0]
    large_value = sorted_values[-1]
    peel_ratio = small_value / total

    if not 0.01 <= peel_ratio <= 0.20:
        return _empty_peeling_result()

    confidence = min(
        0.98,
        0.70 + (0.28 * (1.0 - (peel_ratio / 0.20)))
    )

    return {
        "is_peeling_chain": True,
        "peel_confidence": round(confidence, 3),
        "peel_ratio": round(peel_ratio, 4),
        "peeled_amount_usd": round(small_value, 2),
        "change_amount_usd": round(large_value, 2),
    }


def detect_structuring_smurfing(
    outgoing_transfers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Detect repeated transfers in the configured $8,500-$9,999 range.

    This is a heuristic indicator, not proof of threshold evasion.
    """
    if not isinstance(outgoing_transfers, list):
        return {"is_structuring": False, "suspicious_tx_count": 0}

    smurf_count = 0

    for tx in outgoing_transfers:
        value = _get_valid_amount(tx)

        if value is not None and 8500.0 <= value <= 9999.0:
            smurf_count += 1

    return {
        "is_structuring": smurf_count >= 2,
        "suspicious_tx_count": smurf_count,
    }
