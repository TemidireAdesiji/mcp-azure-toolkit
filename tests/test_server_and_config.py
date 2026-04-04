"""Tests for server assembly and configuration."""
import pytest
from helpers import tool_names

from mcp_azure_toolkit.backends import (
    InMemoryBlobBackend,
    InMemoryResourceBackend,
    InMemorySecretsBackend,
    InMemoryServiceBusBackend,
)
from mcp_azure_toolkit.config import (
    ENV_KEY_VAULT_URL,
    ENV_STORAGE_ACCOUNT_URL,
    ENV_SUBSCRIPTION_ID,
    ToolkitConfig,
)
from mcp_azure_toolkit.server import build_server


async def test_all_backends_registers_all_tools() -> None:
    server = build_server(
        blob=InMemoryBlobBackend(),
        secrets=InMemorySecretsBackend(),
        service_bus=InMemoryServiceBusBackend(),
        resources=InMemoryResourceBackend(),
    )
    names = await tool_names(server)
    assert len(names) == 9  # 3 blob + 2 secret + 2 service bus + 2 resource


async def test_no_backends_registers_no_tools() -> None:
    server = build_server()
    assert await tool_names(server) == set()


async def test_partial_registration() -> None:
    server = build_server(blob=InMemoryBlobBackend(), resources=InMemoryResourceBackend())
    names = await tool_names(server)
    assert any(n.startswith("blob_") for n in names)
    assert any(n.startswith("resource_") for n in names)
    assert not any(n.startswith("keyvault_") for n in names)
    assert not any(n.startswith("servicebus_") for n in names)


# Config


def test_config_from_env_reads_set_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_STORAGE_ACCOUNT_URL, "https://acct.blob.core.windows.net")
    monkeypatch.setenv(ENV_KEY_VAULT_URL, "https://v.vault.azure.net")
    monkeypatch.delenv(ENV_SUBSCRIPTION_ID, raising=False)

    config = ToolkitConfig.from_env()
    assert config.storage_account_url == "https://acct.blob.core.windows.net"
    assert config.key_vault_url == "https://v.vault.azure.net"
    assert config.subscription_id is None


def test_enabled_services_reflects_config() -> None:
    config = ToolkitConfig(
        storage_account_url="https://a.blob.core.windows.net",
        subscription_id="sub-123",
    )
    assert config.enabled_services() == ["blob", "resources"]


def test_enabled_services_empty_when_unconfigured() -> None:
    assert ToolkitConfig().enabled_services() == []


def test_all_services_enabled() -> None:
    config = ToolkitConfig(
        storage_account_url="u",
        key_vault_url="u",
        service_bus_namespace="u",
        subscription_id="u",
    )
    assert config.enabled_services() == ["blob", "keyvault", "servicebus", "resources"]
