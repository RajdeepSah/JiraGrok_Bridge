# Limitations and roadmap

An honest list of what the tool doesn't do today, and ideas for later. None of these
are blockers for the current use — they're the edges to keep in mind and the obvious
next steps.

## Known limitations

### Only summary and description are sent

A run sends the ticket's summary and description to the model. Comments, attachments,
linked issues, custom fields, labels, and status are not included. For templates that
would benefit from history (say, root-cause analysis on a long thread), the model
only sees the two main fields.

### One issue at a time

There's no batch mode in the web app or the API. Each run is a single ticket. The CLI
can be scripted in a loop, but there's no built-in "run this template over a filter."

### The model can be wrong or truncated

Output is AI-generated. It can be confidently wrong, miss nuance, or hit the token
limit and get cut off (`truncated: true`). Templates push the model to reason only
from the ticket, but nothing enforces it. Treat every result as a draft to review,
especially before posting it back to a real ticket.

### No server-side auth or rate limiting

The backend authenticates you to *Jira* with your own token, but it has no notion of
app-level users, roles, or quotas. Anyone who can reach the endpoint can use it (with
their own Jira token). Access control has to come from the network or a reverse proxy.
There's no throttling, so a burst of runs can hit Groq or Jira rate limits.

### Browser encryption is at-rest only

The optional token encryption protects `localStorage` on a shared or stolen machine.
It does nothing against XSS while the token is decrypted in memory. See
[security](security.md#what-is-not-protected).

### No conversation or iteration

Each run is one shot: instructions plus ticket, one response. You can't follow up
with "make it shorter" in the same context — you edit the instructions and run again.

### Rich formatting is flattened

Jira's rich text (ADF) is flattened to plain text on the way in, and the response is
posted back as plain paragraphs. Tables, panels, and inline formatting from the
original ticket don't survive the round-trip as structure.

### Thin automated coverage on the frontend

The Python/API side has a real test suite. The frontend is covered by TypeScript
typechecking and the build, but there are no component or end-to-end tests yet.

## Possible future improvements

Roughly in order of how much they'd help versus how much work they are.

- **Include more ticket context** — optionally pull in comments, labels, or linked
  issues so history-dependent templates have more to work with.
- **Batch runs** — accept a JQL query or a list of keys and run a template across
  them, with results collected in one place.
- **Frontend tests** — add component tests (React Testing Library) and a smoke
  end-to-end test for the run flow.
- **App-level access control** — optional SSO or an allowlist in front of the API, so
  a deployment can be locked to the team without relying only on network placement.
- **Rate limiting / retries** — gentle backoff on Jira 429s and a per-user cap to
  keep one person from exhausting the shared Groq quota.
- **Preserve some formatting** — map common ADF structures (lists, code blocks) more
  faithfully in both directions instead of flattening everything.
- **Per-template model or token settings** — let a short template use a smaller limit
  and a heavy analysis template use a larger one.
- **Rename to match Groq** — the "Grok" in the name refers to Groq the provider, not
  the Grok model. A rename would remove a recurring point of confusion, at the cost of
  touching the repo name, imports, and docs.

## When you pick something up

Add the change in `core/` if it's logic both the CLI and web app should share, keep
the backend and frontend thin over it, and update the relevant page in `docs/`. The
[maintenance guide](maintenance.md) has the workflow.
