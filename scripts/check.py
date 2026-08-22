#!/usr/bin/env python3
"""Run the repository's non-mutating fast quality gate."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]


CHECKS = (
    Check("lock", ("uv", "lock", "--check")),
    Check("lint", ("uv", "run", "--locked", "ruff", "check", "src", "scripts", "tests")),
    Check(
        "format",
        ("uv", "run", "--locked", "ruff", "format", "--check", "src", "scripts", "tests"),
    ),
    Check("types", ("uv", "run", "--locked", "pyrefly", "check", "--summarize-errors")),
    Check(
        "unit",
        ("uv", "run", "--locked", "pytest", "tests", "--ignore=tests/e2e", "-q"),
    ),
)


def main() -> int:
    started = time.monotonic()
    for check in CHECKS:
        step_started = time.monotonic()
        print(f"==> {check.name}: {' '.join(check.command)}", flush=True)
        result = subprocess.run(check.command, check=False)
        elapsed = time.monotonic() - step_started
        print(f"<== {check.name}: exit={result.returncode} elapsed={elapsed:.2f}s", flush=True)
        if result.returncode:
            return result.returncode
    print(f"fast quality gate passed in {time.monotonic() - started:.2f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
