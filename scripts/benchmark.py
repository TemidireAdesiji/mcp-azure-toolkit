"""Benchmark the MCP tool-dispatch path without a live Azure subscription.

This wires the in-memory backends into ``build_server`` and measures the latency of
``FastMCP.call_tool(...)`` per tool. It exercises the real dispatch path (argument
validation, tool lookup, async invocation, result serialisation) while the backends are
trivial in-memory fakes, so what is measured is the toolkit's own overhead rather than
Azure round-trips.

Latency percentiles (p50/p95/p99) and the mean are reported per tool as a Markdown table on
STDOUT.

Requirements:
    pip install -e .        # the [azure] extra is NOT needed for this benchmark

Run:
    python scripts/benchmark.py
    python scripts/benchmark.py --iterations 5000

Pipe the table into a README section (see scripts/inject_readme_section.py):
    python scripts/benchmark.py | python scripts/inject_readme_section.py --section benchmarks
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_azure_toolkit.backends import (
    InMemoryBlobBackend,
    InMemoryResourceBackend,
    InMemorySecretsBackend,
    InMemoryServiceBusBackend,
)
from mcp_azure_toolkit.server import build_server

# A tool plus the arguments to call it with. Backends are seeded below to make every call
# resolve to a real value.
Case = tuple[str, dict[str, Any]]

CASES: list[Case] = [
    ("blob_list_containers", {}),
    ("blob_list_blobs", {"container": "docs"}),
    ("blob_read", {"container": "docs", "name": "readme.txt"}),
    ("keyvault_list_secrets", {}),
    ("keyvault_get_secret", {"name": "api-key"}),
    ("servicebus_send", {"queue": "jobs", "body": "hello"}),
    ("servicebus_peek", {"queue": "jobs", "max_count": 10}),
    ("resource_list_groups", {}),
    ("resource_list_resources", {"resource_group": "rg-prod"}),
]


def _build_seeded_server() -> FastMCP:
    blob = InMemoryBlobBackend(
        {"docs": {"readme.txt": "hello world", "notes.md": "# notes"}, "logs": {"app.log": "x"}}
    )
    secrets = InMemorySecretsBackend({"api-key": "s3cr3t", "db-password": "hunter2"})
    service_bus = InMemoryServiceBusBackend()
    resources = InMemoryResourceBackend(
        {"rg-prod": [{"name": "vm1", "type": "Microsoft.Compute/virtualMachines"}]}
    )
    return build_server(
        blob=blob, secrets=secrets, service_bus=service_bus, resources=resources
    )


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile in milliseconds. ``values`` must be non-empty."""
    ordered = sorted(values)
    rank = max(1, round(pct / 100.0 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


async def _bench_case(
    server: FastMCP, name: str, arguments: dict[str, Any], iterations: int, warmup: int
) -> dict[str, float]:
    for _ in range(warmup):
        await server.call_tool(name, arguments)

    samples_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        await server.call_tool(name, arguments)
        samples_ms.append((time.perf_counter() - start) * 1000.0)

    return {
        "mean": statistics.fmean(samples_ms),
        "p50": _percentile(samples_ms, 50),
        "p95": _percentile(samples_ms, 95),
        "p99": _percentile(samples_ms, 99),
    }


async def _run(iterations: int, warmup: int) -> list[tuple[str, dict[str, float]]]:
    server = _build_seeded_server()
    results: list[tuple[str, dict[str, float]]] = []
    for name, arguments in CASES:
        results.append((name, await _bench_case(server, name, arguments, iterations, warmup)))
    return results


def _render_markdown(
    results: list[tuple[str, dict[str, float]]], iterations: int
) -> str:
    lines = [
        f"In-memory tool-dispatch latency over {iterations} iterations per tool "
        "(no live Azure; measures toolkit overhead only).",
        "",
        "| Tool | mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) |",
        "|---|---|---|---|---|",
    ]
    for name, stats in results:
        lines.append(
            f"| `{name}` | {stats['mean']:.3f} | {stats['p50']:.3f} | "
            f"{stats['p95']:.3f} | {stats['p99']:.3f} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=2000, help="timed calls per tool")
    parser.add_argument("--warmup", type=int, default=100, help="untimed warmup calls per tool")
    args = parser.parse_args()

    results = asyncio.run(_run(args.iterations, args.warmup))
    print(_render_markdown(results, args.iterations))  # noqa: T201 - script CLI output


if __name__ == "__main__":
    main()
