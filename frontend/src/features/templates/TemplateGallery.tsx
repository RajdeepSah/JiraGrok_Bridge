import { useState } from 'react';
import { Alert, Button, Center, Collapse, Group, Loader, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconChevronDown, IconChevronUp } from '@tabler/icons-react';

import { getTemplate } from '../../api/endpoints';
import type { TemplateDetail } from '../../api/types';
import { useRunnerStore } from '../runner/store';
import { TemplateCard } from './TemplateCard';
import { TemplateDetailModal } from './TemplateDetailModal';
import { useTemplates } from './useTemplates';

export function TemplateGallery() {
  const [expanded, setExpanded] = useState(true);
  const { data: templates, isLoading, error } = useTemplates();
  const selectedTemplateId = useRunnerStore((s) => s.selectedTemplateId);
  const detailTemplateId = useRunnerStore((s) => s.detailTemplateId);
  const openDetail = useRunnerStore((s) => s.openDetail);
  const closeDetail = useRunnerStore((s) => s.closeDetail);
  const useTemplate = useRunnerStore((s) => s.useTemplate);

  const applyDetail = (template: TemplateDetail) => {
    useTemplate(template.id, template.name, template.instructions);
    notifications.show({ message: `Loaded "${template.name}" into the editor.`, color: 'teal' });
  };

  // A card only has summary data, so fetch the full template before applying it.
  const applyById = async (id: string, name: string) => {
    try {
      const detail = await getTemplate(id);
      applyDetail(detail);
    } catch (e) {
      notifications.show({
        title: `Couldn't load "${name}"`,
        message: e instanceof Error ? e.message : 'Unknown error.',
        color: 'red',
      });
    }
  };

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="center">
        <Title order={3}>Instruction Templates</Title>
        <Button
          variant="subtle"
          size="xs"
          rightSection={expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
          aria-expanded={expanded}
          aria-controls="instruction-templates-content"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? 'Collapse' : 'Expand'}
        </Button>
      </Group>

      <Collapse in={expanded} id="instruction-templates-content">
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            Pick a starting point. View the full instruction, then load it into the editor to use or tweak.
          </Text>

          {isLoading && (
            <Center py="xl">
              <Loader />
            </Center>
          )}

          {error && (
            <Alert color="red" title="Couldn't load templates">
              {error instanceof Error ? error.message : 'Unknown error.'}
            </Alert>
          )}

          {templates && (
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
              {templates.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  selected={template.id === selectedTemplateId}
                  onView={() => openDetail(template.id)}
                  onUse={() => applyById(template.id, template.name)}
                />
              ))}
            </SimpleGrid>
          )}
        </Stack>
      </Collapse>

      <TemplateDetailModal
        templateId={detailTemplateId}
        onClose={closeDetail}
        onUse={(detail) => {
          applyDetail(detail);
          closeDetail();
        }}
      />
    </Stack>
  );
}
