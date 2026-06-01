from __future__ import annotations

import pytest

from ado_swarm.sandbox.provider import (
    ALLOWED_EXECUTABLES,
    LocalSandboxProvider,
    SandboxCommandError,
)
from ado_swarm.tools.catalog import CATALOG
from ado_swarm.tools.catalog.verification import run_validation_command_impl


def test_run_validation_command_registered() -> None:
    assert "run_validation_command" in CATALOG


def test_passing_command_reports_ok(tmp_path) -> None:
    provider = LocalSandboxProvider(base_dir=tmp_path)
    session = provider.create("verification")
    result = provider.run_command(session, ["python", "-c", "print('ok')"], timeout_seconds=30)
    assert result.ok is True
    assert result.exit_code == 0
    assert "ok" in result.stdout


def test_failing_command_reports_not_ok(tmp_path) -> None:
    provider = LocalSandboxProvider(base_dir=tmp_path)
    session = provider.create("verification")
    result = provider.run_command(
        session, ["python", "-c", "import sys; sys.exit(3)"], timeout_seconds=30
    )
    assert result.ok is False
    assert result.exit_code == 3


def test_non_allowlisted_executable_is_rejected(tmp_path) -> None:
    provider = LocalSandboxProvider(base_dir=tmp_path)
    session = provider.create("verification")
    assert "rm" not in ALLOWED_EXECUTABLES
    with pytest.raises(SandboxCommandError):
        provider.run_command(session, ["rm", "-rf", "/"], timeout_seconds=5)


def test_timeout_is_reported(tmp_path) -> None:
    provider = LocalSandboxProvider(base_dir=tmp_path)
    session = provider.create("verification")
    result = provider.run_command(
        session, ["python", "-c", "import time; time.sleep(5)"], timeout_seconds=1
    )
    assert result.timed_out is True
    assert result.ok is False


def test_tool_impl_rejects_non_allowlisted() -> None:
    out = run_validation_command_impl(["rm", "-rf", "/"])
    assert out["ok"] is False
    assert out["rejected"] is True


def test_tool_impl_runs_allowlisted_pass() -> None:
    out = run_validation_command_impl(["python", "-c", "print('hi')"], timeout_seconds=30)
    assert out["rejected"] is False
    assert out["ok"] is True
    assert out["exit_code"] == 0
