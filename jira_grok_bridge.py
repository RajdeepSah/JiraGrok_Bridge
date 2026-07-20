"""
jira_grok_bridge.py - command-line interface.

Pulls a Jira ticket, sends it to a Groq model with a chosen set of instructions,
and returns the result - printed to the console, saved to a file, or posted back as
a Jira comment.

All the real work now lives in the framework-agnostic ``core`` package, which is
shared with the web app (backend/). This file is just the CLI on top of it. The
instructions are no longer a hardcoded constant: pick a stored template with
--template-id, or supply your own with --instructions.

Usage:
    python jira_grok_bridge.py ISSUE-123                      # improve ticket, print (default)
    python jira_grok_bridge.py ISSUE-123 --save              # save to ISSUE-123_output.txt
    python jira_grok_bridge.py ISSUE-123 --comment           # post back to the Jira ticket
    python jira_grok_bridge.py ISSUE-123 --template-id root-cause-analysis
    python jira_grok_bridge.py ISSUE-123 --instructions "Summarize in one line."
    python jira_grok_bridge.py ISSUE-123 --instructions @prompt.txt
    python jira_grok_bridge.py --list-templates

Shared settings (JIRA_BASE_URL, GROQ_API_KEY) and the per-user Jira credentials
(JIRA_EMAIL, JIRA_API_TOKEN) are read from the environment / a .env file.
"""

import argparse
import os
import sys
from pathlib import Path

import requests

# Re-export the core functions at module level. main() calls them as bare names, so
# tests can patch jira_grok_bridge.get_issue / .ask_groq / .post_comment, and the
# pure converters remain reachable as jira_grok_bridge.adf_to_text / .text_to_adf.
from core.config import load_config
from core.errors import ConfigError, TemplateNotFound
from core.groq_client import ask_groq, build_groq_client
from core.jira_client import adf_to_text, get_issue, post_comment, text_to_adf
from core.templates import get_template_store

__all__ = [
    "adf_to_text",
    "text_to_adf",
    "get_issue",
    "post_comment",
    "ask_groq",
    "build_groq_client",
    "resolve_instructions",
    "build_parser",
    "main",
]


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing {name} - set it in your environment or .env file.")
    return value


def resolve_instructions(args, store) -> str:
    """Pick the instructions (system prompt) for this run.

    Precedence: --instructions (inline or @file) > --template-id > default template.
    """
    if args.instructions is not None:
        text = args.instructions
        if text.startswith("@"):
            text = Path(text[1:]).read_text(encoding="utf-8")
        return text
    if args.template_id:
        return store.get(args.template_id).instructions
    return store.default().instructions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jira_grok_bridge.py",
        description="Send a Jira ticket to Groq with chosen instructions.",
        allow_abbrev=False,  # a typo like --coment must error, not match --comment
    )
    parser.add_argument("issue_key", nargs="?", help="Jira issue key, e.g. FMDEV-5448")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print", dest="mode", action="store_const", const="print",
                      help="print the result to the console (default)")
    mode.add_argument("--save", dest="mode", action="store_const", const="save",
                      help="save the result to ISSUE-KEY_output.txt")
    mode.add_argument("--comment", dest="mode", action="store_const", const="comment",
                      help="post the result back as a Jira comment")
    parser.set_defaults(mode="print")

    parser.add_argument("--template-id", help="id of a stored instruction template")
    parser.add_argument("--instructions", help="custom instructions inline, or @path to read from a file")
    parser.add_argument("--list-templates", action="store_true",
                        help="list available instruction templates and exit")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    store = get_template_store()

    if args.list_templates:
        for tpl in store.list():
            print(f"{tpl.id}\n    {tpl.name} - {tpl.description}")
        return

    if not args.issue_key:
        parser.error("the following arguments are required: issue_key")
    if args.issue_key.startswith("-"):
        parser.error(f"invalid issue key: {args.issue_key!r}")

    issue_key = args.issue_key

    try:
        cfg = load_config()
        auth = (require_env("JIRA_EMAIL"), require_env("JIRA_API_TOKEN"))
        instructions = resolve_instructions(args, store)

        print(f"Fetching {issue_key} from Jira...")
        issue = get_issue(cfg.jira_base_url, auth, issue_key)

        print("Sending to Groq...")
        client = build_groq_client(cfg.groq_api_key)
        result = ask_groq(
            client,
            instructions,
            issue_key,
            issue["summary"],
            issue["description"],
            model=cfg.groq_model,
            max_tokens=cfg.max_tokens,
        )
        if result.truncated:
            print("Warning: output was truncated (max_tokens reached).", file=sys.stderr)

        if args.mode == "comment":
            post_comment(cfg.jira_base_url, auth, issue_key, result.text)
            print(f"Posted as a comment on {issue_key}.")
        elif args.mode == "save":
            filename = f"{issue_key}_output.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(result.text)
            print(f"Saved to {filename}.")
        else:
            print("\n" + result.text)

    except ConfigError as e:
        sys.exit(str(e))
    except TemplateNotFound as e:
        sys.exit(str(e))
    except requests.exceptions.HTTPError as e:
        sys.exit(f"Jira request failed: {e}")
    except Exception as e:
        sys.exit(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
