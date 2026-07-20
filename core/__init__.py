"""
core - framework-agnostic business logic shared by the CLI (jira_grok_bridge.py)
and the FastAPI backend (backend/).

Nothing in this package reads environment variables or builds network clients at
import time; credentials and the LLM instructions are always passed in as arguments.
That is what lets the same code serve a single-user CLI and a multi-user web app.
"""
