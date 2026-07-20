import { useState } from 'react';
import { Stack } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { ApiError } from '../../api/client';
import type { Credentials } from '../../api/types';
import { isValidEmail, isValidIssueKey, normalizeIssueKey } from '../../lib/validation';
import { CredentialsPanel } from '../credentials/CredentialsPanel';
import { useCredentials } from '../credentials/useCredentials';
import { TemplateGallery } from '../templates/TemplateGallery';
import { InstructionEditor } from './InstructionEditor';
import { IssueKeyField } from './IssueKeyField';
import { OutputPanel } from './OutputPanel';
import { RunBar } from './RunBar';
import { useRun, usePostComment } from './mutations';
import { useRunnerStore } from './store';

interface FieldErrors {
  issueKey?: string;
  instructions?: string;
  email?: string;
  token?: string;
  passphrase?: string;
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Unexpected error.';
}

export function RunnerPage() {
  const store = useRunnerStore();
  const creds = useCredentials();

  const run = useRun();
  const comment = usePostComment();

  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [runError, setRunError] = useState<string | null>(null);
  const [postedUrl, setPostedUrl] = useState<string | null | undefined>(undefined);

  const credentials: Credentials = { email: creds.email.trim(), token: creds.token };

  const postToJira = (issueKey: string, text: string, auto = false) => {
    setPostedUrl(undefined);
    comment.mutate(
      { body: { issue_key: issueKey, comment: text }, creds: credentials },
      {
        onSuccess: (result) => {
          setPostedUrl(result.comment_url ?? null);
          notifications.show({
            title: auto ? 'Generated and posted to Jira' : 'Posted to Jira',
            message: `Comment added to ${issueKey}.`,
            color: 'teal',
          });
        },
        onError: (error) => {
          notifications.show({ title: 'Could not post to Jira', message: messageFor(error), color: 'red' });
        },
      },
    );
  };

  const handleRun = () => {
    setRunError(null);
    setPostedUrl(undefined);

    const issueKey = normalizeIssueKey(store.issueKey);
    store.setIssueKey(issueKey);

    const errors: FieldErrors = {};
    if (!isValidIssueKey(issueKey)) errors.issueKey = 'Enter a valid Jira issue key, e.g. FMDEV-5448.';
    if (!store.instructions.trim())
      errors.instructions = "Instructions can't be empty - pick a template or write your own.";
    if (!isValidEmail(creds.email)) errors.email = 'Enter the email for your Atlassian account.';
    if (creds.locked && !creds.token) errors.token = 'Unlock your saved token first.';
    else if (!creds.token.trim()) errors.token = 'Enter your Jira API token.';
    if (creds.remember && creds.encrypt && !creds.passphrase.trim())
      errors.passphrase = 'Enter a passphrase before saving an encrypted token.';

    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    const shouldPost = store.postBack;
    run.mutate(
      {
        body: { issue_key: issueKey, instructions: store.instructions, template_id: store.selectedTemplateId },
        creds: credentials,
      },
      {
        onSuccess: (result) => {
          store.setOutput(result.output);
          void creds.persist();
          if (result.truncated) {
            notifications.show({
              title: 'Response may be truncated',
              message: 'The model hit its token limit.',
              color: 'yellow',
            });
          }
          // The checkbox behaves exactly like --comment: post the generated text as-is.
          if (shouldPost) postToJira(issueKey, result.output, true);
        },
        onError: (error) => setRunError(messageFor(error)),
      },
    );
  };

  return (
    <Stack gap="lg">
      <IssueKeyField error={fieldErrors.issueKey} />
      <TemplateGallery />
      <InstructionEditor error={fieldErrors.instructions} />
      <CredentialsPanel
        emailError={fieldErrors.email}
        tokenError={fieldErrors.token}
        passphraseError={fieldErrors.passphrase}
      />
      <RunBar
        onRun={handleRun}
        running={run.isPending}
        progressLabel="Fetching the ticket and generating the response..."
        errorMessage={runError}
      />
      {run.data && (
        <OutputPanel
          result={run.data}
          onPost={(text) => postToJira(run.data!.issue_key, text)}
          posting={comment.isPending}
          postedUrl={postedUrl}
        />
      )}
    </Stack>
  );
}
