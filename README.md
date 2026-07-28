# Jira Grok Bridge

Jira Grok Bridge turns Jira tickets into AI-generated content with Groq. Use the React web app to choose one of 12 instruction templates, edit the instruction, review and edit the generated result, and optionally post it back to Jira. The original command-line workflow remains available.

The project keeps the Jira/Groq integration in a shared `core/` package:

- `jira_grok_bridge.py` - argparse CLI
- `backend/` - FastAPI API and production SPA host
- `frontend/` - React, TypeScript, Vite, and Mantine SPA
- `core/` - framework-independent configuration, Jira/Groq clients, and templates

Despite the project name, the AI provider is the [Groq API](https://groq.com/), not the Grok model.

## Documentation

This README is the quick start. Deeper documentation for maintainers, users, and administrators lives in [docs/](docs/README.md):

- [Overview](docs/overview.md) and [Architecture](docs/architecture.md) — what it does and how the pieces fit.
- [Setup and deployment](docs/setup-and-deployment.md) — local, single-origin, and Vercel.
- [Configuration](docs/configuration.md), [API reference](docs/api-reference.md), and [CLI reference](docs/cli.md).
- [Security](docs/security.md), [Troubleshooting](docs/troubleshooting.md), [Maintenance](docs/maintenance.md), and [Limitations and roadmap](docs/limitations-and-roadmap.md).

## Features

- Fetch a Jira issue using the current user's Jira email and API token.
- Choose from 12 bundled templates or write a custom instruction.
- Preview the source ticket and edit, copy, or download the generated output.
- Post edited output manually, or auto-post the generated output after a run.
- Keep the shared Groq key on the server; it is never bundled into the SPA or returned by the API.
- Optionally remember Jira credentials in browser `localStorage`, with passphrase-based AES-GCM encryption for the token.
- Use the same core logic from the web app and CLI.

## Prerequisites

- Python 3.10 or newer
- Node.js LTS and npm
- A Groq API key
- A Jira Cloud account and [Atlassian API token](https://id.atlassian.com/manage-profile/security/api-tokens)

## Configuration

Copy the example file and fill in the required values:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux, use `cp .env.example .env`.

| Variable | Required for | Purpose |
| --- | --- | --- |
| `JIRA_BASE_URL` | Web and CLI | Fixed Jira site origin, such as `https://example.atlassian.net`; do not include `/browse/...` |
| `GROQ_API_KEY` | Web and CLI | Shared server-side Groq API key |
| `GROQ_MODEL` | Optional | Model override; defaults to `llama-3.3-70b-versatile` |
| `GROQ_MAX_TOKENS` | Optional | Output limit; defaults to `4096` |
| `JIRA_EMAIL` | CLI only | Jira email used by the command-line tool |
| `JIRA_API_TOKEN` | CLI only | Jira API token used by the command-line tool |
| `JGB_DEV_CORS` | Optional development mode | Set to `1` only when a separate client calls port 8000 directly instead of using the Vite proxy |

For the shared web server, configure only `JIRA_BASE_URL` and `GROQ_API_KEY` (plus optional model settings). Web users enter their own Jira credentials in the browser; the server uses them for that request and does not persist them.

Never name a browser environment variable `VITE_GROQ_API_KEY`, `VITE_JIRA_BASE_URL`, or similar. Vite embeds `VITE_*` values in client JavaScript. The `.env` file is gitignored and must not be committed.

## Install

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Set-Location frontend
npm ci
Set-Location ..
```

If you intentionally change frontend dependencies, use `npm install` to update `package-lock.json`, then commit both `package.json` and the lockfile.

## Run the web app in development

Start FastAPI from the repository root:

```powershell
python -m uvicorn backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to FastAPI on `127.0.0.1:8000`, so normal development does not require CORS configuration.

## Use the web app

1. Enter an issue key such as `FMDEV-8888`, or paste a Jira `/browse/ISSUE-123` URL; the UI extracts and normalizes the key.
2. View and select a template, or enter a custom instruction in the editor.
3. Enter your Jira email and API token.
4. Select **Run**. The generated result and source-ticket preview appear below the form.
5. Edit, copy, or download the output as needed.
6. Select **Post to Jira** to post the current edited output.

The **Post the generated response straight back to Jira** checkbox is different from the manual button: it posts the original generated output immediately after a successful run, like the CLI's `--comment` option.

Credential storage is optional. Remembered credentials are written only after a successful run. If encryption is enabled, a non-empty passphrase is required and is never stored. Unchecking **Remember** or selecting **Forget saved credentials** removes the stored entry and clears the in-memory token. Encryption protects the token at rest only; it does not protect against malicious scripts or theft while the token is unlocked.

## Build and run as a single-origin app

Build the SPA first:

```powershell
Set-Location frontend
npm ci
npm run typecheck
npm run build
Set-Location ..
```

Then start FastAPI, which serves both `/api/*` and `frontend/dist`:

```powershell
python -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Extensionless SPA routes fall back to `index.html`; missing assets and unknown `/api/*` paths still return 404.

For any shared or network deployment, keep Uvicorn bound to `127.0.0.1` and put a TLS-terminating reverse proxy such as Caddy, nginx, or Traefik in front of it. Every authenticated request carries a Jira token, so plain HTTP must not be used on a LAN or the internet.

A suitable proxy should also send a Content Security Policy similar to:

```text
default-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
```

## CLI usage

List the bundled templates:

```powershell
python jira_grok_bridge.py --list-templates
```

Run with the default `ticket-improvement` template and print the output:

```powershell
python jira_grok_bridge.py FMDEV-8888
python jira_grok_bridge.py FMDEV-8888 --print
```

Choose another template or provide custom instructions:

```powershell
python jira_grok_bridge.py FMDEV-8888 --template-id root-cause-analysis
python jira_grok_bridge.py FMDEV-8888 --instructions "Summarize this ticket in one paragraph."
python jira_grok_bridge.py FMDEV-8888 --instructions @prompt.txt
```

Save or post the result:

```powershell
python jira_grok_bridge.py FMDEV-8888 --save
python jira_grok_bridge.py FMDEV-8888 --comment
```

`--print`, `--save`, and `--comment` are mutually exclusive. Instruction precedence is `--instructions`, then `--template-id`, then the default `ticket-improvement` template. The `@prompt.txt` form reads UTF-8 instructions from a file.

## API

Interactive FastAPI documentation is available at `/docs` while the backend is running.

| Method | Path | Jira credential headers | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/health` | No | Liveness check |
| `GET` | `/api/meta` | No | Non-secret Jira URL, model, and configured status |
| `GET` | `/api/templates` | No | Template metadata |
| `GET` | `/api/templates/{id}` | No | Full template instruction |
| `POST` | `/api/run` | Yes | Fetch a Jira issue and generate output |
| `POST` | `/api/comment` | Yes | Post text to a Jira issue |
| `POST` | `/api/validate` | Yes | Validate credentials and optionally check an issue |

Authenticated endpoints expect `X-Jira-Email` and `X-Jira-Token`. Credentials must not be placed in URLs or JSON bodies. Errors use this envelope:

```json
{
  "error": {
    "code": "ISSUE_NOT_FOUND",
    "message": "That Jira issue was not found, or your account can't see it."
  }
}
```

## Add or edit templates

Templates live in `core/templates.json`. Append or edit an object containing `id`, `name`, `description`, and `instructions`; no Python or TypeScript change is required. IDs must be unique. `ticket-improvement` is the default and preserves the original CLI behavior.

## Test and verify

Run the Python/core/API suite from the repository root:

```powershell
python -m pytest -q
```

If pytest cannot use the Windows user temp directory because of local ACLs, use an ignored workspace-local path:

```powershell
python -m pytest -q --basetemp .pytest_cache\test-tmp
```

Check the frontend:

```powershell
Set-Location frontend
npm run typecheck
npm run build
Set-Location ..
```

Smoke-test the live backend:

```powershell
(Invoke-RestMethod http://127.0.0.1:8000/api/health).status
(Invoke-RestMethod http://127.0.0.1:8000/api/templates).Count
```

Expected results are `ok` and `12`. `/api/meta` should return the configured Jira site and model but never the Groq key.

After a production build, scan the bundle for secret-shaped values and your fixed Jira host; the command should return no matches:

```powershell
Get-ChildItem frontend/dist -Recurse -File |
  Select-String -SimpleMatch -CaseSensitive:$false -Pattern 'gsk_', 'firemon.atlassian.net'
```

The automated suite mocks Jira and Groq calls. A final live check requires valid credentials: run against a non-sensitive test ticket, review the generated output, then deliberately test manual post and auto-post because both create real Jira comments.

## Security notes

- Terminate TLS before exposing the app beyond loopback.
- Keep the Jira base URL server-fixed to prevent SSRF.
- Keep user Jira credentials in request headers only; the backend does not persist them.
- Keep the Groq key server-side and out of all `VITE_*` variables.
- Jira content and model output are rendered as escaped React text, without `dangerouslySetInnerHTML`.
- Logs redact Groq-key-shaped strings, authorization values, and all `X-Jira-*` header values.
- Browser-side passphrase encryption reduces at-rest exposure but is not a defense against XSS.
- Use narrowly scoped, rotatable Jira tokens and revoke them if exposure is suspected.
