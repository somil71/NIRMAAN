
"""
Graph Analytics, Community Detection & Laundering Topology Clustering Engine.

Computes graph centrality, fan-out entropy, circular layering detection,
and transaction velocity metrics.
"""

from typing import List, Dict, Any, Optional
import math

import networkx as nx


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

MAX_CYCLE_LENGTH = 6
MAX_EXPLORED_PATHS = 5000


# ---------------------------------------------------------
# Shared validation helpers
# ---------------------------------------------------------

def _safe_float(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    """Convert a value to a finite float, rejecting booleans."""
    if value is None or isinstance(value, bool):
        return default

    try:
        result = float(value)

        if math.isfinite(result):
            return result

    except (TypeError, ValueError, OverflowError):
        pass

    return default


def _safe_timestamp(value: Any) -> Optional[int]:
    """Convert a valid positive integer timestamp."""
    number = _safe_float(value)

    if number is None or number <= 0:
        return None

    if not number.is_integer():
        return None

    return int(number)


def _get_transfer_value(tx: Dict[str, Any]) -> float:
    """Read a transaction value safely, preferring usd_value."""
    if not isinstance(tx, dict):
        return 0.0

    raw_value = tx.get("usd_value")

    if raw_value is None:
        raw_value = tx.get("amount")

    value = _safe_float(raw_value, default=0.0)

    return value if value is not None and value >= 0 else 0.0


def _get_timestamp(tx: Dict[str, Any]) -> Optional[int]:
    """Safely extract a transaction timestamp."""
    if not isinstance(tx, dict):
        return None

    return _safe_timestamp(tx.get("timestamp"))


# ---------------------------------------------------------
# 1. NetworkX graph construction
# ---------------------------------------------------------

def build_nx_graph(edges: List[Dict[str, Any]]) -> nx.DiGraph:
    """
    Construct a directed NetworkX graph from valid edge dictionaries.

    Invalid endpoints and explicitly malformed, negative, or non-finite
    transaction values are skipped. Missing values default to zero.
    """
    graph = nx.DiGraph()

    if not isinstance(edges, (list, tuple)):
        return graph

    for edge in edges:
        if not isinstance(edge, dict):
            continue

        src = edge.get("source") or edge.get("from")
        tgt = edge.get("target") or edge.get("to")

        if not isinstance(src, str) or not isinstance(tgt, str):
            continue

        src = src.strip()
        tgt = tgt.strip()

        if not src or not tgt:
            continue

        raw_value = edge.get("usd_value")

        if raw_value is None:
            raw_value = edge.get("amount")

        if raw_value is None:
            value = 0.0
        else:
            value = _safe_float(raw_value)

        if value is None or value < 0:
            continue

        timestamp = _safe_timestamp(edge.get("timestamp")) or 0
        tx_hash = edge.get("tx_hash", "")

        graph.add_edge(
            src,
            tgt,
            weight=value,
            timestamp=timestamp,
            tx_hash=tx_hash if isinstance(tx_hash, str) else "",
        )

    return graph


# ---------------------------------------------------------
# 2. Graph centrality
# ---------------------------------------------------------

def calculate_graph_centrality(
    G: nx.DiGraph,
    address: str,
) -> Dict[str, float]:
    """
    Compute node degree, approximate betweenness centrality,
    and PageRank.
    """

    default_result = {
        "in_degree": 0,
        "out_degree": 0,
        "betweenness": 0.0,
        "pagerank": 0.0,
    }

    if (
        not isinstance(G, nx.DiGraph)
        or not isinstance(address, str)
        or not address.strip()
        or address not in G
    ):
        return default_result

    in_degree = G.in_degree(address)
    out_degree = G.out_degree(address)

    node_count = G.number_of_nodes()

    if node_count == 0:
        return default_result

    # PageRank
    try:
        pagerank = nx.pagerank(
            G,
            weight="weight",
            max_iter=100,
            tol=1e-6,
        )

        pagerank_score = pagerank.get(address, 0.0)

    except Exception:
        pagerank_score = 1.0 / node_count

    # Betweenness centrality
    try:
        sample_size = min(100, node_count)

        if node_count > 100:
            betweenness = nx.betweenness_centrality(
                G,
                k=sample_size,
                normalized=True,
                weight=None,
                seed=42,
            )
        else:
            betweenness = nx.betweenness_centrality(
                G,
                normalized=True,
                weight=None,
            )

        betweenness_score = betweenness.get(address, 0.0)

    except Exception:
        betweenness_score = 0.0

    return {
        "in_degree": in_degree,
        "out_degree": out_degree,
        "betweenness": round(float(betweenness_score), 4),
        "pagerank": round(float(pagerank_score), 4),
    }


# ---------------------------------------------------------
# 3. Circular layering detection
# ---------------------------------------------------------

def detect_circular_layering(
    G: nx.DiGraph,
    address: str,
) -> Dict[str, Any]:
    """
    Detect directed cycles involving the specified address.

    Searches for cycles of length 2 to MAX_CYCLE_LENGTH.
    Limits explored paths to MAX_EXPLORED_PATHS.

    search_complete indicates whether the bounded search exhausted
    all eligible paths. False means no cycle was found before the
    search limit was reached; it does not prove that no cycle exists.
    """

    if (
        not isinstance(G, nx.DiGraph)
        or not isinstance(address, str)
        or not address.strip()
        or address not in G
    ):
        return {
            "has_cycle": False,
            "cycle_path": [],
            "search_complete": True,
        }

    explored = 0

    # Each path starts at the requested address.
    stack = [
        (neighbor, [address, neighbor], {address, neighbor})
        for neighbor in G.successors(address)
        if neighbor != address
    ]

    while stack and explored < MAX_EXPLORED_PATHS:
        current, path, visited = stack.pop()
        explored += 1

        for neighbor in G.successors(current):

            # Returning to the original address completes a cycle.
            if neighbor == address and len(path) >= 2:
                return {
                    "has_cycle": True,
                    "cycle_path": path,
                    "cycle_length": len(path),
                    "search_complete": True,
                }

            # Do not revisit intermediate nodes.
            if neighbor in visited:
                continue

            # The completed cycle must not exceed the maximum length.
            if len(path) >= MAX_CYCLE_LENGTH:
                continue

            stack.append(
                (
                    neighbor,
                    path + [neighbor],
                    visited | {neighbor},
                )
            )

    return {
        "has_cycle": False,
        "cycle_path": [],
        "search_complete": not bool(stack),
    }


# ---------------------------------------------------------
# 4. Dispersion entropy
# ---------------------------------------------------------

def calculate_dispersion_entropy(
    outgoing_transfers: List[Dict[str, Any]],
) -> float:
    """
    Compute Shannon entropy of valid positive outgoing transfer amounts.

    Higher entropy indicates a more diversified distribution of amounts.
    """

    if not isinstance(outgoing_transfers, (list, tuple)):
        return 0.0

    values = [
        _get_transfer_value(tx)
        for tx in outgoing_transfers
        if isinstance(tx, dict)
    ]

    positive_values = [
        value
        for value in values
        if value > 0 and math.isfinite(value)
    ]

    if len(positive_values) <= 1:
        return 0.0

    total = math.fsum(positive_values)

    if not math.isfinite(total) or total <= 0:
        return 0.0

    probabilities = [
        value / total
        for value in positive_values
    ]

    entropy = -math.fsum(
        probability * math.log2(probability)
        for probability in probabilities
        if probability > 0
    )

    return round(entropy, 3)


# ---------------------------------------------------------
# 5. Transfer velocity and dwell time
# ---------------------------------------------------------

def compute_transfer_velocity(
    incoming_transfers: List[Dict[str, Any]],
    outgoing_transfers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculate dwell time between the first valid receipt and
    the earliest valid outgoing transaction occurring afterward.

    Under 5 minutes: ULTRA_RAPID
    Under 30 minutes: RAPID
    Under 2 hours: MODERATE
    Above 2 hours: SLOW
    """

    normal_result = {
        "dwell_time_seconds": None,
        "is_rapid_forwarder": False,
        "velocity_tier": "NORMAL",
    }

    if not isinstance(incoming_transfers, (list, tuple)):
        return normal_result.copy()

    if not isinstance(outgoing_transfers, (list, tuple)):
        return normal_result.copy()

    if not incoming_transfers or not outgoing_transfers:
        return normal_result.copy()

    incoming_times = [
        timestamp
        for tx in incoming_transfers
        if isinstance(tx, dict)
        for timestamp in [_get_timestamp(tx)]
        if timestamp is not None
    ]

    outgoing_times = [
        timestamp
        for tx in outgoing_transfers
        if isinstance(tx, dict)
        for timestamp in [_get_timestamp(tx)]
        if timestamp is not None
    ]

    if not incoming_times or not outgoing_times:
        return normal_result.copy()

    first_in = min(incoming_times)

    # Only consider outgoing transfers at or after the first receipt.
    valid_outgoing_times = [
        timestamp
        for timestamp in outgoing_times
        if timestamp >= first_in
    ]

    if not valid_outgoing_times:
        return normal_result.copy()

    first_out = min(valid_outgoing_times)

    dwell = first_out - first_in

    if dwell <= 300:
        tier = "ULTRA_RAPID (<5m)"
        rapid = True

    elif dwell <= 1800:
        tier = "RAPID (<30m)"
        rapid = True

    elif dwell <= 7200:
        tier = "MODERATE (<2h)"
        rapid = False

    else:
        tier = "SLOW (>2h)"
        rapid = False

    return {
        "dwell_time_seconds": dwell,
        "is_rapid_forwarder": rapid,
        "velocity_tier": tier,
    }
