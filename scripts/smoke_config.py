"""Smoke test for safe config loading without live service credentials."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tg_typist.settings import load_settings  # noqa: E402


def main() -> int:
    """Load test settings and print a redacted, minimal diagnostic."""

    settings = load_settings({"ENVIRONMENT": "test"})
    safe_settings = settings.safe_dict()

    print(
        "config smoke passed: "
        f"environment={safe_settings['environment']} "
        f"port={safe_settings['port']} "
        f"telegram_bot_token={safe_settings['telegram_bot_token']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
