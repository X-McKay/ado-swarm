from __future__ import annotations

from typing import cast

from strands.hooks import BeforeToolCallEvent

from ado_swarm.tools.catalog import CATALOG
from ado_swarm.tools.catalog.provider_write import (
    add_issue_comment_impl,
    add_pr_comment_impl,
    create_draft_pr_impl,
)
from ado_swarm.tools.policy import ApprovalState, ToolContext, ToolPolicy
from ado_swarm.tools.policy_hook import ToolPolicyHook

STUB_REPO = {
    "provider": "stub",
    "external_id": "repo-1",
    "owner_or_project": "acme",
    "name": "service",
    "default_branch": "main",
    "web_url": "https://example.invalid/acme/service",
}

WRITE_TOOLS = ["provider_create_draft_pr", "provider_add_issue_comment", "provider_add_pr_comment"]


def test_write_tools_registered() -> None:
    for name in WRITE_TOOLS:
        assert name in CATALOG


async def test_create_draft_pr_returns_draft() -> None:
    pr = await create_draft_pr_impl(STUB_REPO, "Fix CVE", "fix/cve", "main", "body")
    assert pr["is_draft"] is True
    assert pr["title"] == "Fix CVE"


async def test_issue_and_pr_comment_impls() -> None:
    issue = await add_issue_comment_impl("SEC-1", "looking into this")
    assert issue["ok"] is True
    pr = await add_pr_comment_impl(STUB_REPO, "PR-1", "validated")
    assert pr["ok"] is True


def _gate(approval: ApprovalState, tool: str) -> bool:
    """Return True if the write tool is allowed under the given approval state."""
    policy = ToolPolicy(WRITE_TOOLS, write_tools=WRITE_TOOLS)
    hook = ToolPolicyHook(policy, ToolContext(run_id="r1", approval_state=approval))

    class _E:
        def __init__(self, name: str) -> None:
            self.tool_use = {"name": name}
            self.cancel_tool = None

    event = _E(tool)
    hook.gate(cast(BeforeToolCallEvent, event))
    return event.cancel_tool is None


def test_write_tools_require_approval() -> None:
    # Unapproved → blocked (approval required); approved → allowed.
    assert _gate(ApprovalState.NOT_REQUIRED, "provider_create_draft_pr") is False
    assert _gate(ApprovalState.REQUIRED, "provider_create_draft_pr") is False
    assert _gate(ApprovalState.APPROVED, "provider_create_draft_pr") is True
