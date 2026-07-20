import { Alert, Button, Checkbox, Group, Loader, Stack, Text } from '@mantine/core';
import { IconAlertTriangle, IconPlayerPlay } from '@tabler/icons-react';

import { useRunnerStore } from './store';

interface Props {
  onRun: () => void;
  running: boolean;
  progressLabel?: string;
  errorMessage?: string | null;
}

export function RunBar({ onRun, running, progressLabel, errorMessage }: Props) {
  const postBack = useRunnerStore((s) => s.postBack);
  const setPostBack = useRunnerStore((s) => s.setPostBack);

  return (
    <Stack gap="sm">
      <Checkbox
        label="Post the generated response straight back to Jira as a comment (like the --comment flag)"
        checked={postBack}
        onChange={(e) => setPostBack(e.currentTarget.checked)}
      />

      <Group>
        <Button
          size="md"
          leftSection={<IconPlayerPlay size={18} />}
          loading={running}
          onClick={onRun}
        >
          Run
        </Button>
        {running && progressLabel && (
          <Group gap="xs">
            <Loader size="sm" />
            <Text size="sm" c="dimmed">
              {progressLabel}
            </Text>
          </Group>
        )}
      </Group>

      {errorMessage && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} title="Something went wrong">
          {errorMessage}
        </Alert>
      )}
    </Stack>
  );
}
