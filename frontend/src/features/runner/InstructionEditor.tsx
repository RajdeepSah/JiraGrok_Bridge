import { Badge, Card, Group, Stack, Text, Textarea, Title } from '@mantine/core';

import { MAX_INSTRUCTIONS } from '../../config/constants';
import { useRunnerStore } from './store';

interface Props {
  error?: string;
}

export function InstructionEditor({ error }: Props) {
  const instructions = useRunnerStore((s) => s.instructions);
  const setInstructions = useRunnerStore((s) => s.setInstructions);
  const selectedTemplateName = useRunnerStore((s) => s.selectedTemplateName);
  const baseline = useRunnerStore((s) => s.instructionsBaseline);

  const modified = selectedTemplateName != null && instructions !== baseline;

  return (
    <Card withBorder radius="md" padding="lg">
      <Stack gap="xs">
        <Group justify="space-between" align="center">
          <Title order={4}>Custom instruction</Title>
          <Group gap="xs">
            {selectedTemplateName && (
              <Badge variant="light">{selectedTemplateName}</Badge>
            )}
            {modified && (
              <Badge variant="light" color="orange">
                Modified
              </Badge>
            )}
          </Group>
        </Group>
        <Text size="sm" c="dimmed">
          This exact text is sent to the model as its instructions. Load a template above, or write your own.
        </Text>
        <Textarea
          autosize
          minRows={8}
          maxRows={20}
          maxLength={MAX_INSTRUCTIONS}
          placeholder="Describe what the model should do with the ticket..."
          value={instructions}
          error={error}
          onChange={(e) => setInstructions(e.currentTarget.value)}
        />
        <Text size="xs" c="dimmed" ta="right">
          {instructions.length.toLocaleString()} / {MAX_INSTRUCTIONS.toLocaleString()}
        </Text>
      </Stack>
    </Card>
  );
}
