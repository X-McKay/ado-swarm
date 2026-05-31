# ADR-0001: Temporal as control plane

Temporal owns mission lifecycle, retries, task state, and approval gates. LLM calls, provider API calls, database work, and graph operations remain in activities or adapters.
