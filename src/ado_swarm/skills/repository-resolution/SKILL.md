---
name: repository-resolution
description: Use this skill when determining the concrete repository, provider, and ref a finding belongs to.
allowed-tools: resolve_repository provider_get_repo_metadata provider_get_issue graphiti_search
metadata:
  pack: repository-investigation
  maturity: base
---
# repository-resolution

## Objective

Pin a finding to a concrete repository and an investigable ref. Before any file or history
work can happen, you must know *which* repo (provider + slug), what its default branch is, and
which ref the finding's evidence should be checked against. This is the first step of repository
investigation and the foundation for `code-location-verification` and `git-history-investigation`.

## When to use

- A `NormalizedFinding` or `SourceIssue` references a repo by name, URL, or implication and you
  need a canonical, resolved repository + ref to work from.
- `RepositoryEvidence.repository` or `.ref` is empty.

## Inputs

- `SourceIssue.repository` / `SourceIssue.url` — the primary repo signal.
- `NormalizedFinding.file_path` — confirms the repo by matching expected layout.
- Provider context (provider id from `SourceIssue.provider`) — Azure DevOps vs GitHub.

## Procedure

1. Call `resolve_repository` with the repo hint (slug, URL, or work-item context) to obtain the
   canonical repository identity.
2. Call `provider_get_repo_metadata` to fetch the default branch, available refs/tags, and clone
   coordinates. Treat the default branch as the ref unless the finding cites a specific scan ref.
3. If the repo hint is ambiguous (org has many similarly named repos), use `provider_get_issue`
   to recover the exact repository the ticket was filed against.
4. Choose the `ref`: prefer an explicit scan ref/commit from the finding; otherwise the default
   branch. Record which one you chose and why in `evidence`.
5. Optionally `graphiti_search` for prior investigations of this repo to reuse known structure.

## Decision criteria

- Treat repository operations as READ-ONLY: read metadata and refs, never create branches or push.
- Prefer the exact commit/scan ref over a moving branch when the finding cites one — it makes
  later verification reproducible.
- If metadata shows the repo archived/renamed/redirected, follow the redirect and note it.

## Output expectations

Populates `RepositoryEvidence.repository` and `RepositoryEvidence.ref` (repo_analyst section),
and seeds `RepositoryEvidence.evidence` with how the repo and ref were resolved.

## Escalation

If the repository cannot be resolved (dead URL, no access, multiple equally plausible repos) or
the finding spans repos, do not guess — leave `RepositoryEvidence` minimal and mark `needs_human`.
