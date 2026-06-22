from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATE_PATH = ROOT / "scripts" / "validate.py"
SMOKE_CONFIG_PATH = ROOT / "scripts" / "smoke_config.py"


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_validation_steps_are_ordered_from_fast_to_broad() -> None:
    validate = _load_module(VALIDATE_PATH, "validate_script_under_test")

    step_names = [step.name for step in validate.build_validation_steps(ROOT)]

    assert step_names == [
        "compile",
        "ruff",
        "mypy",
        "unit-tests",
        "config-smoke",
        "db-smoke",
    ]


def test_validation_commands_use_current_python_for_local_scripts() -> None:
    validate = _load_module(VALIDATE_PATH, "validate_script_commands_under_test")

    commands = {step.name: step.command for step in validate.build_validation_steps(ROOT)}

    assert commands["compile"][:3] == [sys.executable, "-m", "compileall"]
    assert commands["ruff"] == ["ruff", "check", "."]
    assert commands["mypy"] == ["mypy", "src", "tests"]
    assert commands["unit-tests"] == ["pytest", "tests/unit"]
    assert commands["config-smoke"] == [sys.executable, "scripts/smoke_config.py"]
    assert commands["db-smoke"] == [sys.executable, "scripts/smoke_db.py"]


def test_config_smoke_loads_safe_test_settings_without_live_secrets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    smoke_config = _load_module(SMOKE_CONFIG_PATH, "smoke_config_script_under_test")

    exit_code = smoke_config.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "config smoke passed" in captured.out
    assert "telegram_bot_token" in captured.out
    assert "telegram-token" not in captured.out
    assert "deepseek" not in captured.out.lower()
