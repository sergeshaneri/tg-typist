from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

PROMPTS_PACKAGE = "tg_typist.prompts"
DEFAULT_SYSTEM_PROMPT_RESOURCE = "typist_system.md"
SYSTEM_PROMPT_VERSION = "typist_system_v1"


@dataclass(frozen=True, slots=True)
class SystemPrompt:
    """Versioned system prompt loaded from bundled package resources."""

    version: str
    text: str


class PromptLoadError(ValueError):
    """Raised when a bundled prompt resource cannot be loaded safely."""


def load_system_prompt(
    resource_name: str = DEFAULT_SYSTEM_PROMPT_RESOURCE,
    *,
    version: str = SYSTEM_PROMPT_VERSION,
) -> SystemPrompt:
    """Load a versioned system prompt from package resources.

    The loader is deterministic and does not read environment variables,
    network resources, or user-provided filesystem paths.
    """

    try:
        prompt_resource = resources.files(PROMPTS_PACKAGE).joinpath(resource_name)
        prompt_text = prompt_resource.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise PromptLoadError(
            f"system prompt resource not found: {resource_name}"
        ) from exc
    except OSError as exc:
        raise PromptLoadError(
            f"system prompt resource could not be loaded: {resource_name}"
        ) from exc

    text = prompt_text.strip()
    if not text:
        raise PromptLoadError(f"system prompt resource is empty: {resource_name}")

    return SystemPrompt(version=version, text=text)
