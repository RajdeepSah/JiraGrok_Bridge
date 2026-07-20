// Same-origin API. In dev, Vite proxies /api -> FastAPI (see vite.config.ts).
// Intentionally NOT a VITE_* variable: nothing secret is ever baked into the bundle.
export const API_BASE = '';

// Official Atlassian page where a user creates a Jira API token.
export const ATLASSIAN_TOKEN_URL = 'https://id.atlassian.com/manage-profile/security/api-tokens';

// Mirror of the server-side issue-key rule (backend.schemas.ISSUE_KEY_PATTERN).
export const ISSUE_KEY_RE = /^[A-Za-z][A-Za-z0-9]+-\d+$/;

// localStorage key for remembered credentials (versioned for future migrations).
export const CREDS_STORAGE_KEY = 'jgb.creds.v1';

// Match the backend's instruction length cap so we validate before sending.
export const MAX_INSTRUCTIONS = 20000;
