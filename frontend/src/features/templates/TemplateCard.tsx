import { Badge, Button, Card, Group, Stack, Text } from '@mantine/core';

import type { TemplateSummary } from '../../api/types';

interface Props {
  template: TemplateSummary;
  selected: boolean;
  onView: () => void;
  onUse: () => void;
}

export function TemplateCard({ template, selected, onView, onUse }: Props) {
  return (
    <Card
      withBorder
      radius="md"
      padding="md"
      h="100%"
      style={{
        borderColor: selected ? 'var(--mantine-color-teal-filled)' : undefined,
        borderWidth: selected ? 2 : 1,
        backgroundColor: selected ? 'var(--mantine-color-teal-light)' : undefined,
        boxShadow: selected ? 'var(--mantine-shadow-sm)' : undefined,
        transition: 'border-color 150ms ease, background-color 150ms ease, box-shadow 150ms ease',
      }}
    >
      <Stack gap="xs" h="100%" justify="space-between">
        <Stack gap={4}>
          <Group justify="space-between" wrap="nowrap" align="flex-start">
            <Text fw={600}>{template.name}</Text>
            {selected && (
              <Badge size="sm" variant="light" color="teal">
                In Use
              </Badge>
            )}
          </Group>
          <Text size="sm" c="dimmed" lineClamp={3}>
            {template.description}
          </Text>
        </Stack>
        <Group gap="xs" mt="xs">
          <Button size="xs" variant="default" onClick={onView}>
            View details
          </Button>
          <Button size="xs" onClick={onUse}>
            Use template
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}
