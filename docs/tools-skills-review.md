# Agent Tools & Skills Review

**Date:** 2026-05-31
**Context:** All 9 agents are now model-driven (tools in a loop). This review maps what each agent can *actually do* (tools) vs. what its skills *tell it to do*, surfaces gaps, and recommends tools/skills worth adding or exploring.

## Implemented since this review

The wiring table below reflects the original snapshot; subsequently delivered on `feature/claude-cleanup`:
- **Knowledge tools** `graphiti_search` / `graphiti_add_episode` (`tools/catalog/knowledge.py`, via `knowledge/providers.py`) — recall wired into `security_reviewer` for duplicate/stale evidence (activates duplicate-finding-adjudication, campaign-discovery, false-positive-pattern-mining).
- **Provider read tools** `provider_get_issue` / `provider_search_issues` / `provider_get_repo_metadata` (`tools/catalog/provider.py`).
- **Verification governor** `run_validation_command` (`tools/catalog/verification.py`) — runs allowlisted tests/lint/build in a sandbox (`sandbox/provider.py::run_command`, `shell=False`, timeout, output caps); wired into `test_engineer` so checks are *run*, not just proposed. A non-zero exit is a hard failure.
- **Bounded adjudication swarm** for `security_reviewer` (ADR-0009), opt-in + eval-gated.
- All 26 `SKILL.md` bodies replaced with real, distinct guidance referencing only real catalog tools.

Catalog is now 16 tools. Still open: repository-investigation tools (`repo_grep`, `git_log_path`), real provider write tools for the draft-PR path, and a real Graphiti/Neo4j backend behind `KnowledgeStore`.

## 1. Current wiring

| Agent | Section | Tools (capabilities) | Skills (expertise) |
|---|---|---|---|
| `ticket_analyst` | normalized_finding | `normalize_finding` | security-ticket-normalization, finding-type-classification, scanner-finding-fingerprinting |
| `repo_analyst` | repository_evidence | `resolve_repository`, `verify_file_location` | repository-resolution, code-location-verification, git-history-investigation |
| `security_reviewer` | adjudication | `adjudication_signals` | stale-finding-adjudication, duplicate-finding-adjudication, false-positive-evidence-review |
| `risk_auditor` | risk | `score_severity` | security-risk-scoring, change-impact-classification, automation-eligibility-assessment |
| `solutions_architect` | remediation_plan | `propose_remediation_strategy` | fix-plan-generation, remediation-strategy-selection, safe-change-boundary-definition |
| `software_engineer` | execution | `apply_remediation_change` (write) | dependency/localized-code/iac-remediation-execution |
| `test_engineer` | validation | `propose_validation_checks` | test-and-build-validation, security-fix-verification, pull-request-preparation |
| `qa_lead` | readiness | `assess_readiness` | security-ticket-normalization |
| `data_analyst` | (CampaignReport) | `summarize_findings` | campaign-discovery, false-positive-pattern-mining, skill-performance-evaluation |

**Catalog:** 10 tools, all used. **Skills:** 26 total, 24 wired, **2 orphan**: `remediation-diff-review`, `ticket-disposition-update`.

## 2. The headline gap: thin tool loops + skills with no backing tool

Two structural issues stand out:

1. **Most agents have exactly one tool.** A genuine "tools in a loop" agent gets its value from *choosing among* tools and *iterating*. With a single deterministic baseline tool, the loop is degenerate — the model calls the one tool and stops. Each agent should have 2–4 complementary tools so reasoning matters.

