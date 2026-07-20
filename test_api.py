import os
import logging

os.environ.setdefault("JIRA_BASE_URL", "https://example.atlassian.net")
os.environ.setdefault("GROQ_API_KEY", "dummy-key")

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from backend.deps import get_config
from backend.exceptions import RedactionFilter
from backend.main import create_app
from core.groq_client import GroqResult

CREDS = {"X-Jira-Email": "user@example.com", "X-Jira-Token": "user-token"}


@pytest.fixture
def client():
    get_config.cache_clear()  # config is cached; start each test fresh
    return TestClient(create_app())


def _http_error(status_code: int) -> requests.exceptions.HTTPError:
    response = MagicMock()
    response.status_code = status_code
    err = requests.exceptions.HTTPError(f"{status_code}")
    err.response = response
    return err


# ---------------------------------------------------------------------------
# meta / templates (no credentials, no secrets)
# ---------------------------------------------------------------------------

def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta_never_leaks_groq_key(client):
    resp = client.get("/api/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jira_base_url"] == "https://example.atlassian.net"
    assert data["model"] == "llama-3.3-70b-versatile"
    assert data["configured"] is True
    # The shared Groq key must never appear anywhere in the response.
    assert "dummy-key" not in resp.text
    assert "groq_api_key" not in resp.text


def test_meta_reports_not_configured(client, monkeypatch):
    monkeypatch.setattr("core.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    data = client.get("/api/meta").json()
    assert data["configured"] is False


def test_list_templates_returns_metadata_only(client):
    data = client.get("/api/templates").json()
    assert len(data) == 12
    assert set(data[0].keys()) == {"id", "name", "description"}  # no full instructions in the list


def test_template_detail_has_instructions(client):
    data = client.get("/api/templates/ticket-improvement").json()
    assert data["id"] == "ticket-improvement"
    assert "grammar" in data["instructions"].lower()


def test_template_not_found(client):
    resp = client.get("/api/templates/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TEMPLATE_NOT_FOUND"


# ---------------------------------------------------------------------------
# /api/run
# ---------------------------------------------------------------------------

@patch("backend.routers.run.build_groq_client")
@patch("backend.routers.run.ask_groq")
@patch("backend.routers.run.get_issue")
def test_run_happy_path(mock_get, mock_ask, mock_build, client):
    mock_get.return_value = {"summary": "Login broken", "description": "Steps..."}
    mock_ask.return_value = GroqResult("GENERATED OUTPUT", False, "llama-3.3-70b-versatile")

    resp = client.post(
        "/api/run",
        headers=CREDS,
        json={"issue_key": "FMDEV-5448", "instructions": "Summarize this ticket."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["output"] == "GENERATED OUTPUT"
    assert data["summary"] == "Login broken"
    assert data["truncated"] is False

    # The user's credentials were used for the Jira call...
    assert mock_get.call_args.args[1] == ("user@example.com", "user-token")
    # ...and the request's instructions flowed through as the system prompt.
    assert mock_ask.call_args.args[1] == "Summarize this ticket."


def test_run_requires_credentials(client):
    resp = client.post("/api/run", json={"issue_key": "FMDEV-1", "instructions": "hi"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MISSING_CREDENTIALS"


def test_run_rejects_bad_issue_key(client):
    resp = client.post("/api/run", headers=CREDS, json={"issue_key": "not a key", "instructions": "hi"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"


def test_run_rejects_empty_instructions(client):
    resp = client.post("/api/run", headers=CREDS, json={"issue_key": "FMDEV-1", "instructions": ""})
    assert resp.status_code == 400


@patch("backend.routers.run.get_issue")
def test_run_maps_jira_auth_error(mock_get, client):
    mock_get.side_effect = _http_error(401)
    resp = client.post("/api/run", headers=CREDS, json={"issue_key": "FMDEV-1", "instructions": "hi"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "JIRA_AUTH"


@patch("backend.routers.run.get_issue")
def test_run_maps_issue_not_found(mock_get, client):
    mock_get.side_effect = _http_error(404)
    resp = client.post("/api/run", headers=CREDS, json={"issue_key": "FMDEV-1", "instructions": "hi"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ISSUE_NOT_FOUND"


# ---------------------------------------------------------------------------
# /api/comment
# ---------------------------------------------------------------------------

@patch("backend.routers.comment.post_comment")
def test_comment_happy_path(mock_post, client):
    mock_post.return_value = {"id": "10100"}
    resp = client.post("/api/comment", headers=CREDS, json={"issue_key": "FMDEV-5448", "comment": "Posted text"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["posted"] is True
    assert "FMDEV-5448" in data["comment_url"]
    assert "focusedCommentId=10100" in data["comment_url"]
    # Posted with the caller's credentials and comment text.
    assert mock_post.call_args.args[1] == ("user@example.com", "user-token")
    assert mock_post.call_args.args[3] == "Posted text"


def test_comment_requires_credentials(client):
    resp = client.post("/api/comment", json={"issue_key": "FMDEV-1", "comment": "x"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MISSING_CREDENTIALS"


# ---------------------------------------------------------------------------
# Production SPA serving / log-secret redaction
# ---------------------------------------------------------------------------

def test_spa_fallback_preserves_asset_and_api_404s(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<main>Jira Grok Bridge SPA</main>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('loaded')", encoding="utf-8")
    monkeypatch.setattr("backend.main.FRONTEND_DIST", dist)

    spa_client = TestClient(create_app())

    deep_link = spa_client.get("/runner/FMDEV-5448")
    assert deep_link.status_code == 200
    assert "Jira Grok Bridge SPA" in deep_link.text
    assert deep_link.headers["content-type"].startswith("text/html")

    assert spa_client.get("/assets/app.js").status_code == 200
    assert spa_client.get("/assets/missing.js").status_code == 404
    assert spa_client.get("/favicon.ico").status_code == 404
    assert spa_client.get("/api/does-not-exist").status_code == 404


@pytest.mark.parametrize(
    ("message", "secrets"),
    [
        ("Authorization: Basic dXNlcjp0b2tlbg==", ["Basic", "dXNlcjp0b2tlbg=="]),
        (
            "headers={'Authorization': 'Bearer auth-secret', "
            "'X-Jira-Email': 'user@example.com', 'X-Jira-Token': 'jira-secret'}",
            ["Bearer", "auth-secret", "user@example.com", "jira-secret"],
        ),
        (
            'headers={"x-jira-session": "session-secret", "safe": "visible"}',
            ["session-secret"],
        ),
    ],
)
def test_redaction_filter_scrubs_complete_sensitive_header_values(message, secrets):
    record = logging.LogRecord("test", logging.INFO, __file__, 1, message, (), None)

    assert RedactionFilter().filter(record) is True
    rendered = record.getMessage()

    assert "***" in rendered
    for secret in secrets:
        assert secret not in rendered
    if '"safe"' in message:
        assert '"safe": "visible"' in rendered
