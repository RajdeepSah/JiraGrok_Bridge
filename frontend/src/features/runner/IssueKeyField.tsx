import { Card, TextInput } from '@mantine/core';

import { normalizeIssueKey } from '../../lib/validation';
import { useRunnerStore } from './store';

interface Props {
  error?: string;
}

export function IssueKeyField({ error }: Props) {
  const issueKey = useRunnerStore((s) => s.issueKey);
  const setIssueKey = useRunnerStore((s) => s.setIssueKey);

  return (
    <Card withBorder radius="md" padding="lg">
      <TextInput
        label="Jira issue key"
        description="The ticket to work on. You can paste a Jira link and we'll extract the key."
        placeholder="FMDEV-5448"
        value={issueKey}
        error={error}
        onChange={(e) => setIssueKey(e.currentTarget.value)}
        onBlur={(e) => setIssueKey(normalizeIssueKey(e.currentTarget.value))}
      />
    </Card>
  );
}
