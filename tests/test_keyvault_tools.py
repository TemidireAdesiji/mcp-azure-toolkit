"""Tests for the Key Vault tools."""
import pytest
from helpers import call, tool_names

from mcp_azure_toolkit.backends import InMemorySecretsBackend
from mcp_azure_toolkit.server import build_server

SECRETS = {"db-password": "s3cr3t", "api-key": "abc123"}


def _server() -> object:
    return build_server(secrets=InMemorySecretsBackend(SECRETS))


async def test_only_secret_tools_registered() -> None:
    names = await tool_names(_server())
    assert names == {"keyvault_get_secret", "keyvault_list_secrets"}


async def test_get_secret() -> None:
    result = await call(_server(), "keyvault_get_secret", {"name": "db-password"})
    assert result == "s3cr3t"


async def test_list_secrets_returns_names_only() -> None:
    result = await call(_server(), "keyvault_list_secrets")
    assert result == ["api-key", "db-password"]
    # Values must never appear in the listing
    assert "s3cr3t" not in result


async def test_get_missing_secret_raises() -> None:
    with pytest.raises(Exception):  # noqa: B017
        await call(_server(), "keyvault_get_secret", {"name": "nonexistent"})


async def test_backend_get_secret() -> None:
    backend = InMemorySecretsBackend(SECRETS)
    assert await backend.get_secret("api-key") == "abc123"
