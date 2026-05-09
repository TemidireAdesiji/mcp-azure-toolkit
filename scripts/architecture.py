"""Generate the architecture diagram for mcp-azure-toolkit.

Models the real runtime structure: an MCP client launches the FastMCP server over stdio;
the server registers tools that depend on narrow async backend protocols; each protocol has
a real Azure backend (sync SDK wrapped in asyncio.to_thread) reached through
DefaultAzureCredential, plus an in-memory fake used for tests and local development.

Requirements:
    pip install diagrams
    # plus the graphviz "dot" binary on PATH (e.g. apt-get install graphviz)

Run:
    python scripts/architecture.py

Output:
    assets/architecture.png
"""
from __future__ import annotations

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.general import Resource, Toolbox
from diagrams.azure.identity import ManagedIdentities
from diagrams.azure.integration import AzureServiceBus
from diagrams.azure.security import KeyVaults
from diagrams.azure.storage import BlobStorage
from diagrams.onprem.client import Client

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
OUTPUT_BASENAME = ASSETS_DIR / "architecture"


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    graph_attr = {"fontsize": "16", "labelloc": "t", "pad": "0.5", "splines": "spline"}

    with Diagram(
        "mcp-azure-toolkit",
        filename=str(OUTPUT_BASENAME),
        outformat="png",
        show=False,
        direction="LR",
        graph_attr=graph_attr,
    ):
        client = Client("MCP client\n(Claude Desktop, Copilot)")

        with Cluster("FastMCP server (stdio)"):
            tools = Toolbox("Registered tools\n(9 across 4 services)")

            with Cluster("Backend protocols"):
                blob_proto = Resource("BlobBackend")
                secrets_proto = Resource("SecretsBackend")
                bus_proto = Resource("ServiceBusBackend")
                resource_proto = Resource("ResourceBackend")
                protocols = [blob_proto, secrets_proto, bus_proto, resource_proto]

        credential = ManagedIdentities("DefaultAzureCredential")

        with Cluster("Azure backends (live subscription)"):
            blob = BlobStorage("AzureBlobBackend\n-> Blob Storage")
            secrets = KeyVaults("AzureSecretsBackend\n-> Key Vault")
            bus = AzureServiceBus("AzureServiceBusBackend\n-> Service Bus")
            resources = Resource("AzureResourceBackend\n-> Resource Manager")
            azure_backends = [blob, secrets, bus, resources]

        with Cluster("In-memory backends (tests / local dev)"):
            fakes = Resource("InMemory*Backend\n(no Azure needed)")

        client >> Edge(label="stdio (MCP)") >> tools
        tools >> Edge(label="depends on") >> protocols

        # Protocols are satisfied by the live Azure backends in production...
        for proto, backend in zip(protocols, azure_backends):
            proto >> Edge(label="async", style="solid") >> backend

        # ...or by the in-memory fakes for tests and local development.
        for proto in protocols:
            proto >> Edge(label="or", style="dashed") >> fakes

        # The live Azure backends authenticate via DefaultAzureCredential.
        for backend in azure_backends:
            credential >> Edge(style="dotted", label="auth") >> backend

    print(f"Wrote {OUTPUT_BASENAME.with_suffix('.png')}")  # noqa: T201 - script CLI output


if __name__ == "__main__":
    main()
