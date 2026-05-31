# CI workflow (manual install)

`github-actions-ci.yml` is the project CI definition. It is kept here as a
template rather than under `.github/workflows/` because the automation account
that produced this branch lacks the GitHub `workflows` permission (pushes that
add or modify files under `.github/workflows/` are rejected).

To enable CI, a maintainer with write access should copy it into place:

```bash
mkdir -p .github/workflows
cp docs/ci/github-actions-ci.yml .github/workflows/ci.yml
git add .github/workflows/ci.yml && git commit -m "Add CI workflow" && git push
```

The `check` job mirrors `just check` (ruff format/lint, ty, unit tests, and
`eval-agents` on the deterministic `fake` profile). The `integration` job is a
manual (`workflow_dispatch`) placeholder for future Docker-based tests.
</content>
