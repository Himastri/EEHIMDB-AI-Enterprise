import time, hashlib, threading, json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class EvidenceVersion:
    record_id: str
    tx_id: int
    content_hash: str
    retrieved_at: float

@dataclass
class DecisionReceipt:
    decision_id: str
    agent_id: str
    tenant_id: str
    query: str
    read_as_of_tx: int
    evidence: List[EvidenceVersion] = field(default_factory=list)
    steps: List[dict] = field(default_factory=list)
    committed: bool = False
    stale_detected: Optional[dict] = None
    receipt_hash: str = ""

class StaleContextError(Exception):
    def __init__(self, record_id, old_tx, current_tx):
        self.record_id = record_id
        self.old_tx = old_tx
        self.current_tx = current_tx
        super().__init__(f"Stale {record_id} v{old_tx}->{current_tx}")

class ContextReceipt:
    def __init__(self, mvcc_store=None, wal_log=None):
        self._mvcc = mvcc_store if mvcc_store else {}
        self._mvcc_lock = threading.Lock()
        self._wal = wal_log if wal_log else []
        self._wal_lock = threading.Lock()
        self._receipts: Dict[str, DecisionReceipt] = {}
        self._tx_counter = 100
        self._tx_lock = threading.Lock()
    
    def _next_tx(self):
        with self._tx_lock:
            self._tx_counter += 1
            return self._tx_counter
    
    def _hash_content(self, data):
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        return hashlib.sha256(str(data).encode()).hexdigest()[:16]
    
    def begin_decision(self, agent_id, tenant_id, query):
        tx = self._next_tx()
        decision_id = f"dec_{tx}_{hashlib.sha256(f'{agent_id}{query}{time.time()}'.encode()).hexdigest()[:8]}"
        receipt = DecisionReceipt(decision_id=decision_id, agent_id=agent_id, tenant_id=tenant_id, query=query, read_as_of_tx=tx)
        with self._wal_lock:
            prev = self._wal[-1]["hash"] if self._wal else "0"*16
            entry = {"type": "begin_decision", "decision_id": decision_id, "agent_id": agent_id, "tenant_id": tenant_id, "query": query, "tx_id": tx, "prev_hash": prev}
            entry["hash"] = hashlib.sha256(f"{prev}{json.dumps(entry, sort_keys=True)}".encode()).hexdigest()[:16]
            self._wal.append(entry)
            receipt.steps.append(entry)
        self._receipts[decision_id] = receipt
        return receipt
    
    def add_evidence(self, decision_id, record_id, data):
        receipt = self._receipts[decision_id]
        with self._mvcc_lock:
            if record_id not in self._mvcc:
                self._mvcc[record_id] = self._next_tx()
            current_tx = self._mvcc[record_id]
        ev = EvidenceVersion(record_id=record_id, tx_id=current_tx, content_hash=self._hash_content(data), retrieved_at=time.time())
        receipt.evidence.append(ev)
        with self._wal_lock:
            prev = self._wal[-1]["hash"] if self._wal else "0"*16
            entry = {"type": "evidence", "decision_id": decision_id, "record_id": record_id, "tx_id": current_tx, "prev_hash": prev}
            entry["hash"] = hashlib.sha256(f"{prev}{json.dumps(entry, sort_keys=True)}".encode()).hexdigest()[:16]
            self._wal.append(entry)
            receipt.steps.append(entry)
        return ev
    
    def simulate_external_update(self, record_id):
        with self._mvcc_lock:
            self._mvcc[record_id] = self._next_tx()
            return self._mvcc[record_id]
    
    def get_current_tx(self, record_id):
        with self._mvcc_lock:
            return self._mvcc.get(record_id, 0)
    
    def commit_decision(self, decision_id):
        receipt = self._receipts[decision_id]
        for ev in receipt.evidence:
            current = self.get_current_tx(ev.record_id)
            if current != ev.tx_id:
                receipt.stale_detected = {"record_id": ev.record_id, "old_tx": ev.tx_id, "current_tx": current}
                with self._wal_lock:
                    prev = self._wal[-1]["hash"] if self._wal else "0"*16
                    entry = {"type": "stale_detected", "decision_id": decision_id, "record_id": ev.record_id, "old_tx": ev.tx_id, "current_tx": current, "prev_hash": prev}
                    entry["hash"] = hashlib.sha256(f"{prev}{json.dumps(entry, sort_keys=True)}".encode()).hexdigest()[:16]
                    self._wal.append(entry)
                    receipt.steps.append(entry)
                raise StaleContextError(ev.record_id, ev.tx_id, current)
        receipt.committed = True
        final_hash_input = f"{receipt.decision_id}{receipt.read_as_of_tx}{''.join([e.content_hash for e in receipt.evidence])}"
        receipt.receipt_hash = hashlib.sha256(final_hash_input.encode()).hexdigest()[:16]
        with self._wal_lock:
            prev = self._wal[-1]["hash"] if self._wal else "0"*16
            entry = {"type": "commit_decision", "decision_id": decision_id, "receipt_hash": receipt.receipt_hash, "evidence_count": len(receipt.evidence), "prev_hash": prev}
            entry["hash"] = hashlib.sha256(f"{prev}{json.dumps(entry, sort_keys=True)}".encode()).hexdigest()[:16]
            self._wal.append(entry)
            receipt.steps.append(entry)
        return receipt
    
    def verify_wal_chain(self):
        with self._wal_lock:
            prev = "0"*16
            for entry in self._wal:
                if entry["prev_hash"] != prev:
                    return False
                h = entry["hash"]
                entry_copy = {k: v for k, v in entry.items() if k != "hash"}
                recomputed = hashlib.sha256(f"{prev}{json.dumps(entry_copy, sort_keys=True)}".encode()).hexdigest()[:16]
                if recomputed != h:
                    return False
                prev = h
            return True