"""Run deterministic local validation checks for the project."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationStep:
    """One validation command with a human-readable name."""

    name: str
    command: list[str]


def build_validation_steps(project_root: Path) -> list[ValidationStep]:
    """Build the staged validation plan for the current scaffold.

    The gate intentionally starts with fast syntax checks and then runs broader
    static and test checks. Future tasks can extend this list with integration,
    webhook and database smoke tests as those files are added.
    """

    python = sys.executable
    steps = [
        ValidationStep("compile", [python, "-m", "compileall", "-q", "src", "tests"]),
        ValidationStep("ruff", ["ruff", "check", "."]),
        ValidationStep("mypy", ["mypy", "src", "tests"]),
        ValidationStep("unit-tests", ["pytest", "tests/unit"]),
    ]

    if (project_root / "scripts" / "smoke_config.py").exists():
        steps.append(ValidationStep("config-smoke", [python, "scripts/smoke_config.py"]))
    if (project_root / "scripts" / "smoke_db.py").exists():
        steps.append(ValidationStep("db-smoke", [python, "scripts/smoke_db.py"]))

    return steps


def run_step(step: ValidationStep, *, cwd: Path) -> int:
    """Run one validation step and return its process exit code."""

    print(f"\n==> {step.name}: {' '.join(step.command)}", flush=True)
    completed = subprocess.run(step.command, cwd=cwd, check=False)  # noqa: S603
    return completed.returncode


def main(argv: Sequence[str] | None = None) -> int:
    """Run all validation steps, or print them with ``--list``."""

    args = list(argv or [])
    project_root = Path(__file__).resolve().parents[1]
    steps = build_validation_steps(project_root)

    if args == ["--list"]:
        for step in steps:
            print(f"{step.name}: {' '.join(step.command)}")
        return 0

    if args:
        print(f"unsupported arguments: {' '.join(args)}", file=sys.stderr)
        return 2

    for step in steps:
        exit_code = run_step(step, cwd=project_root)
        if exit_code != 0:
            print(f"\nValidation failed at step: {step.name}", file=sys.stderr)
            return exit_code

    print("\nValidation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
