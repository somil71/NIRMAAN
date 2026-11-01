
from app.ml.mixer_directory import KNOWN_MIXERS, identify_mixer_entity
from app.ml.scorer import calculate_node_risk


def test_unknown_address_is_not_identified_as_mixer():
    result = identify_mixer_entity(
        "0x0000000000000000000000000000000000000001"
    )
    assert result is None


def test_mixer_lookup_respects_chain():
    address = "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b"

    assert identify_mixer_entity(address, chain="ETH") is not None
    assert identify_mixer_entity(address, chain="TRON") is None


def test_mixer_directory_metadata_is_not_verified_by_default():
    for entry in KNOWN_MIXERS.values():
        assert entry["verification_status"] == "UNVERIFIED"
        assert entry["sanctions_status"] == "NOT_VERIFIED"


def test_vasp_is_low_risk_when_not_directory_matched():
    result = calculate_node_risk(
        address="0x0000000000000000000000000000000000000001",
        node_type="VASP_HOT",
        incoming_transfers=[],
        outgoing_transfers=[],
        is_vasp=True,
        chain="ETH",
    )

    assert result["risk_tier"] == "LOW"
    assert result["risk_score"] == 0.08
    assert "IDENTIFIED_EXCHANGE_VAULT" in result["flags"]
