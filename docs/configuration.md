# Configuration

All configuration is through environment variables and one JSON file of templates.
There is no config UI and no database.

## Environment variables

The app reads these from the process environment, and from a `.env` file at the
repo root if one exists (`load_dotenv()` doesn't override variables already set in
the environment).

| Variable | Required for | Default | Purpose |
| --- | --- | --- | --- |
| `JIRA_BASE_URL` | Web + CLI | — | The fixed Jira site origin, e.g. `https://firemon.atlassian.net`. Origin only — no `/browse/...` path. A trailing slash is trimmed automatically. |
| `GROQ_API_KEY` | Web + CLI | — | The shared, server-side Groq key. Never sent to the browser or returned by the API. |
| `GROQ_MODEL` | Optional | `llama-3.3-70b-versatile` | Which Groq model to use. |
| `GROQ_MAX_TOKENS` | Optional | `4096` | Max output tokens. Must be an integer, or the server refuses to start with a clear error. |
| `JIRA_EMAIL` | CLI only | — | The Jira account email the CLI authenticates with. |
| `JIRA_API_TOKEN` | CLI only | — | The Jira API token the CLI authenticates with. |
| `JGB_DEV_CORS` | Dev only | unset | Set to `1`/`true`/`yes` to allow the Vite dev origin to call the API cross-origin. Leave unset in production. |

### Shared vs. per-user settings

This split is the whole reason the tool can be shared:

- **Shared, server-side** — `JIRA_BASE_URL` and `GROQ_API_KEY` (plus the optional
  model settings). On a shared web server, these are the *only* things you configure.
- **Per-user Jira credentials** — In the web app, each person enters their own Jira
  email and token in the browser; the server uses them for that one request and never
  stores them. `JIRA_EMAIL` and `JIRA_API_TOKEN` in `.env` are read **only by the
  CLI**. Do not set them on a shared web server.

### The one rule about frontend variables

Never create a browser-visible variable like `VITE_GROQ_API_KEY` or
`VITE_JIRA_BASE_URL`. Vite embeds anything named `VITE_*` directly into the client
JavaScript, which would leak the secret to every user. The frontend is designed so
nothing secret ever needs to reach it — the API base is just an empty string
(same-origin), and the model name comes from `/api/meta` at runtime.

### Where the values are read

`core/config.py` → `load_config()` reads and validates everything into an immutable
`AppConfig`. If a required value is missing it raises `ConfigError`, which the web
app turns into a clean "server not configured" message and the CLI turns into a
one-line exit message. The backend caches the config (`lru_cache`), but because
`lru_cache` doesn't cache exceptions, a misconfigured server will pick up the fix on
the next request once you set the variable — no restart needed for that case.

## Templates

The twelve instruction templates live in `core/templates.json`. Each is one object:

```json
{
  "id": "ticket-improvement",
  "name": "Ticket Improvement",
  "description": "Improve grammar, clarity, formatting, and consistency.",
  "instructions": "You are an expert technical editor. Improve the Jira ticket..."
}
```

| Field | Rule |
| --- | --- |
| `id` | Unique across the file. Used in the URL and the CLI's `--template-id`. |
| `name` | Shown on the gallery card and used in download filenames. |
| `description` | The one-line summary on the card. |
| `instructions` | The system prompt sent to Groq. This is the actual work. |

`instructions` is the text that becomes the model's system prompt. The ticket
(summary + description) is sent as the user message. So a template is really just a
carefully written prompt.

### The default

`ticket-improvement` is the default. The CLI uses it when you don't pass
`--template-id` or `--instructions`, and it reproduces the original script's
behavior. If it were ever removed, the store falls back to the first template in the
file.

### The current twelve

| id | Name | What it produces |
| --- | --- | --- |
| `ticket-improvement` | Ticket Improvement | A cleaned-up Summary + Description. |
| `root-cause-analysis` | Root Cause Analysis | Likely cause, evidence, missing info, confidence, next steps. |
| `qa-test-plan` | QA Test Plan Generator | Preconditions, positive/negative/edge/regression tests, expected results. |
| `manual-test-cases` | Manual Test Case Generator | A Markdown table of executable test cases. |
| `automation-candidate` | Automation Candidate Detector | Whether it's worth automating, and how. |
| `acceptance-criteria` | Acceptance Criteria Generator | Gherkin Given/When/Then scenarios. |
| `missing-information` | Missing Information Checker | A readiness checklist of what the ticket lacks. |
| `developer-summary` | Developer Summary | Problem, expected/actual behavior, affected modules, risks. |
| `executive-summary` | Executive Summary | One plain-language paragraph under 100 words. |
| `documentation` | Documentation Generator | Internal docs: problem, solution, impact, follow-ups. |
| `bug-classification` | Bug Classification | One or more fixed categories, with justification. |
| `questions-for-reporter` | Questions for the Reporter | The clarifications needed before work starts. |

Most templates are written in the voice of a FireMon role (QA engineer, technical
lead, business analyst) and share the same guardrails: reason only from what the
ticket says, preserve technical details exactly, and return only the requested
format.

### Adding or editing a template

Append or edit an object in `core/templates.json`. No Python or TypeScript change is
needed — both the CLI and the web app pick it up. Keep ids unique. The store
validates the file on load, so a malformed entry (missing a field, duplicate id)
fails fast with a clear error rather than shipping a broken template. Full steps and
verification are in [maintenance](maintenance.md#add-or-edit-a-template).
