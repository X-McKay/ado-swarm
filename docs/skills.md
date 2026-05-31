# Runtime Skill Catalog

The base runtime now includes the full initial security-remediation skill catalog. Skills are organized by pack so agents can load phase-relevant procedures without a monolithic prompt.

| Pack | Purpose |
|---|---|
| `triage-readonly` | Normalize source issues and classify scanner findings. |
| `repository-investigation` | Resolve repositories and verify code evidence. |
| `adjudication` | Determine stale, duplicate, already-fixed, and false-positive outcomes. |
| `risk-impact` | Score security risk, change impact, and automation eligibility. |
| `planning` | Produce remediation strategies, fix plans, and safe change boundaries. |
| `remediation` | Define controlled execution procedures for dependency, code, and IaC fixes. |
| `validation-submission` | Review diffs, verify fixes, run tests, prepare PRs, and update tickets. |
| `analytics` | Mine campaigns, false-positive patterns, and skill performance. |

Richer agent behavior should activate these skills based on task phase and then record activated skills in the audit trail.
