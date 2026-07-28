# Troubleshooting

Start by finding your symptom below. Most problems are configuration or credentials,
not bugs.

## The app or the page

### "Server not configured" banner in the web app

The server is missing `JIRA_BASE_URL` or `GROQ_API_KEY`. Set both (in `.env`
locally, or the Vercel project settings) and reload. You can confirm with
`GET /api/meta` — it returns `configured: false` until both are present. No restart
is needed for the config to be re-read on the next request.

### The page loads but `/api` calls fail in development

You're probably running only one server. Dev needs two: Uvicorn on `:8000` and Vite
on `:5173`. The Vite proxy forwards `/api` to Uvicorn, so both have to be up. If you
call `:8000` directly from a separate client, set `JGB_DEV_CORS=1` before starting
Uvicorn.

### A deep link like `/runner/FMDEV-8888` 404s in production

Make sure you built the SPA (`npm run build`) and that FastAPI can see
`frontend/dist`. The history fallback only kicks in for extensionless, non-`/api`
paths. If `frontend/dist` is missing, FastAPI doesn't mount the SPA at all and every
non-API path 404s.

## Credentials and Jira

### `JIRA_AUTH` / "Jira rejected your email or API token"

Either the email/token pair is wrong, or the account can't see that issue. Check:

- The email is the Atlassian account email, and the token is a current API token
  (not your password), created at
  <https://id.atlassian.com/manage-profile/security/api-tokens>.
- The token hasn't been revoked or expired.
- Your account actually has access to the project the issue is in.

Use `POST /api/validate` to test credentials on their own before a full run.

### `ISSUE_NOT_FOUND` / "That Jira issue was not found"

The key doesn't exist, or your account can't see it. Double-check the project prefix
and number. Note the app normalizes what you paste — a full `/browse/ISSUE-123` URL
or lower-case key is fine — but the underlying issue still has to be visible to you.

### `MISSING_CREDENTIALS`

The `X-Jira-Email` / `X-Jira-Token` headers didn't arrive. In the web app, fill in
both credential fields. If a saved encrypted token is locked, unlock it with your
passphrase first — a locked token isn't sent.

### `JIRA_RATE_LIMIT`

Jira is throttling. Wait a moment and retry. There's no automatic backoff.

### `JIRA_TIMEOUT` / `JIRA_UNREACHABLE`

Network or Jira-side trouble. Check that `JIRA_BASE_URL` is the correct site origin
(no `/browse/...` path, no typo) and that the server can reach Jira.

## The generated output

### The output looks cut off / "Response may be truncated"

The model hit its token limit. `truncated` came back `true`. Raise `GROQ_MAX_TOKENS`,
or ask for something shorter (for example the executive-summary template), or shorten
a very long ticket description.

### `GROQ_UPSTREAM` / "The AI service returned an error"

Groq itself returned an error. The upstream message is deliberately not forwarded to
the client, so check the server logs for detail. Common causes: an invalid or
out-of-quota `GROQ_API_KEY`, or a `GROQ_MODEL` name that Groq no longer serves. Verify
the key works and the model is current.

### The output ignores part of my edited instructions

It shouldn't — `/api/run` always generates from the `instructions` you send, not from
the stored template. If an edit seems ignored, confirm the editor actually holds your
change before running, and remember the model is probabilistic: the same prompt can
give slightly different results.

## Saving and posting

### The saved credentials won't unlock

The passphrase is wrong — decryption fails with "Incorrect passphrase." The
passphrase is never stored and can't be recovered. If you've forgotten it, choose
**Forget saved credentials**, then re-enter the token and save again with a new
passphrase.

### "Post to Jira" vs. the auto-post checkbox behave differently

They're different on purpose:

- **Post to Jira** (the button) posts whatever is currently in the output editor,
  including your edits.
- **Post the generated response straight back to Jira** (the checkbox) posts the
  *original* generated output right after a successful run, before you've edited it —
  the same as the CLI's `--comment`.

## Tests and build

### pytest can't use the temp directory on Windows

Local ACLs sometimes block the default temp path. Use a workspace-local one:

```powershell
python -m pytest -q --basetemp .pytest_cache\test-tmp
```

### `npm ci` fails or the lockfile is out of sync

Use `npm ci` for a clean install from the committed lockfile. If you intentionally
changed dependencies, run `npm install` to update `package-lock.json`, then commit
both `package.json` and the lockfile.

## Still stuck

Check the server logs first — unexpected errors are logged in full there (with
secrets redacted) while the client only gets a generic `INTERNAL_ERROR`. The
[API reference](api-reference.md#errors) lists every error code and what triggers it.
