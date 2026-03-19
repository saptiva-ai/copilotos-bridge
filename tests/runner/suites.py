from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Suite:
    name: str
    description: str
    commands: Sequence[list[str]]


def discover_scripts(base_dir: Path) -> list[Path]:
    scripts = [path for path in base_dir.rglob("test_*.py")]
    return sorted(path for path in scripts if path.name != "run_all.py")


def python_command(path: Path) -> list[str]:
    return [sys.executable, str(path)]


def build_suite_from_dir(name: str, description: str, base_dir: Path) -> Suite:
    commands = tuple(python_command(path) for path in discover_scripts(base_dir))
    return Suite(name=name, description=description, commands=commands)


def pytest_command(path: str) -> list[str]:
    return [sys.executable, "-m", "pytest", path]


def all_suites() -> dict[str, Suite]:
    suites = {
        "e2e_regression": build_suite_from_dir(
            "e2e_regression",
            "E2E regression + happy path",
            PROJECT_ROOT / "tests" / "e2e" / "regression",
        ),
        "e2e_conversation": build_suite_from_dir(
            "e2e_conversation",
            "E2E conversation context",
            PROJECT_ROOT / "tests" / "e2e" / "conversation",
        ),
        "e2e_clarification": build_suite_from_dir(
            "e2e_clarification",
            "E2E clarification scenarios",
            PROJECT_ROOT / "tests" / "e2e" / "clarification",
        ),
        "e2e_security": build_suite_from_dir(
            "e2e_security",
            "E2E security coverage",
            PROJECT_ROOT / "tests" / "e2e" / "security",
        ),
        "e2e_charts": build_suite_from_dir(
            "e2e_charts",
            "E2E chart persistence",
            PROJECT_ROOT / "tests" / "e2e" / "charts",
        ),
        "e2e_metrics": build_suite_from_dir(
            "e2e_metrics",
            "E2E metrics suite",
            PROJECT_ROOT / "tests" / "e2e" / "metrics",
        ),
        "integration": build_suite_from_dir(
            "integration",
            "Integration coverage",
            PROJECT_ROOT / "tests" / "integration",
        ),
        "smoke": build_suite_from_dir(
            "smoke",
            "Smoke tests for critical paths",
            PROJECT_ROOT / "tests" / "smoke",
        ),
        "unit": Suite(
            name="unit",
            description="Unit tests",
            commands=(pytest_command("tests/unit"),),
        ),
        "backend_unit": Suite(
            name="backend_unit",
            description="Backend unit tests",
            commands=(pytest_command("apps/backend/tests/unit"),),
        ),
        "e2e_all": build_suite_from_dir(
            "e2e_all",
            "All E2E suites",
            PROJECT_ROOT / "tests" / "e2e",
        ),
    }
    return suites


def default_suites() -> tuple[str, ...]:
    return (
        "e2e_regression",
        "e2e_conversation",
        "e2e_clarification",
        "e2e_security",
        "e2e_charts",
        "e2e_metrics",
        "integration",
        "unit",
    )


def resolve_suites(names: Iterable[str]) -> list[Suite]:
    suites = all_suites()
    resolved = []
    for name in names:
        if name not in suites:
            raise ValueError(f"Unknown suite '{name}'. Use --list to see options.")
        resolved.append(suites[name])
    return resolved
