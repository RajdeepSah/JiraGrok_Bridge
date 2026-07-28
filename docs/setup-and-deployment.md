# Setup and deployment

All commands assume you start from the repository root. The examples use PowerShell,
since that's the primary shell on the dev machines. On macOS or Linux, swap
`Copy-Item` for `cp`, `Set-Location` for `cd`, and activate the venv with
`source .venv/bin/activate`.

## Prerequisites

- Python 3.10 or newer
- Node.js LTS and npm
- A Groq API key
- A Jira Cloud account and an
  [Atlassian API token](https://id.atlassian.com/manage-profile/security/api-tokens)

## 1. Configure

Copy the example env file and fill it in:

```powershell
Copy-Item .env.example .env
```

For a shared web deployment you only need two values:

```
JIRA_BASE_URL=https://firemon.atlassian.net
GROQ_API_KEY=your-groq-api-key
```

The [configuration page](configuration.md) explains every variable, including the
optional model overrides and the CLI-only Jira credentials. `.env` is gitignored;
never commit it.

## 2. Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Set-Location frontend
npm ci
Set-Location ..
```

Use `npm ci` for a clean install from the lockfile. Only run `npm install` when you
deliberately change frontend dependencies, and commit both `package.json` and the
updated `package-lock.json`.

## 3. Run in development

Two terminals. First, the API:

```powershell
python -m uvicorn backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Then the SPA:

```powershell
Set-Location frontend
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to FastAPI on `127.0.0.1:8000`, so
you don't need CORS for normal development.

If you run a client that calls port 8000 directly (instead of through the Vite
proxy), set `JGB_DEV_CORS=1` before starting Uvicorn. Leave it unset otherwise.

## 4. Build and run as a single-origin app

This is the production shape when you're not using Vercel: FastAPI serves the API and
the built SPA on one port.

Build the SPA:

```powershell
Set-Location frontend
npm ci
npm run typecheck
npm run build
Set-Location ..
```

Start FastAPI (note: no `--reload` in production):

```powershell
python -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. The app serves `/api/*` and everything in
`frontend/dist`. Extensionless SPA routes fall back to `index.html`; missing assets
and unknown `/api/*` paths still return 404.

### Put a reverse proxy in front

For anything beyond localhost — a shared box, a LAN, the internet — keep Uvicorn
bound to `127.0.0.1` and put a TLS-terminating reverse proxy (Caddy, nginx, Traefik)
in front of it. Every authenticated request carries a Jira token, so plain HTTP must
never be used off the loopback interface.

The proxy should also send a Content Security Policy. A good starting point:

```
default-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
```

See [security](security.md) for the full reasoning.

## 5. Deploy to Vercel

The repo is already set up for Vercel through `vercel.json`:

- **Build:** `cd frontend && npm ci && npm run build`, output in `frontend/dist`.
- **Routing:** `/api/*` goes to `api/index.py` (the FastAPI app via Python runtime);
  everything else serves the static SPA, with a rewrite to `/index.html` for
  client-side routes.

To deploy:

1. Connect the GitHub repo to a Vercel project.
2. Set the environment variables in the Vercel project settings — at minimum
   `JIRA_BASE_URL` and `GROQ_API_KEY`, plus `GROQ_MODEL` / `GROQ_MAX_TOKENS` if you
   want to override them. Do **not** commit these; set them in the dashboard.
3. Push to the connected branch, or run `vercel` / `vercel --prod` from the CLI.

Vercel terminates TLS for you, so the loopback + reverse-proxy advice above is for
self-hosting, not Vercel.

## Verify it's working

Once the backend is up:

```powershell
(Invoke-RestMethod http://127.0.0.1:8000/api/health).status      # -> ok
(Invoke-RestMethod http://127.0.0.1:8000/api/templates).Count    # -> 12
```

`/api/meta` should return the configured Jira site and model, and never the Groq
key. After a production build, confirm no secrets leaked into the bundle:

```powershell
Get-ChildItem frontend/dist -Recurse -File |
  Select-String -SimpleMatch -CaseSensitive:$false -Pattern 'gsk_', 'firemon.atlassian.net'
```

That command should return nothing. More checks are in [maintenance](maintenance.md#test-and-verify-a-deployment).
