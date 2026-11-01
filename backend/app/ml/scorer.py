
"""
Composite Anomaly & Risk Scorer for Blockchain Forensic Nodes.

Aggregates graph heuristics, peeling metrics, service-directory
screening, and transaction velocity into a heuristic risk score.

Risk scores are triage indicators, not calibrated probabilities
or proof of criminal activity.
"""

from typing import List, Dict, Any, Optional

from app.ml.mixer_directory import identify_mixer_entity
from app.ml.peeling import (
    analyze_peeling_chain,
    detect_structuring_smurfing,
)
from app.ml.graph_clustering import (
    calculate_dispersion_entropy,
    compute_transfer_velocity,
)
from app.ml.syndicate_classifier import classify_syndicate_typology


def _safe_transfers(value: Any) -> List[Dict[str, Any]]:
    """Return only dictionary transaction records."""
    if not isinstance(value, (list, tuple)):
        return []

    return [item for item in value if isinstance(item, dict)]


def calculate_node_risk(
    address: str,
    node_type: str,
    incoming_transfers: List[Dict[str, Any]],
    outgoing_transfers: List[Dict[str, Any]],
    is_vasp: bool = False,
    chain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate a heuristic risk profile for a wallet address.

    The feature vector retains the existing eight-dimensional schema:
    0 incoming count
    1 outgoing count
    2 rapid-forwarder indicator
    3 peeling ratio
    4 suspicious transaction count
    5 dispersion entropy
    6 mixer proximity / service exposure
    7 exchange custody indicator
    """

    incoming = _safe_transfers(incoming_transfers)
    outgoing = _safe_transfers(outgoing_transfers)

    chain_for_typology = (
        chain.strip() if isinstance(chain, str) and chain.strip()
        else "TRON (TRC-20)"
    )

    flags: List[str] = []

    # 1. Configured service-directory screening.
    mixer_info = identify_mixer_entity(address, chain=chain)

    if mixer_info:
        category = str(
            mixer_info.get("category", "UNKNOWN")
        ).upper()

        service_risk = {
            "MIXER": (0.99, "CRITICAL"),
            "PRIVACY_POOL": (0.78, "HIGH"),
            "NON_KYC_SWAP": (0.70, "HIGH"),
            "BRIDGE": (0.65, "HIGH"),
        }

        risk_score, risk_tier = service_risk.get(
            category,
            (0.60, "HIGH"),
        )

        is_mixer = category in {"MIXER", "PRIVACY_POOL"}

        flags.append(
            f"KNOWN_SERVICE_ENTITY:{category}:"
            f"{mixer_info.get('protocol', 'Unknown')}"
        )

        typology = classify_syndicate_typology(
            chain=chain_for_typology,
            is_mixer=is_mixer,
            is_peeling=False,
            is_structuring=False,
            is_rapid_forwarder=False,
            dwell_time_seconds=None,
            destination_found=False,
        )

        return {
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "is_mixer": is_mixer,
            "is_high_risk_service": True,
            "service_category": category,
            "mixer_details": mixer_info,
            "is_peeling": False,
            "peeling_details": None,
            "velocity_details": None,
            "flags": flags,
            "feature_vector": [
                float(len(incoming)),
                float(len(outgoing)),
                0.0,
                0.0,
                0.0,
                0.0,
                1.0 if is_mixer else 0.0,
                0.0,
            ],
            "typology": typology,
            "explanation": (
                f"Address matches a configured {category} directory "
                f"entry ({mixer_info.get('name', 'Unknown service')}). "
                "This is a screening indicator, not proof of "
                "illicit activity. Verify the address and its "
                "provenance independently."
            ),
        }

    # 2. Restore the original legitimate VASP low-risk behavior.
    # Mixer-directory screening intentionally takes precedence.
    if is_vasp or node_type in {"VASP_HOT", "VASP_DEPOSIT"}:
        return {
            "risk_score": 0.08,
            "risk_tier": "LOW",
            "is_mixer": False,
            "is_high_risk_service": False,
            "service_category": None,
            "mixer_details": None,
            "is_peeling": False,
            "peeling_details": None,
            "velocity_details": None,
            "flags": ["IDENTIFIED_EXCHANGE_VAULT"],
            "feature_vector": [
                0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ],
            "typology": None,
            "explanation": (
                "Identified custodial exchange vault or "
                "institutional treasury. Classification should "
                "be supported by the VASP directory evidence."
            ),
        }

    # 3. Base score from forensic position.
    if node_type == "SUSPECT":
        base_score = 0.85
        flags.append("REPORTED_FRAUD_SEED")

    elif node_type == "MULE":
        base_score = 0.60
        flags.append("INTERMEDIARY_HOP_MULE")

    else:
        base_score = 0.30

    # 4. Peeling-chain analysis.
    peel_analysis = analyze_peeling_chain(incoming, outgoing)

    if peel_analysis["is_peeling_chain"]:
        base_score += 0.25 * peel_analysis["peel_confidence"]

        flags.append(
            "ALGORITHMIC_PEELING_CHAIN("
            f"ratio={peel_analysis['peel_ratio']:.1%})"
        )

    # 5. Structuring analysis.
    struct_analysis = detect_structuring_smurfing(outgoing)

    if struct_analysis["is_structuring"]:
        base_score += 0.20

        flags.append(
            "TRANSACTION_STRUCTURING("
            f"{struct_analysis['suspicious_tx_count']}_txs)"
        )

    # 6. Velocity and dwell-time analysis.
    velocity_info = compute_transfer_velocity(
        incoming,
        outgoing,
    )

    if velocity_info["is_rapid_forwarder"]:
        base_score += 0.12

        dwell_seconds = velocity_info["dwell_time_seconds"] or 0

        flags.append(
            f"RAPID_FORWARDING_BOT(dwell={dwell_seconds}s)"
        )

    # 7. Outgoing volume and fan-out entropy.
    dispersion_entropy = calculate_dispersion_entropy(outgoing)

    if len(outgoing) > 10:
        base_score += 0.10
        flags.append("HIGH_FANOUT_DISTRIBUTION")

    # 8. Clamp score.
    final_score = max(0.05, min(0.98, base_score))

    # 9. Determine risk tier.
    if final_score >= 0.80:
        tier = "CRITICAL"
    elif final_score >= 0.60:
        tier = "HIGH"
    elif final_score >= 0.35:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    # 10. Typology classification.
    typology = classify_syndicate_typology(
        chain=chain_for_typology,
        is_mixer=False,
        is_peeling=peel_analysis["is_peeling_chain"],
        is_structuring=struct_analysis["is_structuring"],
        is_rapid_forwarder=velocity_info["is_rapid_forwarder"],
        dwell_time_seconds=velocity_info["dwell_time_seconds"],
        destination_found=False,
    )

    # 11. Eight-dimensional feature vector.
    feature_vector = [
        round(float(len(incoming)), 2),
        round(float(len(outgoing)), 2),
        round(
            float(1.0 if velocity_info["is_rapid_forwarder"] else 0.0),
            2,
        ),
        round(float(peel_analysis["peel_ratio"]), 3),
        round(float(struct_analysis["suspicious_tx_count"]), 2),
        round(float(dispersion_entropy), 3),
        0.0,
        0.0,
    ]

    # 12. Human-readable explanation.
    explanation_parts = []

    if "REPORTED_FRAUD_SEED" in flags:
        explanation_parts.append(
            "Reported victim deposit origin."
        )

    if peel_analysis["is_peeling_chain"]:
        explanation_parts.append(
            "Potential peeling behavior detected with "
            f"${peel_analysis['peeled_amount_usd']:,.2f} "
            "identified as the smallest output."
        )

    if struct_analysis["is_structuring"]:
        explanation_parts.append(
            "Structuring-like activity detected across "
            f"{struct_analysis['suspicious_tx_count']} transfers."
        )

    if velocity_info["is_rapid_forwarder"]:
        explanation_parts.append(
            "Short transaction dwell time detected: "
            f"{velocity_info['dwell_time_seconds']} seconds."
        )

    if not explanation_parts:
        explanation_parts.append(
            "Intermediary transfer node with no specific "
            "high-risk behavioral pattern established."
        )

    return {
        "risk_score": round(final_score, 2),
        "risk_tier": tier,
        "is_mixer": False,
        "is_high_risk_service": False,
        "service_category": None,
        "mixer_details": None,
        "is_peeling": peel_analysis["is_peeling_chain"],
        "peeling_details": peel_analysis,
        "velocity_details": velocity_info,
        "typology": typology,
        "feature_vector": feature_vector,
        "flags": flags,
        "explanation": " ".join(explanation_parts),
    }
