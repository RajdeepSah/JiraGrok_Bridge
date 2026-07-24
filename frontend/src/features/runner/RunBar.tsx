import { Alert, Button, Group, Loader, Stack, Text } from '@mantine/core';
import { IconAlertTriangle, IconPlayerPlay } from '@tabler/icons-react';

interface Props {
  onRun: () => void;
  running: boolean;
  progressLabel?: string;
  errorMessage?: string | null;
}

export function RunBar({ onRun, running, progressLabel, errorMessage }: Props) {
  return (
    <Stack gap="sm">
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
