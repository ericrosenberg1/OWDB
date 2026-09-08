"""
WrestleBot v3 pipeline.

Ordered stages:

    discovery   — produce candidate names from external sources
    fetch       — pull raw content for each candidate; persist as SourceFetch
    extract     — parse stored content into typed field structs
    reconcile   — merge fields across sources (placeholder in v3.0; single-source)
    persist     — write to entity table + FieldProvenance, atomically

Each stage is an idempotent operation over the persistence layer. Re-running
a stage should produce the same DB state given the same inputs.
"""
