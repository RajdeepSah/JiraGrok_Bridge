import { Alert, Button, Code, Group, Loader, Modal, ScrollArea, Text } from '@mantine/core';

import type { TemplateDetail } from '../../api/types';
import { useTemplateDetail } from './useTemplates';

interface Props {
  templateId: string | null;
  onClose: () => void;
  onUse: (template: TemplateDetail) => void;
}

export function TemplateDetailModal({ templateId, onClose, onUse }: Props) {
  const { data, isLoading, error } = useTemplateDetail(templateId);

  return (
    <Modal opened={templateId != null} onClose={onClose} title={data?.name ?? 'Template details'} size="lg">
      {isLoading && <Loader />}
      {error && (
        <Alert color="red" title="Couldn't load template">
          {error instanceof Error ? error.message : 'Unknown error.'}
        </Alert>
      )}
      {data && (
        <>
          <Text size="sm" c="dimmed" mb="sm">
            {data.description}
          </Text>
          <ScrollArea.Autosize mah={360} type="auto">
            <Code block style={{ whiteSpace: 'pre-wrap' }}>
              {data.instructions}
            </Code>
          </ScrollArea.Autosize>
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Close
            </Button>
            <Button onClick={() => onUse(data)}>Use this template</Button>
          </Group>
        </>
      )}
    </Modal>
  );
}
