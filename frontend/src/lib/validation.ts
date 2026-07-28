import { ISSUE_KEY_RE } from '../config/constants';

/** Accept a raw issue key or a pasted Jira URL and return the bare, upper-cased key.
 *  e.g. "https://x.atlassian.net/browse/fmdev-8888" -> "FMDEV-8888". */
export function normalizeIssueKey(raw: string): string {
  const trimmed = raw.trim();
  const match = trimmed.match(/([A-Za-z][A-Za-z0-9]+-\d+)/);
  return (match ? match[1] : trimmed).toUpperCase();
}

export function isValidIssueKey(key: string): boolean {
  return ISSUE_KEY_RE.test(key);
}

export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}
