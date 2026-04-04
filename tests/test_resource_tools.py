"""Tests for the resource group tools."""
import pytest
from helpers import call, tool_names

from mcp_azure_toolkit.backends import InMemoryResourceBackend
from mcp_azure_toolkit.server import build_server

GROUPS = {
    "rg-prod": [
        {"name": "prod-storage", "type": "Microsoft.Storage/storageAccounts"},
        {"name": "prod-vault", "type": "Microsoft.KeyVault/vaults"},
    ],
    "rg-dev": [{"name": "dev-storage", "type": "Microsoft.Storage/storageAccounts"}],
}


def _server() -> object:
    return build_server(resources=InMemoryResourceBackend(GROUPS))


async def test_only_resource_tools_registered() -> None:
    assert await tool_names(_server()) == {
        "resource_list_groups",
        "resource_list_resources",
    }


async def test_list_groups() -> None:
    assert await call(_server(), "resource_list_groups") == ["rg-dev", "rg-prod"]


async def test_list_resources() -> None:
    result = await call(_server(), "resource_list_resources", {"resource_group": "rg-prod"})
    assert len(result) == 2
    assert result[0]["name"] == "prod-storage"
    assert result[0]["type"] == "Microsoft.Storage/storageAccounts"


async def test_list_resources_unknown_group_raises() -> None:
    with pytest.raises(Exception):  # noqa: B017
        await call(_server(), "resource_list_resources", {"resource_group": "ghost"})
