"""Assemble and run the Azure MCP server.

``build_server`` takes any subset of backends and registers their tools - this is what the
tests use, injecting in-memory fakes. ``build_azure_server`` builds the real Azure backends
from configuration and credentials. ``main`` is the stdio entry point an MCP client launches.
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .backends import (
    BlobBackend,
    ResourceBackend,
    SecretsBackend,
    ServiceBusBackend,
)
from .config import ToolkitConfig
from .tools import (
    register_blob_tools,
    register_resource_tools,
    register_secret_tools,
    register_service_bus_tools,
)

logger = logging.getLogger(__name__)

SERVER_NAME = "azure-toolkit"
SERVER_INSTRUCTIONS = (
    "Tools for inspecting Azure resources: Blob Storage, Key Vault, Service Bus, and "
    "resource groups. Operations are read-mostly and safe to call."
)


def build_server(
    *,
    blob: BlobBackend | None = None,
    secrets: SecretsBackend | None = None,
    service_bus: ServiceBusBackend | None = None,
    resources: ResourceBackend | None = None,
) -> FastMCP:
    """Build a FastMCP server with tools for whichever backends are provided."""
    mcp: FastMCP = FastMCP(name=SERVER_NAME, instructions=SERVER_INSTRUCTIONS)

    if blob is not None:
        register_blob_tools(mcp, blob)
    if secrets is not None:
        register_secret_tools(mcp, secrets)
    if service_bus is not None:
        register_service_bus_tools(mcp, service_bus)
    if resources is not None:
        register_resource_tools(mcp, resources)

    return mcp


def build_azure_server(  # pragma: no cover - needs live Azure
    config: ToolkitConfig | None = None,
) -> FastMCP:
    """Build a server backed by real Azure services, using DefaultAzureCredential.

    Only the services configured in ``config`` are registered. Requires the relevant Azure
    SDK extras to be installed.
    """
    config = config or ToolkitConfig.from_env()
    from azure.identity import DefaultAzureCredential

    from .backends import (
        AzureBlobBackend,
        AzureResourceBackend,
        AzureSecretsBackend,
        AzureServiceBusBackend,
    )

    credential = DefaultAzureCredential()

    blob = (
        AzureBlobBackend(config.storage_account_url, credential)
        if config.storage_account_url
        else None
    )
    secrets = (
        AzureSecretsBackend(config.key_vault_url, credential) if config.key_vault_url else None
    )
    service_bus = (
        AzureServiceBusBackend(config.service_bus_namespace, credential)
        if config.service_bus_namespace
        else None
    )
    resources = (
        AzureResourceBackend(config.subscription_id, credential)
        if config.subscription_id
        else None
    )

    logger.info("Starting Azure MCP server for services: %s", config.enabled_services())
    return build_server(
        blob=blob, secrets=secrets, service_bus=service_bus, resources=resources
    )


def main() -> None:  # pragma: no cover - process entry point
    """Console-script entry point: build from env and serve over stdio."""
    logging.basicConfig(level=logging.INFO)
    server = build_azure_server()
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
