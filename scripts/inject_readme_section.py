"""Replace a sentinel-delimited section of README.md with content read from stdin.

The target section must be marked in README.md with a matching pair of HTML comment
sentinels:

    <!-- BEGIN:benchmarks -->
    ...content managed by this script...
    <!-- END:benchmarks -->

The text between the sentinels (the sentinels themselves are kept) is replaced with whatever
is piped in on stdin. This lets generated content (such as the benchmark table) be refreshed
without hand-editing the README.

Run:
    python scripts/benchmark.py | python scripts/inject_readme_section.py --section benchmarks
    cat new_section.md | python scripts/inject_readme_section.py --section benchmarks
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

README_PATH = Path(__file__).resolve().parent.parent / "README.md"


def inject(readme: str, section: str, new_content: str) -> str:
    begin = f"<!-- BEGIN:{section} -->"
    end = f"<!-- END:{section} -->"

    begin_idx = readme.find(begin)
    end_idx = readme.find(end)
    if begin_idx == -1 or end_idx == -1:
        raise ValueError(
            f"Sentinels for section {section!r} not found in {README_PATH}. "
            f"Expected both {begin!r} and {end!r}."
        )
    if end_idx < begin_idx:
        raise ValueError(
            f"Sentinel order is wrong for section {section!r}: {end!r} appears before {begin!r}."
        )

    before = readme[: begin_idx + len(begin)]
    after = readme[end_idx:]
    body = new_content.strip("\n")
    return f"{before}\n{body}\n{after}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--section", required=True, help="sentinel section name to replace")
    args = parser.parse_args()

    new_content = sys.stdin.read()
    if not new_content.strip():
        raise SystemExit("Refusing to inject empty content read from stdin.")

    readme = README_PATH.read_text(encoding="utf-8")
    updated = inject(readme, args.section, new_content)
    README_PATH.write_text(updated, encoding="utf-8")
    print(  # noqa: T201 - script CLI output
        f"Updated section {args.section!r} in {README_PATH}.", file=sys.stderr
    )


if __name__ == "__main__":
    main()
