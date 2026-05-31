# ADR-0005: Structured tool policy, approvals, and budget guardrails

**Status:** Accepted

Natural-language instructions are insufficient for governing agent tool use. `ado-swarm` now models tool access with structured context: run, task, agent, phase, risk level, approval state, provider, repository, and dry-run status. Write and destructive tools are denied unless policy and approval state allow execution.

Budget guardrails are represented separately from policy so the runtime can track loops, tool calls, model calls, elapsed time, token usage, estimated cost, and accepted outcomes. This prepares the system for pass^k evals, cost-per-accepted-outcome metrics, and safer write-enabled remediation.
