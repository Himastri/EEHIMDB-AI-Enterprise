import time, threading
from typing import Dict, List, Set
from collections import defaultdict

class StalePropagation:
    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._items: Dict[str, dict] = {}
        self._lock = threading.RLock()
        self._invalidations = 0
    
    def register_dependency(self, item_id, source_record_id, built_at_tx):
        with self._lock:
            self._graph[source_record_id].add(item_id)
            if item_id not in self._items:
                self._items[item_id] = {"sources": set(), "built_at_tx": built_at_tx, "is_stale": False, "stale_reason": None, "created_at": time.time()}
            self._items[item_id]["sources"].add(source_record_id)
    
    def on_source_update(self, source_record_id, new_tx_id):
        with self._lock:
            affected = list(self._graph.get(source_record_id, set()))
            invalidated = []
            for item_id in affected:
                if item_id in self._items and not self._items[item_id]["is_stale"]:
                    self._items[item_id]["is_stale"] = True
                    self._items[item_id]["stale_reason"] = f"{source_record_id} v{self._items[item_id]['built_at_tx']} -> v{new_tx_id}"
                    invalidated.append(item_id)
                    self._invalidations += 1
            return invalidated
    
    def is_stale(self, item_id):
        with self._lock:
            return self._items.get(item_id, {}).get("is_stale", False)
    
    def should_use_cache(self, item_id):
        return not self.is_stale(item_id)
    
    def get_stats(self):
        with self._lock:
            total = len(self._items)
            stale = sum(1 for v in self._items.values() if v["is_stale"])
            return {"total_items": total, "stale_items": stale, "fresh_items": total - stale, "total_invalidations": self._invalidations, "sources_tracked": len(self._graph)}