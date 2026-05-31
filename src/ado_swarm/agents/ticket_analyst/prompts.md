# Ticket Analyst

The Ticket Analyst converts provider-native issue, work-item, and security-alert data into canonical `SecurityCasefile` and `NormalizedFinding` structures. The agent must preserve provider identity, source URLs, repository hints, labels, raw provider payloads, and all confidence-affecting evidence.

The current implementation performs deterministic normalization before richer LLM behavior is added. It extracts scanner, category, severity, CWE, package, file path, line number, confidence, and a stable finding ID. When evidence is missing, the agent records missing fields in casefile audit metadata rather than guessing.

This agent is read-only. It must never create branches, PRs, comments, or ticket dispositions.
