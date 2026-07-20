import os

# Shared + user credentials for the CLI tests. Nothing reads these at import time
# anymore (the refactor moved env reads into load_config()/main()), but the CLI
# main() tests exercise load_config() and require_env(), so provide dummies.
os.environ["JIRA_BASE_URL"] = "https://example.atlassian.net"
os.environ["JIRA_EMAIL"] = "test@example.com"
os.environ["JIRA_API_TOKEN"] = "dummy-token"
os.environ["GROQ_API_KEY"] = "dummy-key"

from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

import core.jira_client as jira_client
import jira_grok_bridge
from core.config import AppConfig, load_config
from core.errors import ConfigError, TemplateNotFound
from core.groq_client import GroqResult, ask_groq, build_groq_client
from core.templates import get_template_store

INSTRUCTIONS = "You are a helpful assistant. Do the thing."

# Fixed config for main() tests, so they don't read a real .env (whose load_dotenv
# would otherwise call the mocked open() and be counted by mock assertions).
FAKE_CONFIG = AppConfig(jira_base_url="https://example.atlassian.net", groq_api_key="dummy-key")

# ---------------------------------------------------------------------------
# ADF <-> text conversion (pure; also verifies re-export via jira_grok_bridge)
# ---------------------------------------------------------------------------

SAMPLE_ADF = {
    "type": "doc",
    "version": 1,
    "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "This is a sample description."}]},
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Sub-heading"}]},
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "With some "},
                {"type": "text", "text": "more text.", "marks": [{"type": "strong"}]},
            ],
        },
    ],
}
EXPECTED_TEXT_FROM_ADF = "This is a sample description.\nSub-heading\nWith some more text."

SAMPLE_TEXT = "This is a comment.\nIt has two lines."
EXPECTED_ADF_FROM_TEXT = {
    "type": "doc",
    "version": 1,
    "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "This is a comment."}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "It has two lines."}]},
    ],
}


def test_pure_converters_reexported():
    """The CLI re-exports the pure converters so old references keep working."""
    assert jira_grok_bridge.adf_to_text is jira_client.adf_to_text
    assert jira_grok_bridge.text_to_adf is jira_client.text_to_adf


def test_adf_to_text():
    assert jira_client.adf_to_text(SAMPLE_ADF).strip() == EXPECTED_TEXT_FROM_ADF


def test_adf_to_text_hard_break():
    adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Step 1: open app"},
                    {"type": "hardBreak"},
                    {"type": "text", "text": "Step 2: click login"},
                ],
            }
        ],
    }
    assert jira_client.adf_to_text(adf) == "Step 1: open app\nStep 2: click login\n"


def test_adf_to_text_list_items_and_mentions():
    adf = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "First item"}]}],
                    }
                ],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Assign to "},
                    {"type": "mention", "attrs": {"id": "123", "text": "@John Smith"}},
                ],
            },
        ],
    }
    text = jira_client.adf_to_text(adf)
    assert "- First item" in text
    assert "Assign to @John Smith" in text


def test_text_to_adf():
    assert jira_client.text_to_adf(SAMPLE_TEXT) == EXPECTED_ADF_FROM_TEXT


def test_text_to_adf_never_empty():
    adf = jira_client.text_to_adf("   \n  \n")
    assert adf["content"], "content must not be empty - Jira rejects empty comment bodies"


# ---------------------------------------------------------------------------
# Jira client (globals -> parameters; patch targets moved to core.jira_client)
# ---------------------------------------------------------------------------

@patch("core.jira_client.requests.get")
def test_get_issue_success(mock_get):
    mock_response = mock_get.return_value
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"fields": {"summary": "Test Summary", "description": SAMPLE_ADF}}

    issue = jira_client.get_issue(
        "https://example.atlassian.net", ("test@example.com", "dummy-token"), "TEST-1"
    )
    mock_get.assert_called_once()
    assert mock_get.call_args.args[0] == "https://example.atlassian.net/rest/api/3/issue/TEST-1"
    assert mock_get.call_args.kwargs["auth"] == ("test@example.com", "dummy-token")
    assert "timeout" in mock_get.call_args.kwargs
    assert issue["summary"] == "Test Summary"
    assert issue["description"].strip() == EXPECTED_TEXT_FROM_ADF


@patch("core.jira_client.requests.get")
def test_get_issue_null_description(mock_get):
    mock_response = mock_get.return_value
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"fields": {"summary": "S", "description": None}}

    issue = jira_client.get_issue("https://example.atlassian.net", ("e", "t"), "TEST-1")
    assert issue["description"] == ""


@patch("core.jira_client.requests.get")
def test_get_issue_failure(mock_get):
    mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
    with pytest.raises(requests.exceptions.HTTPError):
        jira_client.get_issue("https://example.atlassian.net", ("e", "t"), "TEST-1")


