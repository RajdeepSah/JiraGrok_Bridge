# Security

This tool handles two kinds of secret: the shared Groq key on the server, and each
user's personal Jira token. The design keeps them apart and keeps both out of places
they could leak. This page explains the model, what's protected, what isn't, and how
to deploy without undoing it.

## The threat model in one paragraph

Anyone who can reach the app can send Jira tickets to Groq using *their own* Jira
token, which is fine — that's the point. What we protect against is: the shared Groq
key leaking to users or into the bundle; one user's Jira token leaking to another
user or to logs; a crafted issue key reaching Jira endpoints it shouldn't; model or
ticket text executing in the browser; and the whole thing being exposed over plain
HTTP where tokens travel in the clear.

## What's protected, and how

### The Groq key stays server-side

It lives only in `GROQ_API_KEY` on the server. It's used to build the Groq client per
request and is never placed on a response model, so it can't be serialized back to a
client. `/api/meta` returns the model name and Jira URL but not the key. There is no
`VITE_*` variable for it, so it can never be compiled into the browser bundle. After
a build you can grep `frontend/dist` for `gsk_` to confirm — the check is in
[maintenance](maintenance.md#test-and-verify-a-deployment).

### Jira tokens live in headers and are never stored

Each user's Jira email and token arrive as `X-Jira-Email` / `X-Jira-Token` headers,
used to build the auth for that one request, then dropped. They are:

- **Never in a request body or URL** — so they can't be echoed in a validation error
  or logged as part of a path.
- **Never modeled in `schemas.py`** — there's deliberately no Pydantic field for them.
- **Never persisted** — the backend has no storage.

### Logs are redacted

`backend/exceptions.py` installs a logging filter on the root logger and Uvicorn's
loggers. It scrubs:

- Anything shaped like a Groq key (`gsk_...`).
- The full value of any `Authorization` or `X-Jira-*` header, whether rendered as a
  plain header line or inside a dict/JSON blob.

It's a safety net, not the primary defense — the primary defense is not logging
secrets in the first place. But if something does slip into a log line, this catches
the common shapes.

### Issue keys are validated and encoded

The issue key is validated server-side against `^[A-Za-z][A-Za-z0-9]+-\d+$` and
percent-encoded before it's placed in the Jira URL path. Together those stop a
crafted key from escaping `/issue/` and reaching other Jira REST endpoints.

### The Jira base URL is fixed server-side (SSRF protection)

The Jira origin comes from `JIRA_BASE_URL` on the server, never from the user. A user
can't point the backend at an arbitrary host, so the app can't be tricked into making
requests to internal services on their behalf.

### Output is rendered as escaped text

Ticket content and model output are rendered as normal React text — no
`dangerouslySetInnerHTML` anywhere. So a ticket or a model response containing
`<script>` or other markup is shown as characters, not executed.

### Comments are sent as structured ADF

Text posted back to Jira is wrapped in Atlassian Document Format as plain paragraphs,
not interpreted as markup, which keeps the round-trip predictable.

## What is *not* protected

Be honest about the edges:

- **Browser-side token encryption is at-rest only.** If a user opts to remember and
  encrypt their token, it's encrypted with a passphrase-derived key (PBKDF2, 210k
  iterations, AES-GCM) before going into `localStorage`. That protects against
  someone reading `localStorage` on a shared or stolen machine. It does **not**
  protect against XSS or a malicious script while the token is decrypted in memory.
  The passphrase is never stored.
- **No server-side authorization or rate limiting.** The backend doesn't know who you
  are beyond the Jira token you send. Anyone who can reach it can use it (with their
  own token). Put access control at the network or proxy layer if you need it.
- **The app trusts its own deployment.** There's no protection against a compromised
  server or a malicious admin who can read `GROQ_API_KEY`.

## Deploying safely

The code's protections only hold if the deployment doesn't undo them:

1. **Terminate TLS before exposing the app past loopback.** Keep Uvicorn on
   `127.0.0.1` and front it with Caddy, nginx, or Traefik. Every request carries a
   Jira token — plain HTTP on a LAN or the internet leaks it. (On Vercel, TLS is
   handled for you.)
2. **Send a Content Security Policy** from the proxy. A tight default:
   ```
   default-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
   ```
3. **Keep CORS off in production.** `JGB_DEV_CORS` is dev-only. Production is
   single-origin and needs no CORS.
4. **Never add a `VITE_*` secret.** It would end up in the bundle.
5. **Keep `.env` out of git.** It's gitignored; leave it that way.

## Token hygiene for users

- Use narrowly scoped, rotatable Jira API tokens.
- Revoke a token immediately if you suspect it's exposed, and create a new one.
- On a shared machine, either don't tick "remember," or use the encryption option and
  choose a real passphrase.
