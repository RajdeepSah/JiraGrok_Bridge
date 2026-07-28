# CLI reference

The command-line version (`jira_grok_bridge.py`) does the same job as the web app
from a terminal. It's handy for scripting or quick one-off runs. It shares all the
core logic with the backend, so templates behave identically.

## Setup

The CLI reads both the shared settings *and* the Jira credentials from the
environment or `.env`, because there's no browser to collect them:

```
JIRA_BASE_URL=https://firemon.atlassian.net
GROQ_API_KEY=your-groq-api-key
JIRA_EMAIL=you@firemon.com
JIRA_API_TOKEN=your-jira-api-token
```

Create the token at
<https://id.atlassian.com/manage-profile/security/api-tokens>. See
[configuration](configuration.md) for the optional model variables.

## Basic usage

```powershell
# List the available templates
python jira_grok_bridge.py --list-templates

# Improve a ticket with the default template and print it (default mode)
python jira_grok_bridge.py FMDEV-8888
python jira_grok_bridge.py FMDEV-8888 --print

# Use a specific template
python jira_grok_bridge.py FMDEV-8888 --template-id root-cause-analysis

# Custom instructions, inline or from a file
python jira_grok_bridge.py FMDEV-8888 --instructions "Summarize this ticket in one paragraph."
python jira_grok_bridge.py FMDEV-8888 --instructions @prompt.txt

# Save to ISSUE-KEY_output.txt, or post back as a comment
python jira_grok_bridge.py FMDEV-8888 --save
python jira_grok_bridge.py FMDEV-8888 --comment
```

## Arguments

| Argument | Meaning |
| --- | --- |
| `issue_key` | The Jira issue, e.g. `FMDEV-8888`. Required unless you pass `--list-templates`. |
| `--print` | Print the result to the console. This is the default. |
| `--save` | Save the result to `ISSUE-KEY_output.txt`. |
| `--comment` | Post the result back as a Jira comment. |
| `--template-id ID` | Use a stored template by id. |
| `--instructions TEXT` | Use custom instructions. `@path` reads them from a UTF-8 file. |
| `--list-templates` | Print the templates and exit. |

`--print`, `--save`, and `--comment` are mutually exclusive.

## Instruction precedence

When more than one source is given, the CLI picks in this order:

1. `--instructions` (inline text, or `@file`)
2. `--template-id`
3. The default `ticket-improvement` template

So `--instructions` always wins over `--template-id`, which mirrors how the web app
sends edited instructions rather than a bare template id.

## Behavior notes

- The tool prints progress as it goes: `Fetching {key} from Jira...` then
  `Sending to Groq...`.
- If the model hits its token limit, it prints a truncation warning to stderr but
  still returns what it got.
- `--comment` posts a real comment on a real ticket. Test against a throwaway ticket
  first.
- Abbreviated flags are rejected on purpose (`allow_abbrev=False`), so a typo like
  `--coment` errors instead of quietly matching `--comment`.

## Exit behavior

The CLI exits with a short message on the common failure paths rather than a stack
trace: missing config, unknown template, a Jira HTTP error, or any other unexpected
error. Anything deeper is a bug worth reporting.
