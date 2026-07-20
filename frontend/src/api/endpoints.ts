import { request } from './client';
import type {
  CommentRequestBody,
  CommentResult,
  Credentials,
  MetaInfo,
  RunRequestBody,
  RunResult,
  TemplateDetail,
  TemplateSummary,
} from './types';

/** The user's Jira credentials travel as headers on every authenticated call.
 *  They are never put in the URL, query string, or a logged body. */
function credHeaders(creds: Credentials): Record<string, string> {
  return {
    'X-Jira-Email': creds.email,
    'X-Jira-Token': creds.token,
  };
}

export function getMeta(): Promise<MetaInfo> {
  return request<MetaInfo>('GET', '/api/meta');
}

export function getTemplates(): Promise<TemplateSummary[]> {
  return request<TemplateSummary[]>('GET', '/api/templates');
}

export function getTemplate(id: string): Promise<TemplateDetail> {
  return request<TemplateDetail>('GET', `/api/templates/${encodeURIComponent(id)}`);
}

export function runIssue(body: RunRequestBody, creds: Credentials): Promise<RunResult> {
  return request<RunResult>('POST', '/api/run', { body, headers: credHeaders(creds) });
}

export function postComment(body: CommentRequestBody, creds: Credentials): Promise<CommentResult> {
  return request<CommentResult>('POST', '/api/comment', { body, headers: credHeaders(creds), timeoutMs: 30000 });
}
