# Storage Footprint vs. Vector Payload Compression

1. **Vector Payload Compression (96.8% payload only):**
   Qdrant BQ, 【entity-Azure¦canonical_name=Azure】 BQ compress individual vector payload 3072 bytes -> 96 bytes = 96.875%. This is raw vector arrays only.

2. **Total Engine Footprint (60-64% measured):**
   EEHIMDB measured total includes entire transactional file: vectors 3MB + WAL hash-chain 0.5MB + MVCC 10 versions/key 2MB + HNSW graph 1MB + TagIndex 0.3MB = 6.8MB raw -> 2.4MB compressed = 64.7% saving.
   Method: File size before/after QuantizerV2, not isolated vector bytes.

Rule: Never claim 96-98% as total. 96.8% is payload only, 60-64% is total with WAL+MVCC+HNSW.
