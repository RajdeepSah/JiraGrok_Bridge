import { API_BASE } from '../config/constants';

/** A typed error carrying the backend's error code (or a synthetic one for
 *  network/timeout failures). The message is already user-friendly. */
export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

interface RequestOptions {
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
}

/** Thin fetch wrapper: JSON in/out, typed errors, and a request timeout.
 *  Credentials, when present, are passed by callers as headers - never logged
 *  here and never placed in the URL. */
export async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const { body, headers = {}, timeoutMs = 60000 } = opts;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const text = await response.text();
    const data = text ? JSON.parse(text) : null;

    if (!response.ok) {
      const err = data?.error;
      throw new ApiError(
        err?.message ?? `Request failed (${response.status}).`,
        err?.code ?? `HTTP_${response.status}`,
        response.status,
      );
    }
    return data as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ApiError('The request timed out. Please try again.', 'TIMEOUT', 0);
    }
    throw new ApiError("Couldn't reach the server. Check your connection and retry.", 'NETWORK', 0);
  } finally {
    clearTimeout(timer);
  }
}
