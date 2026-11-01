
import pytest

from app.ml.peeling import (
    analyze_peeling_chain,
    detect_structuring_smurfing,
)


@pytest.mark.parametrize("invalid", [
    "invalid", -100, True, float("nan"),
    float("inf"), float("-inf"), None,
])
def test_peeling_rejects_invalid_amounts(invalid):
    result = analyze_peeling_chain(
        [],
        [{"usd_value": invalid}, {"usd_value": 9500.0}],
    )
    assert result["is_peeling_chain"] is False


def test_peeling_accepts_two_outputs():
    result = analyze_peeling_chain(
        [],
        [{"usd_value": 500.0}, {"usd_value": 9500.0}],
    )
    assert result["is_peeling_chain"] is True
    assert result["peel_ratio"] == 0.05


def test_peeling_accepts_three_outputs():
    result = analyze_peeling_chain(
        [],
        [
            {"usd_value": 500.0},
            {"usd_value": 4500.0},
            {"usd_value": 5000.0},
        ],
    )
    assert result["is_peeling_chain"] is True


def test_peeling_rejects_missing_amount():
    result = analyze_peeling_chain([], [{}, {"usd_value": 9500.0}])
    assert result["is_peeling_chain"] is False


def test_peeling_rejects_zero_amount():
    result = analyze_peeling_chain(
        [],
        [{"usd_value": 0}, {"usd_value": 9500}],
    )
    assert result["is_peeling_chain"] is False


def test_structuring_ignores_invalid_amounts():
    result = detect_structuring_smurfing([
        {"usd_value": "invalid"},
        {"usd_value": True},
        {"usd_value": 9400.0},
        {"usd_value": 9850.0},
    ])
    assert result["is_structuring"] is True
    assert result["suspicious_tx_count"] == 2


def test_structuring_rejects_invalid_values_without_crashing():
    result = detect_structuring_smurfing([
        {"usd_value": float("nan")},
        {"usd_value": float("inf")},
        {"usd_value": -9000},
        {"usd_value": "invalid"},
    ])
    assert result["is_structuring"] is False
    assert result["suspicious_tx_count"] == 0


def test_structuring_requires_two_suspicious_transfers():
    result = detect_structuring_smurfing([
        {"usd_value": 9400.0},
    ])
    assert result["is_structuring"] is False
