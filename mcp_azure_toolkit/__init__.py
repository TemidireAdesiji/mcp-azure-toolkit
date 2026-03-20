"""mcp-azure-toolkit: an MCP server exposing Azure services as AI tools."""

from .config import ToolkitConfig
from .server import build_azure_server, build_server

__version__ = "0.1.0"

__all__ = ["ToolkitConfig", "build_azure_server", "build_server"]
