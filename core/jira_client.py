"""Jira REST v3 client.

The ADF <-> text conversions are pure and were moved here unchanged from the
original script. ``get_issue`` / ``post_comment`` are the original bodies with the
module globals (JIRA_BASE_URL, JIRA_AUTH) replaced by explicit ``base_url`` and
``auth`` parameters, so each web request can use the calling user's own credentials.
"""

from urllib.parse import quote

import requests

Auth = tuple[str, str]  # (email, api_token) - HTTP basic auth for Jira Cloud


# ---------- ADF <-> plain text (pure, unchanged) ----------

def adf_to_text(node):
    """Jira returns rich text (like the description) as Atlassian Document Format - a nested
    JSON structure, not a plain string. This walks the structure and flattens it to text."""
    if not isinstance(node, dict):
        return ""
    node_type = node.get("type")
    if node_type == "hardBreak":
        return "\n"
    if node_type == "mention":
        return node.get("attrs", {}).get("text", "")
    if node_type == "emoji":
        return node.get("attrs", {}).get("shortName", "")
    if node_type == "inlineCard":
        return node.get("attrs", {}).get("url", "")
    parts = [node.get("text", "")]
    if node_type == "listItem":
        parts.append("- ")
    for child in node.get("content", []):
        parts.append(adf_to_text(child))
    if node_type in ("paragraph", "heading", "codeBlock"):
        parts.append("\n")
    return "".join(parts)


def text_to_adf(text):
    """The reverse of adf_to_text - wraps plain text in the structure Jira's v3 API
    requires for comment bodies (it rejects a plain string)."""
    content = [
        {"type": "paragraph", "content": [{"type": "text", "text": line}]}
        for line in text.split("\n")
        if line.strip()
    ]
    if not content:
        # Jira rejects a doc whose content array is empty.
        content = [{"type": "paragraph", "content": [{"type": "text", "text": "(empty response)"}]}]
    return {"type": "doc", "version": 1, "content": content}


# ---------- network calls (globals -> parameters) ----------

def get_issue(base_url: str, auth: Auth, issue_key: str, *, timeout: int = 30) -> dict:
    """Fetch a Jira issue and return its summary + flattened description.

    ``issue_key`` is percent-encoded before being placed in the URL path so a
    crafted key cannot escape the /issue/ path and reach other REST endpoints.
    """
    url = f"{base_url}/rest/api/3/issue/{quote(issue_key, safe='')}"
    response = requests.get(url, auth=auth, headers={"Accept": "application/json"}, timeout=timeout)
    response.raise_for_status()
    fields = response.json()["fields"]
    return {
        "summary": fields.get("summary", ""),
        "description": adf_to_text(fields.get("description") or {}),
    }


def verify_credentials(base_url: str, auth: Auth, *, timeout: int = 30) -> dict:
    """Confirm the given credentials work by fetching the current user (/myself).

    Raises requests.HTTPError (401/403) if the email/token are wrong. Returns the
    caller's own account info - never another user's."""
    url = f"{base_url}/rest/api/3/myself"
    response = requests.get(url, auth=auth, headers={"Accept": "application/json"}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def post_comment(base_url: str, auth: Auth, issue_key: str, text: str, *, timeout: int = 30) -> dict:
    """Post ``text`` as a comment on the issue. Returns Jira's JSON response, which
    includes the new comment's id and ``self`` link (used to build a link back)."""
    url = f"{base_url}/rest/api/3/issue/{quote(issue_key, safe='')}/comment"
    response = requests.post(
        url,
        auth=auth,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"body": text_to_adf(text)},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
