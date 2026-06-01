from __future__ import annotations

import pytest
from pydantic import ValidationError

from ado_swarm.config import Settings

TEST_CREDENTIAL = "token-for-tests"


def test_stub_provider_requires_no_external_credentials() -> None:
    settings = Settings(source_provider="stub")

    assert settings.source_provider == "stub"


def test_github_provider_requires_token_and_owner() -> None:
    with pytest.raises(ValidationError, match="GITHUB_TOKEN and GITHUB_OWNER"):
        Settings(source_provider="github", github_token=TEST_CREDENTIAL)


def test_github_provider_accepts_required_credentials() -> None:
    settings = Settings(source_provider="github", github_token=TEST_CREDENTIAL, github_owner="octo")

    assert settings.source_provider == "github"


def test_azure_devops_provider_requires_all_credentials() -> None:
    with pytest.raises(ValidationError, match="ADO_ORG_URL, ADO_PROJECT, and ADO_PAT"):
        Settings(source_provider="azure_devops", ado_org_url="https://dev.azure.com/contoso")


def test_azure_devops_provider_accepts_required_credentials() -> None:
    settings = Settings(
        source_provider="azure_devops",
        ado_org_url="https://dev.azure.com/contoso",
        ado_project="project",
        ado_pat="pat",
    )

    assert settings.source_provider == "azure_devops"
