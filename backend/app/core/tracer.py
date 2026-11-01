"""
Multi-Chain Blockchain Tracing & Heuristic VASP Resolver Engine
Bounded BFS pathfinding using NetworkX with Exchange Deposit Sweep Detection.
Integrated with Machine Learning Risk Scorer, Peeling Classifier & Mixer Detection.
Supports TRON, EVM (Ethereum/BSC), and Bitcoin.
"""
import os
import json
import time
import uuid
import hashlib
import logging
from typing import Dict, Any, Tuple, Optional, List
import networkx as nx

from app.models.schemas import TraceRequest, TraceResponse, GraphNode, GraphEdge, TargetVASP
from app.crawlers.multi_chain_crawler import MultiChainCrawler, detect_chain
from app.ml.scorer import calculate_node_risk
from app.core.legal_notice import compute_canonical_evidence_digest
from app.crawlers.tron import DEMO_FIXTURE_TRAIL
from app.crawlers.evm import DEMO_EVM_TRAIL
from app.crawlers.btc import DEMO_BTC_TRAIL
from app.ml.graph_clustering import build_nx_graph

logger = logging.getLogger("nirmaan.core.tracer")

class ForensicTracer:
    def __init__(self, vasp_db_path: Optional[str] = None):
        if not vasp_db_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            vasp_db_path = os.path.join(base_dir, "data", "vasp_directory.json")
        
        self.vasp_db = self._load_vasp_directory(vasp_db_path)
        self.crawler = MultiChainCrawler()

    def _load_vasp_directory(self, path: str) -> Dict[str, Any]:
        """Loads and indexes known VASP hot wallets (normalized for case-insensitive EVM match)."""
        hot_wallet_index = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for vasp_key, vasp_info in data.get("vasps", {}).items():
                    for addr in vasp_info.get("known_hot_wallets", []):
                        if addr.startswith("[TEST_STUB]"):
                            continue
                        # Store both original and lowercase for EVM addresses
                        normalized_key = addr.lower() if addr.startswith("0x") else addr
                        hot_wallet_index[normalized_key] = {
                            "vasp_key": vasp_key,
                            "original_address": addr,
                            "name": vasp_info["name"],
                            "fiu_registered": vasp_info["fiu_registered"],
                            "nodal_email": vasp_info["nodal_email"],
                            "law_enforcement_portal": vasp_info["law_enforcement_portal"],
                            "source": vasp_info.get("source", "FIU-IND Verified Registry"),
                            "verification_date": vasp_info.get("verification_date", "2026-10-31"),
                            "confidence": vasp_info.get("confidence", "HIGH")
                        }
        except Exception as e:
            logger.error(f"Failed to load VASP directory from {path}: {e}")
        return hot_wallet_index

    def _lookup_vasp(self, address: str) -> Optional[Dict[str, Any]]:
        key = address.lower() if address.startswith("0x") else address
        return self.vasp_db.get(key)

    async def trace(self, req: TraceRequest) -> TraceResponse:
        start_time = time.time()
        trace_id = f"tr_{uuid.uuid4().hex[:8]}"

        # Determine chain: allow explicit request override if specified, else detect
        if req.chain and req.chain.lower() in ("bsc", "binance", "binancesmartchain"):
            chain = "bsc"
        elif req.chain and req.chain.lower() in ("ethereum", "eth", "tron", "bitcoin", "btc"):
            chain = req.chain.lower()
            if chain == "eth":
                chain = "ethereum"
            elif chain == "btc":
                chain = "bitcoin"
        else:
            chain = detect_chain(req.seed_address)

        chain_label = {
            "tron": "TRON (TRC-20)",
            "ethereum": "Ethereum (ERC-20)",
            "bsc": "Binance Smart Chain (BEP-20)",
            "bitcoin": "Bitcoin (UTXO)"
        }.get(chain, "Multi-Chain")

        is_synthetic = bool(
            req.seed_address in DEMO_FIXTURE_TRAIL
            or req.seed_address in DEMO_BTC_TRAIL
            or any(req.seed_address.lower() == k.lower() for k in DEMO_EVM_TRAIL)
        )

        queue = [(req.seed_address, 0, "SUSPECT")]
        visited = set()

        nodes_map: Dict[str, GraphNode] = {
            req.seed_address: GraphNode(
                id=req.seed_address,
                address=req.seed_address,
                node_type="SUSPECT",
                label=f"Scam Origin ({chain_label})",
                balance_usd=0.0
            )
        }
        edges_list: List[GraphEdge] = []
        found_target_vasp: Optional[TargetVASP] = None

        while queue:
            if time.time() - start_time > 30.0:
                logger.warning(f"Trace {trace_id} exceeded maximum execution budget (30s). Halting BFS.")
                break
            curr_addr, depth, curr_type = queue.pop(0)

            if depth >= req.max_depth or curr_addr in visited:
                continue
            visited.add(curr_addr)

            # Direct check if current address is a known hot wallet
            direct_match = self._lookup_vasp(curr_addr)
            if direct_match:
                nodes_map[curr_addr].node_type = "VASP_HOT"
                nodes_map[curr_addr].label = f"{direct_match['name']} Hot Wallet"
                nodes_map[curr_addr].vasp_name = direct_match["name"]
                if not found_target_vasp:
                    found_target_vasp = TargetVASP(
                        name=direct_match["name"],
                        fiu_registered=direct_match["fiu_registered"],
                        deposit_address=curr_addr,
                        hot_wallet=curr_addr,
                        nodal_email=direct_match["nodal_email"],
                        law_enforcement_portal=direct_match["law_enforcement_portal"],
                        source=direct_match.get("source", "FIU-IND Verified Registry"),
                        verification_date=direct_match.get("verification_date", "2026-10-31"),
                        confidence=direct_match.get("confidence", "HIGH")
                    )
                continue

            # Fetch outbound transfers across appropriate crawler
            transfers = await self.crawler.fetch_transfers(curr_addr, chain=chain)

            for tx in transfers:
                tx_hash = tx.get("tx_hash")
                if not isinstance(tx_hash, str) or not tx_hash.strip():
                    logger.warning("Skipping transfer with missing or invalid tx_hash from %s", curr_addr)
                    continue
                recipient = tx["to"]
                raw_amount = tx["amount"]
                token = tx.get("token", "USDT")
                
                # Multi-Asset USD conversion with spot heuristics (ERR-07)
                token_upper = token.upper()
                if token_upper == "BTC":
                    usd_rate = 65000.0
                elif token_upper == "ETH":
                    usd_rate = 2600.0
                elif token_upper == "BNB":
                    usd_rate = 580.0
                elif token_upper == "TRX":
                    usd_rate = 0.16
                else:
                    usd_rate = 1.0
                usd_value = raw_amount * usd_rate

                # Apply value pruning constraint in USD
                if usd_value < req.min_usd_value:
                    continue

                vasp_meta = self._lookup_vasp(recipient)
                is_known_hot = vasp_meta is not None

                # Deposit Sweep Heuristic
                if is_known_hot:
                    if curr_addr in nodes_map and nodes_map[curr_addr].node_type != "SUSPECT":
                        nodes_map[curr_addr].node_type = "VASP_DEPOSIT"
                        nodes_map[curr_addr].label = f"{vasp_meta['name']} Deposit Forwarder"
                        nodes_map[curr_addr].vasp_name = vasp_meta["name"]

                    recipient_type = "VASP_HOT"
                    recipient_label = f"{vasp_meta['name']} Master Hot Wallet"
                    recipient_vasp = vasp_meta["name"]

                    if not found_target_vasp:
                        found_target_vasp = TargetVASP(
                            name=vasp_meta["name"],
                            fiu_registered=vasp_meta["fiu_registered"],
                            deposit_address=curr_addr,
                            hot_wallet=recipient,
                            sweep_tx_hash=tx["tx_hash"],
                            nodal_email=vasp_meta["nodal_email"],
                            law_enforcement_portal=vasp_meta["law_enforcement_portal"],
                            source=vasp_meta.get("source", "FIU-IND Verified Registry"),
                            verification_date=vasp_meta.get("verification_date", "2026-10-31"),
                            confidence=vasp_meta.get("confidence", "HIGH")
                        )
                else:
                    recipient_type = "MULE"
                    recipient_label = f"Intermediary Mule (Hop {depth + 1})"
                    recipient_vasp = None

                if recipient not in nodes_map:
                    nodes_map[recipient] = GraphNode(
                        id=recipient,
                        address=recipient,
                        node_type=recipient_type,
                        label=recipient_label,
                        vasp_name=recipient_vasp,
                        balance_usd=usd_value
                    )

                edge_obj = GraphEdge(
                    source=curr_addr,
                    target=recipient,
                    tx_hash=tx["tx_hash"],
                    amount=raw_amount,
                    token=token,
                    usd_value=usd_value,
                    timestamp=tx["timestamp"]
                )
                edges_list.append(edge_obj)

                if not is_known_hot:
                    queue.append((recipient, depth + 1, "MULE"))

        # ML Risk, Syndicate Typology & Graph Analytics Layer (Vertical 2)
        dominant_typology = None
        max_ml_score = 0.0

        for node_id, node in nodes_map.items():
            in_edges = [e.model_dump() for e in edges_list if e.target == node_id]
            out_edges = [e.model_dump() for e in edges_list if e.source == node_id]
            
            risk_profile = calculate_node_risk(
                address=node.address,
                node_type=node.node_type,
                incoming_transfers=in_edges,
                outgoing_transfers=out_edges,
                is_vasp=bool(node.vasp_name),
                chain=chain_label
            )

            node.risk_score = risk_profile["risk_score"]
            node.risk_tier = risk_profile["risk_tier"]
            node.is_peeling = risk_profile["is_peeling"]
            node.is_mixer = risk_profile["is_mixer"]
            node.flags = risk_profile["flags"]
            node.explanation = risk_profile["explanation"]
            node.feature_vector = risk_profile.get("feature_vector")
            node.typology = risk_profile.get("typology")

            if node.risk_score > max_ml_score:
                max_ml_score = node.risk_score

            if risk_profile.get("typology") and not dominant_typology:
                dominant_typology = risk_profile["typology"]

            if risk_profile["is_mixer"]:
                node.node_type = "MIXER"
                node.label = f"Mixer Protocol ({risk_profile['mixer_details']['name']})"

        # Construct and calculate NetworkX graph centrality & topology metrics (ERR-28, P2 Item 6)
        G = build_nx_graph([e.model_dump() for e in edges_list])
        G_undir = G.to_undirected(as_view=True)
        mixer_nodes = [n.address for n in nodes_map.values() if n.is_mixer or n.node_type == "MIXER"]
        vasp_nodes = [n.address for n in nodes_map.values() if n.node_type == "VASP_HOT" or n.vasp_name]

        for node_id, node in nodes_map.items():
            if node.feature_vector and len(node.feature_vector) >= 8:
                # Dim 6: mixer proximity computed from real shortest path to identified mixer
                if node.is_mixer or node.node_type == "MIXER":
                    node.feature_vector[6] = 1.0
                elif mixer_nodes and G.has_node(node.address):
                    min_mix = None
                    for m in mixer_nodes:
                        if G.has_node(m) and nx.has_path(G, node.address, m):
                            d = nx.shortest_path_length(G, node.address, m)
                            if min_mix is None or d < min_mix:
                                min_mix = d
                        elif G_undir.has_node(m) and nx.has_path(G_undir, node.address, m):
                            d = nx.shortest_path_length(G_undir, node.address, m) + 1
                            if min_mix is None or d < min_mix:
                                min_mix = d
                    node.feature_vector[6] = round(1.0 / (min_mix + 1), 3) if min_mix is not None else 0.0
                else:
                    node.feature_vector[6] = 0.0

                # Dim 7: exchange custody computed from real graph distance to VASP hot wallet
                if node.node_type == "VASP_HOT":
                    node.feature_vector[7] = 1.0
                elif node.node_type == "VASP_DEPOSIT":
                    node.feature_vector[7] = 0.8
                elif vasp_nodes and G.has_node(node.address):
                    min_vasp = None
                    for v in vasp_nodes:
                        if G.has_node(v) and nx.has_path(G, node.address, v):
                            d = nx.shortest_path_length(G, node.address, v)
                            if min_vasp is None or d < min_vasp:
                                min_vasp = d
                        elif G_undir.has_node(v) and nx.has_path(G_undir, node.address, v):
                            d = nx.shortest_path_length(G_undir, node.address, v) + 1
                            if min_vasp is None or d < min_vasp:
                                min_vasp = d
                    node.feature_vector[7] = round(1.0 / (min_vasp + 1), 3) if min_vasp is not None else 0.0
                else:
                    node.feature_vector[7] = 0.0

        # Generate deterministic canonical SHA-256 evidence digest over all graph nodes & edges (ERR-11)
        evidence_sha256 = compute_canonical_evidence_digest({
            "seed_address": req.seed_address,
            "chain": chain_label,
            "nodes": list(nodes_map.values()),
            "edges": edges_list
        })

        exec_time = round((time.time() - start_time) * 1000, 2)

        return TraceResponse(
            trace_id=trace_id,
            seed_address=req.seed_address,
            chain=chain_label,
            execution_time_ms=exec_time,
            destination_found=found_target_vasp is not None,
            target_vasp=found_target_vasp,
            nodes=list(nodes_map.values()),
            edges=edges_list,
            evidence_sha256=evidence_sha256,
            syndicate_typology=dominant_typology,
            ml_anomaly_score=round(max_ml_score, 2),
            is_synthetic=is_synthetic
        )
