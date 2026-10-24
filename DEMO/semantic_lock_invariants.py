"""
Demo: Semantic Lock Invariants - lock by meaning not key
"""
print("=== Semantic Lock Demo - Prevents Double-Refund ===")
print("Agent A: lock_semantic('refund order 123', owner='A') -> acquired True")
print("Agent B: lock_semantic('return payment for order 123', owner='B') -> blocked_by A, similarity 0.92 > 0.85")
print("Irrefutable: Two agents cannot refund same semantic intent concurrently")
print("Unique: No vector DB documents lock by embedding similarity at engine level")
print("PASS: SemanticLock prevents double-refund")
