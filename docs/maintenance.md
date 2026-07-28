# Maintenance

Day-to-day upkeep: adding templates, updating dependencies, running the tests,
rotating keys, and shipping a change. None of it is heavy — the project is small on
purpose.

## Add or edit a template

Templates are data, so this is usually the most common change and it needs no code.

1. Open `core/templates.json`.
2. Add or edit an object with `id`, `name`, `description`, and `instructions`. Keep
   `id` unique. See [configuration](configuration.md#templates) for what each field
   does.
3. Write `instructions` as a system prompt. The house style for the built-ins:
   set the role, tell the model to reason only from the ticket, tell it to preserve
   technical details exactly, and specify the exact output format.
4. Verify it loaded:
   ```powershell
   python jira_grok_bridge.py --list-templates
   (Invoke-RestMethod http://127.0.0.1:8000/api/templates).Count
   ```
   The count should go up by one, and the new id should appear in the list. The store
   validates the file on load, so a missing field or duplicate id fails immediately
   with a clear message.
5. Run the tests — one of them asserts the template count, so bump the expected number
   if you added or removed a template (see below).

## Run the tests

Python / core / API suite, from the repo root:

```powershell
python -m pytest -q
```

If pytest can't use the Windows user temp directory (local ACLs), point it at an
ignored workspace path:

```powershell
python -m pytest -q --basetemp .pytest_cache\test-tmp
```

The suite mocks Jira and Groq — no real network calls, no real credentials. It covers
the happy path for each endpoint, error mapping (auth, not-found, etc.), that
`/api/meta` never leaks the key, the SPA fallback behavior, and the log-redaction
filter. A couple of tests hardcode the template count (`12`) and an example issue key
— if you change either, update the tests.

Frontend checks:

```powershell
Set-Location frontend
npm run typecheck
npm run build
Set-Location ..
```

`typecheck` runs `tsc --noEmit` over both the app and the Vite config. There's no
frontend unit-test suite yet — see [roadmap](limitations-and-roadmap.md).

## Test and verify a deployment

After a production build, confirm no secrets ended up in the bundle:

```powershell
Get-ChildItem frontend/dist -Recurse -File |
  Select-String -SimpleMatch -CaseSensitive:$false -Pattern 'gsk_', 'firemon.atlassian.net'
```

That should return nothing. Then smoke-test the live backend:

```powershell
(Invoke-RestMethod http://127.0.0.1:8000/api/health).status      # -> ok
(Invoke-RestMethod http://127.0.0.1:8000/api/templates).Count    # -> 12
```

The automated suite never touches real Jira or Groq. Before trusting a release, do
one live run with real credentials against a non-sensitive test ticket, and
deliberately exercise both **manual post** and **auto-post**, because each creates a
real Jira comment.

## Update dependencies

**Python** — versions are pinned in `requirements.txt`. To upgrade, bump a pin,
reinstall, and run the tests:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

Watch `fastapi`, `pydantic`, and `groq` in particular — a major bump in any of them
can change behavior. The Groq SDK version also determines which models are available.

**Frontend** — change `package.json`, run `npm install` to refresh
`package-lock.json`, then `npm run typecheck && npm run build`. Commit both
`package.json` and the lockfile. For a clean install that respects the lockfile
exactly, use `npm ci`.

## Rotate the Groq key

1. Create a new key in the Groq console.
2. Update `GROQ_API_KEY` where it's set — `.env` locally, or the Vercel project
   settings.
3. On Vercel, redeploy so the new value is picked up. Self-hosted, the config is
   re-read on the next request, but restart if you want to be certain.
4. Revoke the old key.

Because the key is only ever server-side, rotating it doesn't touch users or the
bundle.

## Change the model

Set `GROQ_MODEL` to any model Groq currently serves. The UI reads it from
`/api/meta`, so it updates without a rebuild. If you pick a model with a different
context or output limit, revisit `GROQ_MAX_TOKENS`. If Groq retires the configured
model, runs fail with `GROQ_UPSTREAM` until you point it at a current one.

## Making a change (the short version)

1. Branch off `main`.
2. Make the change. Keep `core/` framework-independent — no FastAPI or React imports
   in there.
3. Run `python -m pytest -q` and, for frontend changes, `npm run typecheck && npm run
   build`.
4. If you touched the API surface, update [api-reference.md](api-reference.md); if you
   added config, update [configuration.md](configuration.md).
5. Open a PR against `main`.

## Repository layout recap

```
core/          shared logic (no framework imports) — the heart of the tool
backend/       FastAPI API + production SPA host
frontend/      React SPA
api/index.py   Vercel entrypoint (imports the FastAPI app)
jira_grok_bridge.py   CLI
requirements.txt      pinned Python deps
vercel.json           Vercel build + routing
docs/          this documentation
```

The guiding rule when extending: business logic goes in `core/` so both the CLI and
the web app get it; the backend and frontend stay thin over that core.
