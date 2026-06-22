"""Environment-backed application settings with safe redaction helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from os import environ
from urllib.parse import urlsplit, urlunsplit

TEST_ENVIRONMENT = "test"
PRODUCTION_ENVIRONMENT = "production"

_REQUIRED_PRODUCTION_ENV_VARS = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "PUBLIC_WEBHOOK_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DATABASE_URL",
)


class SettingsError(ValueError):
    """Raised when environment settings are missing or invalid."""


@dataclass(frozen=True, repr=False)
class Settings:
    """Runtime settings parsed from environment variables."""

    environment: str
    log_level: str
    port: int
    telegram_bot_token: str | None
    telegram_webhook_secret: str | None
    public_webhook_base_url: str | None
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str | None
    database_url: str | None
    admin_telegram_ids: tuple[int, ...]
    max_message_chars: int
    rate_limit_messages: int
    rate_limit_window_seconds: int
    deepseek_timeout_seconds: float
    deepseek_max_retries: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = environ if env is None else env
        environment = _get_str(source, "ENVIRONMENT", "development").lower()

        settings = cls(
            environment=environment,
            log_level=_get_str(source, "LOG_LEVEL", "INFO").upper(),
            port=_get_int(source, "PORT", 8000, min_value=1, max_value=65535),
            telegram_bot_token=_get_optional_str(source, "TELEGRAM_BOT_TOKEN"),
            telegram_webhook_secret=_get_optional_str(source, "TELEGRAM_WEBHOOK_SECRET"),
            public_webhook_base_url=_get_optional_str(source, "PUBLIC_WEBHOOK_BASE_URL"),
            deepseek_api_key=_get_optional_str(source, "DEEPSEEK_API_KEY"),
            deepseek_base_url=_get_str(source, "DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=_get_optional_str(source, "DEEPSEEK_MODEL")
            or ("test-model" if environment == TEST_ENVIRONMENT else None),
            database_url=_get_optional_str(source, "DATABASE_URL"),
            admin_telegram_ids=_get_int_tuple(source, "ADMIN_TELEGRAM_IDS"),
            max_message_chars=_get_int(source, "MAX_MESSAGE_CHARS", 4000, min_value=1),
            rate_limit_messages=_get_int(source, "RATE_LIMIT_MESSAGES", 20, min_value=1),
            rate_limit_window_seconds=_get_int(
                source,
                "RATE_LIMIT_WINDOW_SECONDS",
                60,
                min_value=1,
            ),
            deepseek_timeout_seconds=_get_float(
                source,
                "DEEPSEEK_TIMEOUT_SECONDS",
                30.0,
                min_value=0.001,
            ),
            deepseek_max_retries=_get_int(source, "DEEPSEEK_MAX_RETRIES", 2, min_value=0),
        )

        settings._validate()
        return settings

    def safe_dict(self) -> dict[str, object]:
        """Return settings data suitable for logs, tests and health diagnostics."""

        return {
            "environment": self.environment,
            "log_level": self.log_level,
            "port": self.port,
            "telegram_bot_token": _redact_secret(self.telegram_bot_token),
            "telegram_webhook_secret": _redact_secret(self.telegram_webhook_secret),
            "public_webhook_base_url": self.public_webhook_base_url,
            "deepseek_api_key": _redact_secret(self.deepseek_api_key),
            "deepseek_base_url": self.deepseek_base_url,
            "deepseek_model": self.deepseek_model,
            "database_url": _redact_database_url(self.database_url),
            "admin_telegram_ids": self.admin_telegram_ids,
            "max_message_chars": self.max_message_chars,
            "rate_limit_messages": self.rate_limit_messages,
            "rate_limit_window_seconds": self.rate_limit_window_seconds,
            "deepseek_timeout_seconds": self.deepseek_timeout_seconds,
            "deepseek_max_retries": self.deepseek_max_retries,
        }

    def __repr__(self) -> str:
        fields = ", ".join(f"{key}={value!r}" for key, value in self.safe_dict().items())
        return f"{self.__class__.__name__}({fields})"

    def _validate(self) -> None:
        if self.environment != PRODUCTION_ENVIRONMENT:
            return

        missing = [
            env_var
            for env_var in _REQUIRED_PRODUCTION_ENV_VARS
            if _settings_attr_is_missing(self, env_var)
        ]
        if missing:
            joined = ", ".join(missing)
            raise SettingsError(f"Missing required production environment variables: {joined}")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Load settings from a mapping or from process environment."""

    return Settings.from_env(env)


def _get_optional_str(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _get_str(env: Mapping[str, str], name: str, default: str) -> str:
    return _get_optional_str(env, name) or default


def _get_int(
    env: Mapping[str, str],
    name: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    raw_value = _get_optional_str(env, name)
    if raw_value is None:
        value = default
    else:
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise SettingsError(f"{name} must be an integer") from exc

    if min_value is not None and value < min_value:
        raise SettingsError(f"{name} must be greater than or equal to {min_value}")
    if max_value is not None and value > max_value:
        raise SettingsError(f"{name} must be less than or equal to {max_value}")
    return value


def _get_float(
    env: Mapping[str, str],
    name: str,
    default: float,
    *,
    min_value: float | None = None,
) -> float:
    raw_value = _get_optional_str(env, name)
    if raw_value is None:
        value = default
    else:
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise SettingsError(f"{name} must be a number") from exc

    if min_value is not None and value < min_value:
        raise SettingsError(f"{name} must be greater than or equal to {min_value}")
    return value


def _get_int_tuple(env: Mapping[str, str], name: str) -> tuple[int, ...]:
    raw_value = _get_optional_str(env, name)
    if raw_value is None:
        return ()

    ids: list[int] = []
    for part in raw_value.replace(";", ",").split(","):
        item = part.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError as exc:
            raise SettingsError(f"{name} must contain only integer IDs") from exc
    return tuple(ids)


def _redact_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return "***"


def _redact_database_url(value: str | None) -> str | None:
    if value is None:
        return None

    parsed = urlsplit(value)
    if parsed.password is None:
        return value

    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"

    username = parsed.username or ""
    netloc = f"{username}:***@{host}" if username else host
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _settings_attr_is_missing(settings: Settings, env_var: str) -> bool:
    attr_name = env_var.lower()
    value = getattr(settings, attr_name)
    return value is None or value == ""
