# API reference

The backend is a small REST API under `/api`. When the server is running, live
interactive docs are at `/docs` (Swagger UI) and the schema is at
`/openapi.json`.

All requests and responses are JSON. Errors always use the same envelope (see
[Errors](#errors) below).

## Authentication

There are no sessions, cookies, or API keys for the backend itself. The endpoints
that touch Jira require the caller's own Jira credentials, sent as headers:

```
X-Jira-Email: you@firemon.com
X-Jira-Token: <your Jira API token>
```

Credentials must be in these headers only — never in the URL, query string, or body.
Endpoints that don't touch Jira (`/health`, `/meta`, `/templates`) need no
credentials.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/health` | No | Liveness check. |
| `GET` | `/api/meta` | No | Non-secret server info: Jira URL, model, configured flag. |
| `GET` | `/api/templates` | No | Template list (id, name, description). |
| `GET` | `/api/templates/{id}` | No | One template including its full instructions. |
| `POST` | `/api/run` | Yes | Fetch a Jira issue and generate output. |
| `POST` | `/api/comment` | Yes | Post text as a comment on a Jira issue. |
| `POST` | `/api/validate` | Yes | Check credentials, and optionally whether an issue exists. |

### GET /api/health

```json
{ "status": "ok" }
```

### GET /api/meta

Returns what the UI needs to render, and nothing secret. If the server isn't
configured yet, it returns `configured: false` instead of erroring, so the UI can
show a notice.

```json
{
  "jira_base_url": "https://firemon.atlassian.net",
  "model": "llama-3.3-70b-versatile",
  "configured": true
}
```

The Groq key never appears here.

### GET /api/templates

Metadata only — the full instruction text is intentionally left out of the list so
the gallery stays light.

```json
[
  { "id": "ticket-improvement", "name": "Ticket Improvement", "description": "Improve grammar, clarity, formatting, and consistency." }
]
```

### GET /api/templates/{id}

The full template, including `instructions`. Used by the "View details" modal.
Returns `404 TEMPLATE_NOT_FOUND` for an unknown id.

### POST /api/run

The main endpoint. Fetches the issue with the caller's Jira credentials, then sends
it to Groq using `instructions` as the system prompt.

Request:

```json
{
  "issue_key": "FMDEV-8888",
  "instructions": "You are an expert technical editor...",
  "template_id": "ticket-improvement"
}
```

| Field | Rules |
| --- | --- |
| `issue_key` | Must match `^[A-Za-z][A-Za-z0-9]+-\d+$`, max 64 chars. |
| `instructions` | 1–20,000 characters. This is what the model actually follows. |
| `template_id` | Optional, for auditing only. `instructions` is always what's used. |

Response:

```json
{
  "issue_key": "FMDEV-8888",
  "summary": "Login page returns 500",
  "description": "Steps to reproduce...",
  "output": "Summary: ...\nDescription: ...",
  "truncated": false,
  "model": "llama-3.3-70b-versatile"
}
```

`truncated` is `true` when the model hit `max_tokens` and the output was cut off.

Note that `template_id` is metadata only — the server generates from `instructions`,
never by re-reading the template. This lets the UI send an *edited* template without
the edit being silently ignored.

### POST /api/comment

Posts text as a comment on the issue, attributed to the caller (it's their token).

Request:

```json
{ "issue_key": "FMDEV-8888", "comment": "The generated text to post." }
```

`comment` is 1–32,000 characters. Response:

```json
{
  "issue_key": "FMDEV-8888",
  "posted": true,
  "comment_url": "https://firemon.atlassian.net/browse/FMDEV-8888?focusedCommentId=10100"
}
```

`comment_url` links straight to the new comment. It's `null` if Jira didn't return a
comment id.

### POST /api/validate

An optional pre-flight check. Confirms the credentials work (by fetching `/myself`
from Jira), and if you pass an `issue_key`, whether that issue is visible to you.

Request (issue key optional):

```json
{ "issue_key": "FMDEV-8888" }
```

Response:

```json
{ "valid": true, "issue_exists": true }
```

`issue_exists` is `null` when no key was given, `false` when the key returns 404, and
`true` when it's found. Bad credentials return `401 JIRA_AUTH`.

## Errors

Every failure — bad input, Jira rejecting you, Groq failing, a missing config — comes
back in one shape, with the right HTTP status:

```json
{
  "error": {
    "code": "ISSUE_NOT_FOUND",
    "message": "That Jira issue was not found, or your account can't see it."
  }
}
```

Raw upstream response bodies and stack traces are never sent to the client. The
messages are written to be shown directly to a user.

### Error codes

| HTTP | Code | When |
| --- | --- | --- |
| 400 | `MISSING_CREDENTIALS` | The `X-Jira-*` headers were missing or empty. |
| 400 | `INVALID_REQUEST` | Request body failed validation (bad issue key, empty instructions, too long). |
| 400 | `JIRA_BAD_REQUEST` | Jira rejected the request (other 4xx). |
| 401 | `JIRA_AUTH` | Jira rejected the email/token, or it can't see the issue. |
| 404 | `ISSUE_NOT_FOUND` | The issue doesn't exist or isn't visible to you. |
| 404 | `TEMPLATE_NOT_FOUND` | No template with that id. |
| 429 | `JIRA_RATE_LIMIT` | Jira is rate-limiting. Wait and retry. |
| 500 | `SERVER_NOT_CONFIGURED` | The server is missing `JIRA_BASE_URL` or `GROQ_API_KEY`. |
| 500 | `INTERNAL_ERROR` | An unexpected server error. Details go to the server log only. |
| 502 | `JIRA_UPSTREAM` | Jira returned a 5xx. |
| 502 | `JIRA_UNREACHABLE` | Couldn't connect to Jira. |
| 502 | `GROQ_UPSTREAM` | The Groq API returned an error. The upstream message is deliberately not forwarded. |
| 504 | `JIRA_TIMEOUT` | Jira took too long. |

The frontend's `fetch` wrapper adds two client-side codes that never come from the
server: `TIMEOUT` (the request aborted after its timeout) and `NETWORK` (couldn't
reach the server at all).

## Curl examples

```bash
# Health
curl http://127.0.0.1:8000/api/health

# Run a ticket through a template
curl -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -H "X-Jira-Email: you@firemon.com" \
  -H "X-Jira-Token: $JIRA_API_TOKEN" \
  -d '{"issue_key":"FMDEV-8888","instructions":"Summarize this ticket in one paragraph."}'
```
