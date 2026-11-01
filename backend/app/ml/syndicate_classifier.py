
"""
Syndicate Typology & Modus Operandi (MO) Forensic Classifier.

Classifies on-chain behavioral indicators into screening typologies.
These classifications are heuristic indicators, not proof of criminal activity.
"""

from typing import Any, Dict


TYPOLOGY_DEFINITIONS = {
    "TELEGRAM_TASK_FRAUD": {
        "name": "TRON-Based Peeling Pattern",
        "description": (
            "A peeling pattern was detected on a TRON-related chain. "
            "This pattern may be consistent with multi-hop fund distribution, "
            "but does not independently establish Telegram task fraud."
        ),
        "statutory_violation": (
            "Potentially relevant legal provisions require independent "
            "verification and legal review."
        ),
    },
    "PIG_BUTCHERING_SHA_ZHU_PAN": {
        "name": "Investment-Related Peeling Pattern",
        "description": (
            "A peeling pattern was detected. This may indicate staged fund "
            "distribution, but transaction patterns alone cannot establish "
            "investment fraud or pig-butchering activity."
        ),
        "statutory_violation": (
            "Potentially relevant legal provisions require independent "
            "verification and legal review."
        ),
    },
    "MIXER_OBSCURATION": {
        "name": "Mixer or Privacy-Service Exposure",
        "description": (
            "The address is associated with a configured mixer or "
            "privacy-related service directory entry. This is a screening "
            "indicator and does not establish criminal intent."
        ),
        "statutory_violation": (
            "Potentially relevant legal provisions require independent "
            "verification and legal review."
        ),
    },
    "P2P_SMURFING_RING": {
        "name": "Structuring-Like Transaction Pattern",
        "description": (
            "Transaction amounts exhibit a structuring-like pattern. "
            "This indicator requires contextual investigation and does not "
            "by itself establish coordinated P2P smurfing."
        ),
        "statutory_violation": (
            "Potentially relevant legal provisions require independent "
            "verification and legal review."
        ),
    },
    "STANDARD_RAPID_MULE": {
        "name": "Intermediary Transaction Activity",
        "description": (
            "No sufficiently specific typology signal was established. "
            "The address is retained under the default classification for "
            "compatibility; rapid mule activity has not been confirmed."
        ),
        "statutory_violation": (
            "No specific statutory violation can be inferred from the "
            "available indicators alone."
        ),
    },
}


def _valid_bool(value: Any) -> bool:
    """Accept actual boolean values only."""
    return isinstance(value, bool) and value


def _normalize_chain(chain: Any) -> str:
    """Safely normalize a blockchain identifier."""
    if not isinstance(chain, str):
        return ""

    return chain.strip().upper()


def classify_syndicate_typology(
    chain: str,
    is_mixer: bool,
    is_peeling: bool,
    is_structuring: bool,
    is_rapid_forwarder: bool,
    dwell_time_seconds: Any,
    destination_found: bool,
    target_vasp_name: Any = None,
) -> Dict[str, Any]:
    """
    Classify the dominant behavioral indicator.

    Confidence values are heuristic scores, not calibrated probabilities.

    dwell_time_seconds and target_vasp_name are retained for API
    compatibility. They are not currently used as independent
    classification signals.
    """

    normalized_chain = _normalize_chain(chain)

    mixer_detected = _valid_bool(is_mixer)
    peeling_detected = _valid_bool(is_peeling)
    structuring_detected = _valid_bool(is_structuring)
    rapid_forwarder_detected = _valid_bool(is_rapid_forwarder)
    destination_detected = _valid_bool(destination_found)

    # Priority 1: Known mixer or privacy-service exposure.
    if mixer_detected:
        typ = "MIXER_OBSCURATION"
        confidence = 0.96

    # Priority 2: Peeling pattern on TRON-related chains.
    elif peeling_detected and (
        "TRON" in normalized_chain or "TRC" in normalized_chain
    ):
        typ = "TELEGRAM_TASK_FRAUD"
        confidence = 0.75

    # Priority 3: Structuring-like transaction pattern.
    elif structuring_detected:
        typ = "P2P_SMURFING_RING"
        confidence = 0.78

    # Priority 4: Rapid forwarder with a detected destination.
    elif rapid_forwarder_detected and destination_detected:
        typ = "STANDARD_RAPID_MULE"
        confidence = 0.80

    # Priority 5: Peeling pattern on other chains.
    elif peeling_detected:
        typ = "PIG_BUTCHERING_SHA_ZHU_PAN"
        confidence = 0.70

    # Default: insufficient evidence for a specific typology.
    else:
        typ = "STANDARD_RAPID_MULE"
        confidence = 0.30

    details = TYPOLOGY_DEFINITIONS[typ]

    return {
        "typology_code": typ,
        "typology_name": details["name"],
        "confidence": confidence,
        "description": details["description"],
        "statutory_violation": details["statutory_violation"],
    }
