# Architecture

## The pieces

The repository is one project with four parts that share a common core.

```
jira_grok_bridge.py     CLI — argparse on top of core/
backend/                FastAPI app: REST API + serves the built SPA in production
frontend/               React + TypeScript + Vite + Mantine single-page app
core/                   Framework-independent logic shared by the CLI and backend
api/index.py            Vercel entrypoint that imports the FastAPI app
```

The important rule: **`core/` knows nothing about FastAPI, React, or the CLI.** It's
plain Python that talks to Jira and Groq. Both the CLI and the backend import it.
That's why a change to a template or the Groq call shows up in both places at once.

### `core/` — the shared logic

| File | Responsibility |
| --- | --- |
| `config.py` | Reads the shared server settings (`JIRA_BASE_URL`, `GROQ_API_KEY`, model options) into an immutable `AppConfig`. Reads happen when `load_config()` is *called*, not at import, so tests and callers control timing. |
| `jira_client.py` | Jira REST v3 calls: `get_issue`, `post_comment`, `verify_credentials`, plus the pure ADF↔text converters. Credentials are passed in per call — never module globals. |
| `groq_client.py` | Builds a Groq client per call and sends the ticket with the chosen instructions as the system prompt. Returns text plus a `truncated` flag. |
| `templates.py` | Loads and validates `templates.json` once, caches it, and looks templates up by id. |
| `templates.json` | The twelve instruction templates. Data, not code — see [configuration](configuration.md#templates). |
| `errors.py` | Two small exception types: `ConfigError` and `TemplateNotFound`. |

Two design choices worth calling out:

- **Nothing is read at import time.** The original script built the Groq client and
  read credentials the moment it was imported, which made it impossible to reuse for
  a multi-user server. Now importing `core` has no side effects.
- **Credentials are parameters, not globals.** `get_issue(base_url, auth, key)` takes
  the auth tuple explicitly, so each web request can use a different user's token.

### `backend/` — the API and production host

| File | Responsibility |
| --- | --- |
| `main.py` | The app factory `create_app()`. Wires routers under `/api`, installs error handling and log redaction, and (in production) mounts the built SPA at `/`. |
| `deps.py` | FastAPI dependencies: cached shared config, and pulling the user's Jira credentials out of request headers. |
| `schemas.py` | Pydantic request/response models. Notably, there is no field anywhere for the Groq key or the Jira token. |
| `exceptions.py` | Turns every upstream failure into one JSON error envelope, and scrubs secret-looking strings from logs. |
| `routers/` | One file per endpoint group: `meta`, `templates`, `run`, `comment`, `validate`. |

### `frontend/` — the web app

React with TypeScript, built by Vite, styled with Mantine. State is split by concern:

- **Server state** (templates, meta, run results) uses TanStack Query.
- **Local UI state** uses two small Zustand stores: one for the runner
  (`features/runner/store.ts`), one for credentials
  (`features/credentials/useCredentials.ts`).
- **API calls** go through a single typed `fetch` wrapper in `api/client.ts`, with
  endpoint functions in `api/endpoints.ts`.

Code is organized by feature (`features/runner`, `features/templates`,
`features/credentials`) rather than by file type.

## How a run flows through the system

This is the main path — the user clicks **Run** in the web app:

```
Browser (React)
  │  POST /api/run
  │  headers: X-Jira-Email, X-Jira-Token
  │  body:    { issue_key, instructions, template_id }
  ▼
FastAPI  backend/routers/run.py
  │  1. require_jira_credentials()  → pulls email/token from headers
  │  2. get_config()                → shared JIRA_BASE_URL + GROQ_API_KEY
  ▼
core.jira_client.get_issue(base_url, auth, issue_key)
  │  GET {base}/rest/api/3/issue/{key}
  │  returns summary + description (ADF flattened to text)
  ▼
core.groq_client.ask_groq(client, instructions, key, summary, description)
  │  chat completion: system = instructions, user = the ticket
  ▼
RunResponse { issue_key, summary, description, output, truncated, model }
  ▼
Browser renders the output; user can edit / copy / download / post
```

Posting back to Jira is a second, separate call (`POST /api/comment`) that the user
triggers with the **Post to Jira** button, or automatically right after a run if
they ticked the auto-post box.

## Why credentials travel in headers

The user's Jira email and token are sent as `X-Jira-Email` and `X-Jira-Token`
headers, never in the URL or JSON body. Two reasons:

1. They never enter a request model, so they can't be echoed back in a validation
   error or captured by accident.
2. Header values are covered by the log-redaction filter.

The backend uses them to build the auth tuple for that one request and then drops
them. Nothing is persisted server-side.

## Where the Groq key lives

Only on the server, in `GROQ_API_KEY`. It's used to build the Groq client for each
request and never appears on any response model. `/api/meta` deliberately returns
the model name and the public Jira URL but not the key. There is no `VITE_*`
variable for it, so it can't be baked into the browser bundle.

## Serving the SPA in production

In development the SPA runs on Vite (`:5173`) and proxies `/api` to FastAPI
(`:8000`), so the browser talks to one origin and CORS isn't needed.

In production, FastAPI serves both. `create_app()` mounts `frontend/dist` at `/`
using a small `SPAStaticFiles` subclass. That subclass adds the history fallback a
React app needs: a missing, extensionless, non-`/api` path returns `index.html`, so
deep links like `/runner/FMDEV-8888` work — but missing assets and unknown `/api/*`
paths still return a real 404 instead of HTML.

## Deployment shapes

The same app runs three ways:

- **Local single origin** — `uvicorn backend.main:create_app` serves the API and the
  built SPA together on one port.
- **Local dev, two servers** — Vite for the SPA, Uvicorn for the API, wired by the
  Vite proxy.
- **Vercel** — `vercel.json` builds the SPA and routes `/api/*` to `api/index.py`
  (which imports the same FastAPI app) and everything else to the static SPA.

See [setup and deployment](setup-and-deployment.md) for the commands.
