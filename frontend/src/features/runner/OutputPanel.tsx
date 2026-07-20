import {
  Accordion,
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  CopyButton,
  Group,
  Stack,
  Text,
  Textarea,
  Title,
} from '@mantine/core';
import { IconAlertTriangle, IconBrandJira, IconCheck, IconCopy, IconDownload } from '@tabler/icons-react';

import type { RunResult } from '../../api/types';
import { useRunnerStore } from './store';

interface Props {
  result: RunResult;
  onPost: (text: string) => void;
  posting: boolean;
  postedUrl: string | null | undefined;
}

export function OutputPanel({ result, onPost, posting, postedUrl }: Props) {
  const output = useRunnerStore((s) => s.output);
  const editOutput = useRunnerStore((s) => s.editOutput);

  const download = () => {
    const blob = new Blob([output], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${result.issue_key}_output.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card withBorder radius="md" padding="lg">
      <Stack gap="sm">
        <Group justify="space-between" align="center">
          <Title order={4}>Generated response</Title>
          <Badge variant="light" color="gray">
            {result.model}
          </Badge>
        </Group>

        <Accordion variant="contained">
          <Accordion.Item value="source">
            <Accordion.Control>Source ticket: {result.issue_key}</Accordion.Control>
            <Accordion.Panel>
              <Text fw={600} size="sm">
                {result.summary || '(no summary)'}
              </Text>
              <Text size="sm" c="dimmed" style={{ whiteSpace: 'pre-wrap' }} mt={4}>
                {result.description || '(no description)'}
              </Text>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>

        {result.truncated && (
          <Alert color="yellow" icon={<IconAlertTriangle size={18} />}>
            The response hit the model's token limit and may be cut off. Consider a shorter instruction.
          </Alert>
        )}

        <Textarea
          autosize
          minRows={10}
          maxRows={30}
          value={output}
          onChange={(e) => editOutput(e.currentTarget.value)}
        />

        <Group justify="space-between">
          <Group gap="xs">
            <Button
              leftSection={<IconBrandJira size={18} />}
              loading={posting}
              onClick={() => onPost(output)}
            >
              Post to Jira
            </Button>
            <CopyButton value={output}>
              {({ copied, copy }) => (
                <Button
                  variant="default"
                  leftSection={copied ? <IconCheck size={18} /> : <IconCopy size={18} />}
                  onClick={copy}
                >
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              )}
            </CopyButton>
            <Button variant="default" leftSection={<IconDownload size={18} />} onClick={download}>
              Download
            </Button>
          </Group>
        </Group>

        {postedUrl !== undefined && postedUrl !== null && (
          <Alert color="teal" icon={<IconCheck size={18} />} title="Posted to Jira">
            <Anchor href={postedUrl} target="_blank" rel="noopener noreferrer">
              View the comment on {result.issue_key}
            </Anchor>
          </Alert>
        )}
      </Stack>
    </Card>
  );
}