2. **Several skills describe capabilities the agent cannot perform** (the skill is real expertise, but there's no tool to act on it). These are the highest-value gaps because the skill already exists — it just needs a backing tool:

| Agent | Skill that implies a capability | Missing backing tool |
|---|---|---|
| `repo_analyst` | **git-history-investigation** | no git tool — can't inspect history/blame |
| `security_reviewer` | **duplicate-finding-adjudication** | no duplicate-lookup (knowledge) tool — can't find duplicates |
| `security_reviewer` | stale-finding-adjudication | only confidence/file-exists; no git "last-modified / deleted" signal |
| `test_engineer` | **test-and-build-validation**, security-fix-verification | no test/scanner-run tool — can only *propose* checks, not run them |
| `software_engineer` | dependency/code/iac-remediation-execution | only a sandbox placeholder; no real dependency/code/IaC edit tools |
| `data_analyst` | **campaign-discovery**, false-positive-pattern-mining | only in-memory counts; no knowledge-store query over real history |
| `qa_lead` | (skill is *security-ticket-normalization* — mismatched) | no readiness/coordination skill exists |

## 3. Easy wins — wrap capabilities that already exist

These need almost no new infrastructure (wrap existing ports), and immediately thicken the loops:

### 3a. Provider tools (wrap `SourceProvider` methods)
The provider port already exposes `get_issue`, `search_issues`, `get_repository`, `list_branches`, `get_file`, plus write methods. Add read tools:
- `provider_get_issue(external_id)` → ticket_analyst, qa_lead
- `provider_search_issues(query)` → data_analyst (find related/duplicate tickets), security_reviewer
- `provider_get_repository(owner, name)` / `provider_list_branches(repo)` → repo_analyst
- (write, approval-gated, later) `provider_add_issue_comment`, `provider_create_draft_pr`, `provider_add_pr_comment` → test_engineer/qa_lead (this also backs the orphan **ticket-disposition-update** skill)

### 3b. Knowledge tools (wrap `KnowledgeStore`)
`KnowledgeStore` already has `search` and `add_episode` but **no agent can call it**. Wrapping it makes two orphaned-ish skills real and gives the knowledge store a purpose:
- `knowledge_search(query)` → security_reviewer (**duplicate** detection), data_analyst (**campaign** mining)
- `knowledge_record_outcome(casefile)` → data_analyst / a closing step (the learning loop)

This is the single highest-leverage addition: it activates duplicate-finding-adjudication, campaign-discovery, and false-positive-pattern-mining, and makes `/health` honest once Graphiti is real.

## 4. New tools worth building (need real implementations)

Mapped to the plan's tooling model (§11) and the skills that want them:

| Category | Tools | Backs skill(s) | For agents |
|---|---|---|---|
| **Git (read)** | `git_log_path`, `git_blame`, `git_diff_readonly`, `git_show_deleted` | git-history-investigation, stale-finding-adjudication | repo_analyst, security_reviewer |
| **Repo search** | `repo_grep`, `repo_find_file`, `repo_locate_symbol`, `repo_parse_manifest` | code-location-verification | repo_analyst, solutions_architect |
| **Scanner** | `scanner_parse_existing_result`, `scanner_run_targeted` (sandbox) | security-fix-verification, scanner-finding-fingerprinting | security_reviewer, test_engineer |
| **Dependency** | `dependency_inspect_manifest`, `dependency_plan_upgrade` | dependency-remediation-execution | solutions_architect, software_engineer |
| **Test/build** | `test_discover_commands`, `test_run_targeted` (sandbox) | test-and-build-validation | test_engineer, software_engineer |
| **Diff** | `compute_diff`, `review_diff` | **remediation-diff-review** (orphan) | test_engineer, software_engineer |
| **Code edit (write)** | `apply_code_patch`, `apply_dependency_bump`, `apply_iac_change` (sandbox, approval) | localized-code/iac-remediation-execution | software_engineer |

The write/sandbox tools (scanner-run, test-run, code-edit) should run in the `LocalSandboxProvider` with timeouts/output caps and be policy-gated behind approval — extending the pattern `apply_remediation_change` already establishes.

## 5. Orphan skills — decide per skill

- **`remediation-diff-review`**: add `compute_diff`/`review_diff` tools and wire to `test_engineer` (review the proposed change before readiness) or `software_engineer`.
- **`ticket-disposition-update`**: add a write tool `provider_update_disposition` (comment + close/label) and wire to `qa_lead` or `test_engineer`, approval-gated. This closes the loop back to the source provider.

## 6. New skills worth exploring

- **`phase-readiness-assessment`** for `qa_lead` (its current `security-ticket-normalization` skill is a mismatch — it doesn't normalize tickets).
- **`knowledge-graph-querying`** — how to phrase duplicate/campaign queries against the knowledge store (pairs with the new knowledge tools).
- **`sandbox-execution-safety`** — guardrails for running scanners/tests/edits in the sandbox (pairs with the new sandbox tools), reinforcing the approval posture.
- Split/clarify the three remediation-execution skills so each maps to its concrete edit tool (dependency vs code vs IaC).

## 7. Recommended sequence (highest value first)

1. **Knowledge tools** (`knowledge_search`, `knowledge_record_outcome`) — wrap the existing store; activates 3 skills; makes duplicate/campaign reasoning real. *Cheap, high impact.*
2. **Provider read tools** (`provider_get_issue`, `provider_search_issues`, `provider_get_repository`, `provider_list_branches`) — wrap existing port; thickens ticket_analyst/repo_analyst/data_analyst loops. *Cheap.*
3. **Git read + repo search tools** — real implementations against a cloned sandbox; backs git-history/code-location skills (repo_analyst, security_reviewer). *Medium.*
4. **Diff + ticket-disposition tools** — resolves the two orphan skills end-to-end. *Medium.*
5. **Sandbox scanner/test/edit tools** (write, approval-gated) — makes test_engineer/software_engineer actually validate and apply. *Larger; gated behind the approval+verification loop.*
6. **New skills** (`phase-readiness-assessment`, `knowledge-graph-querying`, `sandbox-execution-safety`) alongside their tools.

## 8. Guardrail reminder

Every new tool follows the established pattern: a typed `@tool` in `tools/catalog/` with an isolated unit test; reads are default-allow, **writes go in `write_tool_names` and are approval-gated** via `ToolPolicyHook`. Skills remain documentation/expertise — enforcement stays in the policy layer.
</content>
