"""FastAPI dependencies: shared config + per-user credential extraction."""

from functools import lru_cache

from fastapi import Header

from core.config import AppConfig, load_config

from .exceptions import ApiError

# Type alias for HTTP basic auth: (jira_email, jira_api_token)
JiraCredentials = tuple[str, str]


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Load the shared server config once and cache it.

    lru_cache does not cache exceptions, so if configuration is missing the first
    call raises ConfigError and later calls retry once it is fixed.
    """
    return load_config()


def require_jira_credentials(
    x_jira_email: str | None = Header(default=None),
    x_jira_token: str | None = Header(default=None),
) -> JiraCredentials:
    """Pull the caller's Jira email + API token from request headers.

    Kept in headers (not the JSON body) so they never enter a request model that
    could be logged or echoed. Used only to build the per-request auth tuple.
    """
    email = (x_jira_email or "").strip()
    token = (x_jira_token or "").strip()
    if not email or not token:
        raise ApiError(400, "MISSING_CREDENTIALS",
                       "Provide your Jira email and API token (X-Jira-Email / X-Jira-Token headers).")
    return (email, token)
