"""Tests for the Service Bus tools."""
from helpers import call, tool_names

from mcp_azure_toolkit.backends import InMemoryServiceBusBackend
from mcp_azure_toolkit.server import build_server


async def test_only_service_bus_tools_registered() -> None:
    server = build_server(service_bus=InMemoryServiceBusBackend())
    assert await tool_names(server) == {"servicebus_send", "servicebus_peek"}


async def test_send_then_peek() -> None:
    backend = InMemoryServiceBusBackend()
    server = build_server(service_bus=backend)

    await call(server, "servicebus_send", {"queue": "orders", "body": "order-1"})
    await call(server, "servicebus_send", {"queue": "orders", "body": "order-2"})

    peeked = await call(server, "servicebus_peek", {"queue": "orders"})
    assert peeked == ["order-1", "order-2"]


async def test_send_returns_confirmation() -> None:
    server = build_server(service_bus=InMemoryServiceBusBackend())
    result = await call(server, "servicebus_send", {"queue": "q", "body": "x"})
    assert "q" in result and "sent" in result.lower()


async def test_peek_respects_max_count() -> None:
    backend = InMemoryServiceBusBackend()
    server = build_server(service_bus=backend)
    for i in range(5):
        await call(server, "servicebus_send", {"queue": "q", "body": f"m{i}"})

    peeked = await call(server, "servicebus_peek", {"queue": "q", "max_count": 2})
    assert peeked == ["m0", "m1"]


async def test_peek_is_non_destructive() -> None:
    backend = InMemoryServiceBusBackend()
    server = build_server(service_bus=backend)
    await call(server, "servicebus_send", {"queue": "q", "body": "keep"})

    await call(server, "servicebus_peek", {"queue": "q"})
    # Peeking does not consume - a second peek sees the same message
    assert await call(server, "servicebus_peek", {"queue": "q"}) == ["keep"]


async def test_peek_empty_queue() -> None:
    server = build_server(service_bus=InMemoryServiceBusBackend())
    assert await call(server, "servicebus_peek", {"queue": "empty"}) == []