@patch("core.jira_client.requests.get")
def test_get_issue_encodes_key(mock_get):
    """A crafted issue key must be percent-encoded, not left to escape the path."""
    mock_get.return_value.raise_for_status.return_value = None
    mock_get.return_value.json.return_value = {"fields": {"summary": "", "description": None}}
    jira_client.get_issue("https://example.atlassian.net", ("e", "t"), "A-1/../myself")
    assert "/rest/api/3/issue/A-1%2F..%2Fmyself" == mock_get.call_args.args[0].split("atlassian.net")[1]


@patch("core.jira_client.requests.post")
def test_post_comment(mock_post):
    mock_post.return_value.raise_for_status.return_value = None
    mock_post.return_value.json.return_value = {"id": "10001"}

    result = jira_client.post_comment(
        "https://example.atlassian.net", ("test@example.com", "dummy-token"), "TEST-1", "This is a test comment."
    )
    mock_post.assert_called_once()
    assert mock_post.call_args.args[0] == "https://example.atlassian.net/rest/api/3/issue/TEST-1/comment"
    assert mock_post.call_args.kwargs["auth"] == ("test@example.com", "dummy-token")
    assert "timeout" in mock_post.call_args.kwargs
    assert mock_post.call_args.kwargs["json"]["body"] == jira_client.text_to_adf("This is a test comment.")
    assert result == {"id": "10001"}


# ---------------------------------------------------------------------------
# Groq client (per-call client + instructions parameter)
# ---------------------------------------------------------------------------

def _mock_groq_client(content="Mocked Groq response", finish_reason="stop"):
    client = MagicMock()
    choice = client.chat.completions.create.return_value.choices[0]
    choice.message.content = content
    choice.finish_reason = finish_reason
    return client


def test_ask_groq():
    client = _mock_groq_client()
    result = ask_groq(client, INSTRUCTIONS, "TEST-1", "Summary", "Description")

    client.chat.completions.create.assert_called_once()
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    sys_msg, user_msg = kwargs["messages"]
    assert sys_msg["role"] == "system"
    assert sys_msg["content"] == INSTRUCTIONS  # instructions flow through unchanged
    assert user_msg["role"] == "user"
    for expected in ("TEST-1", "Summary", "Description"):
        assert expected in user_msg["content"]
    assert result.text == "Mocked Groq response"
    assert result.truncated is False
    assert result.model == "llama-3.3-70b-versatile"


def test_ask_groq_truncation_flagged():
    client = _mock_groq_client(finish_reason="length")
    result = ask_groq(client, INSTRUCTIONS, "T-1", "S", "D")
    assert result.truncated is True


@patch("core.groq_client.Groq")
def test_build_groq_client(mock_groq):
    client = build_groq_client("secret-key")
    mock_groq.assert_called_once_with(api_key="secret-key")
    assert client is mock_groq.return_value


# ---------------------------------------------------------------------------
# Template store
# ---------------------------------------------------------------------------

def test_templates_store_loads_twelve():
    store = get_template_store()
    assert len(store.list()) == 12
    assert "ticket-improvement" in [t.id for t in store.list()]


def test_templates_get_missing_raises():
    with pytest.raises(TemplateNotFound):
        get_template_store().get("does-not-exist")


def test_default_template_reproduces_original_behavior():
    """The default template is the old TASK_INSTRUCTIONS: improve the ticket text."""
    default = get_template_store().default()
    assert default.id == "ticket-improvement"
    low = default.instructions.lower()
    for word in ("grammar", "concise", "clarity"):
        assert word in low
    assert "test case" not in low


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def test_load_config_ok():
    cfg = load_config()
    assert cfg.jira_base_url == "https://example.atlassian.net"
    assert cfg.groq_model == "llama-3.3-70b-versatile"


