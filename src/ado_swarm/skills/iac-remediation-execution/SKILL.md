---
name: iac-remediation-execution
description: Use this skill when remediating an infrastructure-as-code misconfiguration (category=iac, e.g. Terraform/CloudFormation/K8s) inside an approved, sandboxed change boundary.
allowed-tools: resolve_repository verify_file_location propose_remediation_strategy apply_remediation_change graphiti_search
metadata:
  pack: remediation
  maturity: base
---
# iac-remediation-execution

## Objective

Correct a `normalized_finding.category == "iac"` misconfiguration (public bucket, open
security group, missing encryption, over-broad IAM, disabled logging) by editing the
declarative resource block to a secure-by-default setting — a config edit, never app code.

## When to use

The finding is an IaC/Terraform/CloudFormation/Kubernetes/Helm misconfiguration whose
`file_path` points at the declaration, with a `remediation_plan` for the config change.

## Inputs

- `normalized_finding`: `cwe`, `file_path` (`.tf`, `.yaml`, `.json`, Helm template), `title`.
- `remediation_plan`: `strategy`, `change_boundary`, `steps`.
- Sandbox working copy root + `repository_evidence.repository`.

## Procedure

1. Confirm approval (`requires_human_approval`) before any write; abort if unapproved.
2. `verify_file_location` on the IaC file; ensure it is in `change_boundary`.
3. Identify the exact attribute to harden (e.g. `acl = "private"`, enable `encryption`,
   restrict CIDR off `0.0.0.0/0`, `enable_logging = true`, scope IAM action/resource).
4. `graphiti_search` for the org's accepted secure baseline for this resource type.
5. Apply via `apply_remediation_change` with a precise `find`/`replace` on the single attribute;
   keep variable interpolation and module wiring intact.
6. Record the diff in `execution`.

## Decision criteria

- Choose the least-privilege / encrypted / private default that still meets the resource's purpose.
- Do not widen access to "make it work"; if hardening breaks a required path, escalate.
- Prefer module/variable defaults over hardcoding when a shared module is in use.

## Checklist

- [ ] Only the misconfigured attribute(s) changed; plan/state files untouched.
- [ ] No secrets introduced into the manifest.
- [ ] HCL/YAML remains well-formed.

## Output expectations

`ExecutionResult` with `applied=true`, `changed_files` limited to the IaC file(s).

## Safety

WRITE tool `apply_remediation_change` is approval-gated and sandbox-bounded; out-of-boundary
paths are refused. Never edit live infra, state, or credentials — config files only.

## Escalation

Change risks an outage, needs a coordinated infra rollout, or touches IAM trust policy → leave
unapplied and escalate to `needs_human`.
