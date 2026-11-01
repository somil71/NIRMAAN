
"""
Configured Mixer and Privacy-Service Directory.

IMPORTANT:
The addresses below are inherited project configuration entries.
Their current ownership, chain deployment, and sanctions status
have not been independently verified.

Do not use this directory as authoritative sanctions intelligence.
Verify addresses against primary sources before operational use.
"""

from typing import Any, Dict, List, Optional


# Recognized EVM chain identifiers.
EVM_CHAINS = {
    "ethereum",
    "eth",
    "bsc",
    "bnb",
    "arbitrum",
    "polygon",
    "avalanche",
    "optimism",
    "base",
    "evm",
}


# Existing project entries retained for compatibility.
# Their verification status is explicitly marked.
KNOWN_MIXERS: Dict[str, Dict[str, Any]] = {
    # Tornado Cash pool addresses.
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": {
        "name": "Tornado Cash: 0.1 ETH",
        "category": "MIXER",
        "protocol": "Tornado Cash",
        "risk_tier": "CRITICAL",
        "chains": ["ethereum"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": {
        "name": "Tornado Cash: 1 ETH",
        "category": "MIXER",
        "protocol": "Tornado Cash",
        "risk_tier": "CRITICAL",
        "chains": ["ethereum"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": {
        "name": "Tornado Cash: 10 ETH",
        "category": "MIXER",
        "protocol": "Tornado Cash",
        "risk_tier": "CRITICAL",
        "chains": ["ethereum"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },
    "0xa160cdab22498500032724c218144c9e32d49c74": {
        "name": "Tornado Cash: 100 ETH",
        "category": "MIXER",
        "protocol": "Tornado Cash",
        "risk_tier": "CRITICAL",
        "chains": ["ethereum"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },
    "0x0836222f2b2b24a3f36f98668ed8f0b38d1a872f": {
        "name": "Tornado Cash: 10,000 USDT",
        "category": "MIXER",
        "protocol": "Tornado Cash",
        "risk_tier": "CRITICAL",
        "chains": ["ethereum"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },
    "0x169ad27a470d064ddec0d0c77c570b2265202eac": {
        "name": "Tornado Cash: 100,000 USDT",
        "category": "MIXER",
        "protocol": "Tornado Cash",
        "risk_tier": "CRITICAL",
        "chains": ["ethereum"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },

    # Railgun project entry.
    "0xfa7093cdd9ee6932b4eb2c9e1cde7ce00b1fa4b9": {
        "name": "Railgun: Configured Address",
        "category": "PRIVACY_POOL",
        "protocol": "Railgun",
        "risk_tier": "HIGH",
        "chains": ["evm"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },

    # FixedFloat project entry.
    "0x4e5b2e1dc63f6b91cb6cd759936495434c7e972f": {
        "name": "FixedFloat: Configured Address",
        "category": "NON_KYC_SWAP",
        "protocol": "FixedFloat",
        "risk_tier": "HIGH",
        "chains": ["evm"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },

    # TRON project entry.
    "TJY2fT4b4r8uX7pE9wS2vD6nM3kL1qA0zZ": {
        "name": "TronAnonymousPool: Configured Address",
        "category": "MIXER",
        "protocol": "Tron Anonymous Relay",
        "risk_tier": "CRITICAL",
        "chains": ["tron"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },

    # Bitcoin project entries.
    "16Gv5z7YV7z1Z5Yd5z7YV7z1Z5Yd5z7YV7": {
        "name": "Sinbad: Configured Address",
        "category": "MIXER",
        "protocol": "Sinbad",
        "risk_tier": "CRITICAL",
        "chains": ["bitcoin"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },
    "bc1qa5wkgaew2dkv56kfvj49j0av5nmar2w4n6cacw": {
        "name": "Blender: Configured Address",
        "category": "MIXER",
        "protocol": "Blender.io",
        "risk_tier": "CRITICAL",
        "chains": ["bitcoin"],
        "verification_status": "UNVERIFIED",
        "sanctions_status": "NOT_VERIFIED",
    },
}


def _normalize_chain(chain: Any) -> Optional[str]:
    """Normalize common blockchain names and aliases."""

    if not isinstance(chain, str) or not chain.strip():
        return None

    value = chain.strip().lower()

    aliases = {
        "eth": "ethereum",
        "ethereum mainnet": "ethereum",
        "ethereum (erc-20)": "ethereum",
        "bep20": "bsc",
        "bep-20": "bsc",
        "bsc (bep-20)": "bsc",
        "binance": "bsc",
        "binance smart chain": "bsc",
        "bnb chain": "bsc",
        "arb": "arbitrum",
        "arbitrum one": "arbitrum",
        "trx": "tron",
        "tron trc20": "tron",
        "tron (trc-20)": "tron",
        "btc": "bitcoin",
        "bitcoin mainnet": "bitcoin",
        "bitcoin (utxo)": "bitcoin",
    }

    return aliases.get(value, value)


def _chain_matches(
    requested_chain: Optional[str],
    supported_chains: List[str],
) -> bool:
    """Check whether a directory entry supports the requested chain."""

    if requested_chain is None:
        return True

    requested = _normalize_chain(requested_chain)

    if requested is None:
        return False

    if not isinstance(supported_chains, (list, tuple, set)):
        return False

    supported = {
        _normalize_chain(item)
        for item in supported_chains
        if isinstance(item, str)
    }

    if requested in supported:
        return True

    if "evm" in supported and requested in EVM_CHAINS:
        return True

    return False


def identify_mixer_entity(
    address: str,
    chain: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Find a configured service by wallet address.

    EVM addresses are compared case-insensitively.
    Non-EVM addresses are compared case-sensitively.

    When chain is supplied, entries are filtered by chain.
    When chain is omitted, all configured entries are checked
    for backwards compatibility.

    Returned metadata is copied so callers cannot mutate the
    global directory accidentally.
    """

    if not isinstance(address, str) or not address.strip():
        return None

    candidate = address.strip()

    for registered_address, metadata in KNOWN_MIXERS.items():
        if not isinstance(metadata, dict):
            continue

        supported_chains = metadata.get("chains", [])

        if not _chain_matches(chain, supported_chains):
            continue

        is_evm_entry = any(
            _normalize_chain(item) in EVM_CHAINS
            for item in supported_chains
            if isinstance(item, str)
        )

        if is_evm_entry:
            matched = candidate.lower() == registered_address.lower()
        else:
            matched = candidate == registered_address

        if matched:
            return dict(metadata)

    return None
