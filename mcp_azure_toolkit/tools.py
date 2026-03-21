"""Register Azure backend operations as MCP tools on a FastMCP server.

Each ``register_*_tools`` function takes a FastMCP server and a backend, and wires the
backend's methods up as MCP tools the model can call. Tools return plain JSON-serialisable
values (strings, lists, dicts) so any MCP client can consume them.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .backends import (
    BlobBackend,
    ResourceBackend,
    SecretsBackend,
    ServiceBusBackend,
)


def register_blob_tools(mcp: FastMCP, backend: BlobBackend) -> None:
    @mcp.tool(
        name="blob_list_containers",
        description="List the blob containers in the storage account.",
    )
    async def blob_list_containers() -> list[str]:
        return await backend.list_containers()

    @mcp.tool(
        name="blob_list_blobs",
        description="List the blobs in a given container.",
    )
    async def blob_list_blobs(container: str) -> list[str]:
        return await backend.list_blobs(container)

    @mcp.tool(
        name="blob_read",
        description="Read the text content of a blob in a container.",
    )
    async def blob_read(container: str, name: str) -> str:
        return await backend.read_blob(container, name)


def register_secret_tools(mcp: FastMCP, backend: SecretsBackend) -> None:
    @mcp.tool(
        name="keyvault_get_secret",
        description="Get the value of a secret from Key Vault by name.",
    )
    async def keyvault_get_secret(name: str) -> str:
        return await backend.get_secret(name)

    @mcp.tool(
        name="keyvault_list_secrets",
        description="List the names of the secrets in Key Vault (values not included).",
    )
    async def keyvault_list_secrets() -> list[str]:
        return await backend.list_secrets()


def register_service_bus_tools(mcp: FastMCP, backend: ServiceBusBackend) -> None:
    @mcp.tool(
        name="servicebus_send",
        description="Send a text message to a Service Bus queue.",
    )
    async def servicebus_send(queue: str, body: str) -> str:
        await backend.send_message(queue, body)
        return f"Message sent to queue '{queue}'."

    @mcp.tool(
        name="servicebus_peek",
        description="Peek (without consuming) up to max_count messages on a queue.",
    )
    async def servicebus_peek(queue: str, max_count: int = 10) -> list[str]:
        return await backend.peek_messages(queue, max_count)


def register_resource_tools(mcp: FastMCP, backend: ResourceBackend) -> None:
    @mcp.tool(
        name="resource_list_groups",
        description="List the resource groups in the subscription.",
    )
    async def resource_list_groups() -> list[str]:
        return await backend.list_resource_groups()

    @mcp.tool(
        name="resource_list_resources",
        description="List the resources (name and type) in a resource group.",
    )
    async def resource_list_resources(resource_group: str) -> list[dict[str, str]]:
        return await backend.list_resources(resource_group)
