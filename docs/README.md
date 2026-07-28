# Jira Grok Bridge — Documentation

This folder holds the working documentation for Jira Grok Bridge, the internal tool
that pulls a Jira ticket, runs it through a Groq model with a chosen instruction
template, and (optionally) posts the result back as a Jira comment.

The top-level [README](../README.md) is the quick start: prerequisites, install,
and how to run the app. The pages here go deeper and are aimed at whoever ends up
maintaining, deploying, or extending the tool.

## What's here

| Page | Read it when you want to |
| --- | --- |
| [Overview](overview.md) | Understand what the tool does and who uses it, in one page. |
| [Architecture](architecture.md) | See how the pieces fit together and follow a request end to end. |
| [Setup and deployment](setup-and-deployment.md) | Install locally, run in dev, build for production, or deploy to Vercel. |
| [Configuration](configuration.md) | Know every environment variable and how templates are stored. |
| [API reference](api-reference.md) | Call the backend directly, or debug what the frontend sends. |
| [CLI reference](cli.md) | Use the command-line version instead of the web app. |
| [Security](security.md) | Understand the threat model, what's protected, and how to deploy safely. |
| [Troubleshooting](troubleshooting.md) | Fix a specific error or behavior. |
| [Maintenance](maintenance.md) | Add templates, update dependencies, run tests, rotate keys, cut a release. |
| [Limitations and roadmap](limitations-and-roadmap.md) | Know the known gaps and what could come next. |

## A note on the name

Despite "Grok" in the name, the AI provider is [Groq](https://groq.com/), not the
Grok model. The name stuck from early on. If it ever causes confusion, renaming is
listed in the [roadmap](limitations-and-roadmap.md).
