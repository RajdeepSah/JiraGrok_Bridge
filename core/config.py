"""Runtime configuration.

The original script read every credential and built the Groq client at *import*
time, which made it impossible to reuse for a multi-user web app. Here the shared,
server-side settings are read only when ``load_config()`` is *called*, so importing
this module has no side effects and tests can set the environment first.

Only the SHARED settings live here:
    JIRA_BASE_URL   - the fixed Jira site origin (e.g. https://firemon.atlassian.net)
    GROQ_API_KEY    - the shared Groq API key (never sent to the browser)
    GROQ_MODEL      - optional model override (defaults to the original model)
    GROQ_MAX_TOKENS - optional max_tokens override

The per-user Jira email + API token are NOT read here. In the web app they arrive
per request; in the CLI they are read from the environment inside main().
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .errors import ConfigError

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_MAX_TOKENS = 4096


@dataclass(frozen=True)
class AppConfig:
    """Immutable snapshot of the shared, server-side configuration.

    ``groq_api_key`` is a secret: it is used only to build the Groq client and is
    never placed on a response model, so it cannot be serialized back to a client.
    """

    jira_base_url: str
    groq_api_key: str
    groq_model: str = DEFAULT_GROQ_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS


def load_config() -> AppConfig:
    """Read shared settings from the environment (and a .env file, if present).

    Raises ConfigError if a required setting is missing so the caller can report a
    clean message instead of failing deep inside a request.
    """
    load_dotenv()  # no-op if there is no .env; does not override already-set vars

    base_url = (os.environ.get("JIRA_BASE_URL") or "").strip().rstrip("/")
    groq_api_key = (os.environ.get("GROQ_API_KEY") or "").strip()

    missing = [
        name
        for name, value in (("JIRA_BASE_URL", base_url), ("GROQ_API_KEY", groq_api_key))
        if not value
    ]
    if missing:
        raise ConfigError(
            "Missing required server configuration: "
            + ", ".join(missing)
            + ". Set them in the environment or a .env file."
        )

    model = (os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()
    try:
        max_tokens = int(os.environ.get("GROQ_MAX_TOKENS") or DEFAULT_MAX_TOKENS)
    except ValueError as exc:
        raise ConfigError("GROQ_MAX_TOKENS must be an integer.") from exc

    return AppConfig(
        jira_base_url=base_url,
        groq_api_key=groq_api_key,
        groq_model=model,
        max_tokens=max_tokens,
    )
