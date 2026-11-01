
import math
import networkx as nx

from app.ml.graph_clustering import (
    build_nx_graph,
    calculate_graph_centrality,
    detect_circular_layering,
    calculate_dispersion_entropy,
    compute_transfer_velocity,
)

def test_build_graph_ignores_invalid_edges():
    graph = build_nx_graph([
        {"source": "A", "target": "B", "usd_value": "100"},
        {"source": "B", "target": "C", "usd_value": "invalid"},
        {"source": None, "target": "D", "usd_value": 50},
        None,
        {"source": "C", "target": "D", "usd_value": -10},
    ])

    assert graph.has_edge("A", "B")
    assert graph["A"]["B"]["weight"] == 100.0

    # Invalid and negative transactions must be skipped.
    assert not graph.has_edge("B", "C")
    assert not graph.has_edge("C", "D")

    # Invalid endpoints must also be skipped.
    assert "D" not in graph

def test_build_graph_handles_invalid_timestamps():
    graph = build_nx_graph([
        {
            "source": "A",
            "target": "B",
            "usd_value": 10,
            "timestamp": "invalid",
        }
    ])

    assert graph["A"]["B"]["timestamp"] == 0


def test_entropy_ignores_invalid_and_negative_values():
    transfers = [
        {"usd_value": 100},
        {"usd_value": 100},
        {"usd_value": -50},
        {"usd_value": "invalid"},
        {"usd_value": float("nan")},
    ]

    assert calculate_dispersion_entropy(transfers) == 1.0


def test_entropy_returns_zero_for_empty_or_single_transfer():
    assert calculate_dispersion_entropy([]) == 0.0
    assert calculate_dispersion_entropy([{"usd_value": 100}]) == 0.0


def test_velocity_detects_ultra_rapid_forwarding():
    incoming = [{"timestamp": 1000}]
    outgoing = [{"timestamp": 1300}]

    result = compute_transfer_velocity(incoming, outgoing)

    assert result["dwell_time_seconds"] == 300
    assert result["is_rapid_forwarder"] is True
    assert result["velocity_tier"] == "ULTRA_RAPID (<5m)"


def test_velocity_detects_rapid_forwarding():
    result = compute_transfer_velocity(
        [{"timestamp": 1000}],
        [{"timestamp": 1001 + 300}],
    )

    assert result["is_rapid_forwarder"] is True
    assert result["velocity_tier"] == "RAPID (<30m)"


def test_velocity_rejects_invalid_timestamps():
    result = compute_transfer_velocity(
        [{"timestamp": "invalid"}],
        [{"timestamp": "also-invalid"}],
    )

    assert result["dwell_time_seconds"] is None
    assert result["is_rapid_forwarder"] is False


def test_velocity_does_not_flag_outgoing_before_incoming():
    result = compute_transfer_velocity(
        [{"timestamp": 2000}],
        [{"timestamp": 1000}],
    )

    assert result["dwell_time_seconds"] is None
    assert result["is_rapid_forwarder"] is False


def test_cycle_detection_finds_two_node_cycle():
    graph = nx.DiGraph()
    graph.add_edges_from([
        ("A", "B"),
        ("B", "A"),
    ])

    result = detect_circular_layering(graph, "A")

    assert result["has_cycle"] is True
    assert result["cycle_length"] == 2


def test_cycle_detection_finds_longer_cycle():
    graph = nx.DiGraph()
    graph.add_edges_from([
        ("A", "B"),
        ("B", "C"),
        ("C", "D"),
        ("D", "A"),
    ])

    result = detect_circular_layering(graph, "A")

    assert result["has_cycle"] is True
    assert result["cycle_length"] == 4


def test_cycle_detection_ignores_cycles_not_containing_address():
    graph = nx.DiGraph()
    graph.add_edges_from([
        ("A", "B"),
        ("B", "C"),
        ("C", "B"),
    ])

    result = detect_circular_layering(graph, "A")

    assert result["has_cycle"] is False


def test_centrality_returns_zero_for_missing_address():
    graph = nx.DiGraph()
    graph.add_edge("A", "B", weight=10)

    result = calculate_graph_centrality(graph, "UNKNOWN")

    assert result["in_degree"] == 0
    assert result["out_degree"] == 0
    assert result["betweenness"] == 0.0
    assert result["pagerank"] == 0.0


def test_centrality_calculates_for_existing_address():
    graph = nx.DiGraph()
    graph.add_edge("A", "B", weight=10)
    graph.add_edge("B", "C", weight=20)

    result = calculate_graph_centrality(graph, "B")

    assert result["in_degree"] == 1
    assert result["out_degree"] == 1
    assert 0.0 <= result["pagerank"] <= 1.0
    assert 0.0 <= result["betweenness"] <= 1.0