def test_load_config_missing(monkeypatch):
    # Stop load_dotenv from repopulating from a real .env, then clear the vars.
    monkeypatch.setattr("core.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_config()


# ---------------------------------------------------------------------------
# CLI argument parsing + instruction resolution
# ---------------------------------------------------------------------------

def test_cli_parses_flag_before_key():
    """argparse handles '--save TEST-1' correctly (the old order-swap bug is gone)."""
    args = jira_grok_bridge.build_parser().parse_args(["--save", "TEST-1"])
    assert args.issue_key == "TEST-1"
    assert args.mode == "save"


def test_resolve_instructions_precedence():
    store = get_template_store()
    parser = jira_grok_bridge.build_parser()

    inline = parser.parse_args(["T-1", "--instructions", "INLINE", "--template-id", "root-cause-analysis"])
    assert jira_grok_bridge.resolve_instructions(inline, store) == "INLINE"

    by_id = parser.parse_args(["T-1", "--template-id", "executive-summary"])
    assert jira_grok_bridge.resolve_instructions(by_id, store) == store.get("executive-summary").instructions

    default = parser.parse_args(["T-1"])
    assert jira_grok_bridge.resolve_instructions(default, store) == store.default().instructions


def test_cli_instructions_from_file(tmp_path):
    path = tmp_path / "prompt.txt"
    path.write_text("Custom file instructions", encoding="utf-8")
    args = jira_grok_bridge.build_parser().parse_args(["TEST-1", "--instructions", f"@{path}"])
    assert jira_grok_bridge.resolve_instructions(args, get_template_store()) == "Custom file instructions"


def test_cli_list_templates(capsys):
    with patch("sys.argv", ["jira_grok_bridge.py", "--list-templates"]):
        jira_grok_bridge.main()
    out = capsys.readouterr().out
    assert "ticket-improvement" in out
    assert "root-cause-analysis" in out


# ---------------------------------------------------------------------------
# CLI main() output modes
# ---------------------------------------------------------------------------

@patch("jira_grok_bridge.load_config", return_value=FAKE_CONFIG)
@patch("jira_grok_bridge.build_groq_client")
@patch("jira_grok_bridge.get_issue")
@patch("jira_grok_bridge.ask_groq")
@patch("builtins.print")
def test_main_print_mode(mock_print, mock_ask, mock_get, mock_build, mock_config):
    mock_get.return_value = {"summary": "S", "description": "D"}
    mock_ask.return_value = GroqResult("Groq Result", False, "llama-3.3-70b-versatile")
    with patch("sys.argv", ["jira_grok_bridge.py", "TEST-1"]):
        jira_grok_bridge.main()
    mock_print.assert_any_call("\n" + "Groq Result")


@patch("jira_grok_bridge.load_config", return_value=FAKE_CONFIG)
@patch("jira_grok_bridge.build_groq_client")
@patch("jira_grok_bridge.get_issue")
@patch("jira_grok_bridge.ask_groq")
@patch("builtins.open", new_callable=mock_open)
def test_main_save_mode(mock_file, mock_ask, mock_get, mock_build, mock_config):
    mock_get.return_value = {"summary": "S", "description": "D"}
    mock_ask.return_value = GroqResult("Groq Result", False, "llama-3.3-70b-versatile")
    with patch("sys.argv", ["jira_grok_bridge.py", "TEST-1", "--save"]):
        jira_grok_bridge.main()
    mock_file.assert_called_once_with("TEST-1_output.txt", "w", encoding="utf-8")
    mock_file().write.assert_called_once_with("Groq Result")


@patch("jira_grok_bridge.load_config", return_value=FAKE_CONFIG)
@patch("jira_grok_bridge.build_groq_client")
@patch("jira_grok_bridge.get_issue")
@patch("jira_grok_bridge.ask_groq")
@patch("jira_grok_bridge.post_comment")
def test_main_comment_mode(mock_post, mock_ask, mock_get, mock_build, mock_config):
    mock_get.return_value = {"summary": "S", "description": "D"}
    mock_ask.return_value = GroqResult("Groq Result", False, "llama-3.3-70b-versatile")
    with patch("sys.argv", ["jira_grok_bridge.py", "TEST-1", "--comment"]):
        jira_grok_bridge.main()
    mock_post.assert_called_once_with(
        "https://example.atlassian.net", ("test@example.com", "dummy-token"), "TEST-1", "Groq Result"
    )


def test_main_no_args_exits(capsys):
    with patch("sys.argv", ["jira_grok_bridge.py"]):
        with pytest.raises(SystemExit):
            jira_grok_bridge.main()
    assert "issue_key" in capsys.readouterr().err


@patch("jira_grok_bridge.post_comment")
@patch("jira_grok_bridge.get_issue")
def test_main_unknown_flag_rejected(mock_get, mock_post):
    with patch("sys.argv", ["jira_grok_bridge.py", "TEST-1", "--coment"]):
        with pytest.raises(SystemExit):
            jira_grok_bridge.main()
    mock_get.assert_not_called()
    mock_post.assert_not_called()


@patch("jira_grok_bridge.load_config", return_value=FAKE_CONFIG)
@patch("jira_grok_bridge.build_groq_client")
@patch("jira_grok_bridge.get_issue")
def test_main_jira_error_exits(mock_get, mock_build, mock_config):
    mock_get.side_effect = requests.exceptions.HTTPError("404 Client Error")
    with patch("sys.argv", ["jira_grok_bridge.py", "TEST-1"]):
        with pytest.raises(SystemExit) as exc_info:
            jira_grok_bridge.main()
    assert "Jira request failed" in str(exc_info.value)
