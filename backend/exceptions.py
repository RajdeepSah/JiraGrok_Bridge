"""Central error handling + log redaction.

Every upstream failure (Jira HTTP error, timeout, Groq error, bad config, unknown
template, request validation) is turned into a single JSON envelope:

    {"error": {"code": "SOME_CODE", "message": "human readable"}}

Raw upstream response bodies and stack traces are never sent to the client. A
logging filter also strips anything that looks like a secret from log output.
"""

import logging
import re

import groq
import requests
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.errors import ConfigError, TemplateNotFound

logger = logging.getLogger("jgb.backend")


class ApiError(Exception):
    """An error we deliberately surface to the client with a chosen status + code."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _payload(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _map_http_error(exc: requests.exceptions.HTTPError) -> ApiError:
    response = getattr(exc, "response", None)
    status = response.status_code if response is not None else 502
    if status in (401, 403):
        return ApiError(401, "JIRA_AUTH",
                        "Jira rejected your email or API token, or it lacks access to this issue.")
    if status == 404:
        return ApiError(404, "ISSUE_NOT_FOUND",
                        "That Jira issue was not found, or your account can't see it.")
    if status == 429:
        return ApiError(429, "JIRA_RATE_LIMIT",
                        "Jira is rate-limiting requests. Wait a moment and try again.")
    if 400 <= status < 500:
        return ApiError(400, "JIRA_BAD_REQUEST", "Jira rejected the request.")
    return ApiError(502, "JIRA_UPSTREAM", "Jira returned a server error. Try again shortly.")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=_payload(exc.code, exc.message))

    @app.exception_handler(requests.exceptions.HTTPError)
    async def _http_error(_: Request, exc: requests.exceptions.HTTPError):
        mapped = _map_http_error(exc)
        return JSONResponse(status_code=mapped.status_code, content=_payload(mapped.code, mapped.message))

    @app.exception_handler(requests.exceptions.Timeout)
    async def _timeout(_: Request, __: requests.exceptions.Timeout):
        return JSONResponse(status_code=504,
                            content=_payload("JIRA_TIMEOUT", "Jira took too long to respond. Try again."))

    @app.exception_handler(requests.exceptions.ConnectionError)
    async def _conn(_: Request, __: requests.exceptions.ConnectionError):
        return JSONResponse(status_code=502,
                            content=_payload("JIRA_UNREACHABLE", "Could not reach Jira. Try again shortly."))

    @app.exception_handler(groq.APIError)
    async def _groq(_: Request, __: groq.APIError):
        # Do not leak the upstream message - it can reference the shared key/config.
        return JSONResponse(status_code=502,
                            content=_payload("GROQ_UPSTREAM", "The AI service returned an error. Try again shortly."))

    @app.exception_handler(ConfigError)
    async def _config(_: Request, exc: ConfigError):
        logger.error("Server configuration error: %s", exc)
        return JSONResponse(status_code=500,
                            content=_payload("SERVER_NOT_CONFIGURED",
                                             "The server is missing required configuration. Contact the administrator."))

    @app.exception_handler(TemplateNotFound)
    async def _template(_: Request, exc: TemplateNotFound):
        return JSONResponse(status_code=404, content=_payload("TEMPLATE_NOT_FOUND", str(exc)))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p not in ("body",))
        message = first.get("msg", "Invalid request.")
        detail = f"{loc}: {message}" if loc else message
        return JSONResponse(status_code=400, content=_payload("INVALID_REQUEST", detail))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        # Full detail to the server log (no credentials live in these paths); generic to the client.
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(status_code=500,
                            content=_payload("INTERNAL_ERROR", "An unexpected server error occurred."))


# ---------- log redaction ----------

_GROQ_KEY_PATTERN = re.compile(r"gsk_[A-Za-z0-9._-]+")

# Match both ordinary header rendering and common dict/JSON rendering, e.g.:
#   Authorization: Basic dXNlcjp0b2tlbg==
#   {'X-Jira-Token': 'secret', 'X-Jira-Email': 'user@example.com'}
# The unquoted branch deliberately consumes the full value (including an auth
# scheme and its credential) up to a structural delimiter or end-of-line.
_SENSITIVE_HEADER_PATTERN = re.compile(
    r"""
    (?P<prefix>
        (?P<key_quote>["']?)
        (?:x-jira-[a-z0-9_-]+|authorization)
        (?P=key_quote)
        \s*[:=]\s*
    )
    (?P<value>
        "(?:\\.|[^"\\])*"
        |
        '(?:\\.|[^'\\])*'
        |
        [^,;\r\n}\]]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _redact_sensitive_header(match: re.Match) -> str:
    """Keep a header's spelling/quotes while replacing its complete value."""
    value = match.group("value")
    if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
        replacement = f"{value[0]}***{value[0]}"
    else:
        replacement = "***"
    return match.group("prefix") + replacement


class RedactionFilter(logging.Filter):
    """Scrub secret-looking substrings from every log record as a safety net."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _GROQ_KEY_PATTERN.sub("***", message)
        redacted = _SENSITIVE_HEADER_PATTERN.sub(_redact_sensitive_header, redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install_log_redaction() -> None:
    """Attach the redaction filter to the root logger and uvicorn's loggers."""
    filt = RedactionFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "jgb.backend"):
        logging.getLogger(name).addFilter(filt)
