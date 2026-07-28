# Overview

## What it does

Jira Grok Bridge takes a Jira ticket and turns it into AI-generated content. You
give it an issue key, pick an instruction template (or write your own), and it:

1. Fetches the ticket's summary and description from Jira.
2. Sends both to a Groq model, using your chosen instructions as the system prompt.
3. Shows you the result, which you can edit, copy, download, or post back to the
   ticket as a comment.

There are twelve built-in templates for common jobs: cleaning up a ticket,
root-cause analysis, generating test plans and cases, writing acceptance criteria,
executive summaries, and so on. See [configuration](configuration.md#templates) for
the full list.

## Who uses it

It's an internal FireMon tool, meant for engineers, QA, and other people who work
Jira tickets day to day. Two audiences, two ways in:

- **Most people** use the web app. They open the page, paste a ticket key, pick a
  template, enter their own Jira credentials, and run it.
- **A few people** use the command-line version for scripting or one-off runs from
  a terminal.

Both share the same core logic, so a template or a fix applies to both.

## The two ways to run it

| | Web app | CLI |
| --- | --- | --- |
| Who it's for | Everyone | Scripts, power users |
| Jira credentials | Entered per user in the browser | Read from `.env` or the environment |
| Groq key | Lives on the server only | Lives on the machine running the CLI |
| Templates | Picked from a gallery | Chosen with `--template-id` |
| Output | Edit, copy, download, post | Print, save to file, or post |

## What makes it a shared tool, not a personal script

The original version was a single script that read one person's credentials at
import time and had one hardcoded prompt. The current version splits shared,
server-side settings (the Jira site URL and the Groq key) from per-user Jira
credentials, so a single deployment can serve a whole team. Each person brings
their own Jira token; the server never stores it. The Groq key stays on the server
and is never sent to the browser.

That split is the main design idea. The rest of the [architecture](architecture.md)
follows from it.
