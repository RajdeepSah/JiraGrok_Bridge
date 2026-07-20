export interface TemplateSummary {
  id: string;
  name: string;
  description: string;
}

export interface TemplateDetail extends TemplateSummary {
  instructions: string;
}

export interface Credentials {
  email: string;
  token: string;
}

export interface RunRequestBody {
  issue_key: string;
  instructions: string;
  template_id?: string | null;
}

export interface RunResult {
  issue_key: string;
  summary: string;
  description: string;
  output: string;
  truncated: boolean;
  model: string;
}

export interface CommentRequestBody {
  issue_key: string;
  comment: string;
}

export interface CommentResult {
  issue_key: string;
  posted: boolean;
  comment_url: string | null;
}

export interface MetaInfo {
  jira_base_url: string;
  model: string;
  configured: boolean;
}
