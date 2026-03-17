"""Backends expose Azure services behind narrow async protocols.

Each protocol is the minimal surface the MCP tools need. There are two implementations:

- ``Azure*Backend`` - wraps the real Azure SDK (sync clients run in a worker thread so
  they do not block the event loop). Used in production.
- ``InMemory*Backend`` - a dependency-free fake used by the tests and for local demos.

Tools depend only on the protocols, so the same server runs against real Azure or against
fakes with no code change. Operations are deliberately read-mostly: blobs and secrets are
read-only, Service Bus exposes send + non-destructive peek. Destructive operations are
intentionally omitted so the server is safe to expose to an AI client by default.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential


# --------------------------------------------------------------------------- protocols


@runtime_checkable
class BlobBackend(Protocol):
    async def list_containers(self) -> list[str]: ...
    async def list_blobs(self, container: str) -> list[str]: ...
    async def read_blob(self, container: str, name: str) -> str: ...


@runtime_checkable
class SecretsBackend(Protocol):
    async def get_secret(self, name: str) -> str: ...
    async def list_secrets(self) -> list[str]: ...


@runtime_checkable
class ServiceBusBackend(Protocol):
    async def send_message(self, queue: str, body: str) -> None: ...
    async def peek_messages(self, queue: str, max_count: int) -> list[str]: ...


@runtime_checkable
class ResourceBackend(Protocol):
    async def list_resource_groups(self) -> list[str]: ...
    async def list_resources(self, resource_group: str) -> list[dict[str, str]]: ...


# --------------------------------------------------------------------------- in-memory fakes


class InMemoryBlobBackend:
    """In-memory blob store: ``{container: {blob_name: content}}``."""

    def __init__(self, data: dict[str, dict[str, str]] | None = None) -> None:
        self._data = data or {}

    async def list_containers(self) -> list[str]:
        return sorted(self._data)

    async def list_blobs(self, container: str) -> list[str]:
        if container not in self._data:
            raise KeyError(f"container {container!r} not found")
        return sorted(self._data[container])

    async def read_blob(self, container: str, name: str) -> str:
        try:
            return self._data[container][name]
        except KeyError as exc:
            raise KeyError(f"blob {container}/{name} not found") from exc


class InMemorySecretsBackend:
    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets = secrets or {}

    async def get_secret(self, name: str) -> str:
        try:
            return self._secrets[name]
        except KeyError as exc:
            raise KeyError(f"secret {name!r} not found") from exc

    async def list_secrets(self) -> list[str]:
        return sorted(self._secrets)


class InMemoryServiceBusBackend:
    """Records sent messages per queue and lets tests peek them non-destructively."""

    def __init__(self) -> None:
        self.queues: dict[str, list[str]] = {}

    async def send_message(self, queue: str, body: str) -> None:
        self.queues.setdefault(queue, []).append(body)

    async def peek_messages(self, queue: str, max_count: int) -> list[str]:
        return self.queues.get(queue, [])[:max_count]


class InMemoryResourceBackend:
    def __init__(self, groups: dict[str, list[dict[str, str]]] | None = None) -> None:
        self._groups = groups or {}

    async def list_resource_groups(self) -> list[str]:
        return sorted(self._groups)

    async def list_resources(self, resource_group: str) -> list[dict[str, str]]:
        if resource_group not in self._groups:
            raise KeyError(f"resource group {resource_group!r} not found")
        return self._groups[resource_group]


# --------------------------------------------------------------------------- real Azure backends
#
# These are exercised only against a live Azure subscription, so they are excluded from
# coverage. They wrap synchronous Azure SDK clients with asyncio.to_thread to avoid
# blocking the event loop.


class AzureBlobBackend:  # pragma: no cover - requires live Azure
    def __init__(self, account_url: str, credential: TokenCredential) -> None:
        from azure.storage.blob import BlobServiceClient

        self._client = BlobServiceClient(account_url, credential=credential)

    async def list_containers(self) -> list[str]:
        def _work() -> list[str]:
            return [str(c.name) for c in self._client.list_containers()]

        return await asyncio.to_thread(_work)

    async def list_blobs(self, container: str) -> list[str]:
        def _work() -> list[str]:
            client = self._client.get_container_client(container)
            return [str(b.name) for b in client.list_blobs()]

        return await asyncio.to_thread(_work)

    async def read_blob(self, container: str, name: str) -> str:
        def _work() -> str:
            blob = self._client.get_blob_client(container, name)
            return blob.download_blob().readall().decode("utf-8")

        return await asyncio.to_thread(_work)


class AzureSecretsBackend:  # pragma: no cover - requires live Azure
    def __init__(self, vault_url: str, credential: TokenCredential) -> None:
        from azure.keyvault.secrets import SecretClient

        self._client = SecretClient(vault_url=vault_url, credential=credential)

    async def get_secret(self, name: str) -> str:
        def _work() -> str:
            return self._client.get_secret(name).value or ""

        return await asyncio.to_thread(_work)

    async def list_secrets(self) -> list[str]:
        def _work() -> list[str]:
            return [str(s.name) for s in self._client.list_properties_of_secrets()]

        return await asyncio.to_thread(_work)


class AzureServiceBusBackend:  # pragma: no cover - requires live Azure
    def __init__(self, namespace: str, credential: TokenCredential) -> None:
        from azure.servicebus import ServiceBusClient

        self._client = ServiceBusClient(namespace, credential)

    async def send_message(self, queue: str, body: str) -> None:
        from azure.servicebus import ServiceBusMessage

        def _work() -> None:
            with self._client.get_queue_sender(queue) as sender:
                sender.send_messages(ServiceBusMessage(body))

        await asyncio.to_thread(_work)

    async def peek_messages(self, queue: str, max_count: int) -> list[str]:
        def _work() -> list[str]:
            with self._client.get_queue_receiver(queue) as receiver:
                peeked = receiver.peek_messages(max_message_count=max_count)
                return [str(m) for m in peeked]

        return await asyncio.to_thread(_work)


class AzureResourceBackend:  # pragma: no cover - requires live Azure
    def __init__(self, subscription_id: str, credential: TokenCredential) -> None:
        from azure.mgmt.resource import ResourceManagementClient

        self._client = ResourceManagementClient(credential, subscription_id)

    async def list_resource_groups(self) -> list[str]:
        def _work() -> list[str]:
            return [str(g.name) for g in self._client.resource_groups.list()]

        return await asyncio.to_thread(_work)

    async def list_resources(self, resource_group: str) -> list[dict[str, str]]:
        def _work() -> list[dict[str, str]]:
            resources = self._client.resources.list_by_resource_group(resource_group)
            return [{"name": str(r.name), "type": str(r.type)} for r in resources]

        return await asyncio.to_thread(_work)
