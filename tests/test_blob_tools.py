"""Tests for the Blob Storage tools."""
import pytest
from helpers import call, tool_names

from mcp_azure_toolkit.backends import InMemoryBlobBackend
from mcp_azure_toolkit.server import build_server

DATA = {
    "docs": {"readme.txt": "hello world", "notes.md": "# notes"},
    "logs": {"app.log": "line1\nline2"},
}


def _server() -> object:
    return build_server(blob=InMemoryBlobBackend(DATA))


async def test_only_blob_tools_registered() -> None:
    names = await tool_names(_server())
    assert names == {"blob_list_containers", "blob_list_blobs", "blob_read"}


async def test_list_containers() -> None:
    result = await call(_server(), "blob_list_containers")
    assert result == ["docs", "logs"]


async def test_list_blobs() -> None:
    result = await call(_server(), "blob_list_blobs", {"container": "docs"})
    assert result == ["notes.md", "readme.txt"]


async def test_read_blob() -> None:
    result = await call(_server(), "blob_read", {"container": "docs", "name": "readme.txt"})
    assert result == "hello world"


async def test_read_missing_blob_raises() -> None:
    with pytest.raises(Exception):  # noqa: B017 - MCP wraps backend errors as a tool error
        await call(_server(), "blob_read", {"container": "docs", "name": "nope.txt"})


async def test_list_blobs_missing_container_raises() -> None:
    with pytest.raises(Exception):  # noqa: B017
        await call(_server(), "blob_list_blobs", {"container": "ghost"})


# Direct backend tests (no MCP layer)


async def test_backend_list_containers_sorted() -> None:
    backend = InMemoryBlobBackend(DATA)
    assert await backend.list_containers() == ["docs", "logs"]


async def test_backend_read_missing_raises_keyerror() -> None:
    backend = InMemoryBlobBackend(DATA)
    with pytest.raises(KeyError):
        await backend.read_blob("docs", "missing")
