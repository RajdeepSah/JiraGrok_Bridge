import { useEffect } from 'react';
import {
  ActionIcon,
  Alert,
  Anchor,
  Box,
  Container,
  Group,
  Stack,
  Text,
  Title,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from '@mantine/core';
import { IconAlertTriangle, IconMoon, IconSun } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';

import { getMeta } from './api/endpoints';
import { useCredentials } from './features/credentials/useCredentials';
import { RunnerPage } from './features/runner/RunnerPage';

function ColorSchemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const computed = useComputedColorScheme('light', { getInitialValueInEffect: true });
  const toggle = () => setColorScheme(computed === 'dark' ? 'light' : 'dark');
  return (
    <Tooltip label={computed === 'dark' ? 'Light mode' : 'Dark mode'}>
      <ActionIcon variant="default" size="lg" aria-label="Toggle color scheme" onClick={toggle}>
        {computed === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
      </ActionIcon>
    </Tooltip>
  );
}

export default function App() {
  const hydrate = useCredentials((s) => s.hydrate);
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const meta = useQuery({ queryKey: ['meta'], queryFn: getMeta });

  return (
    <Box mih="100vh">
      <Box
        component="header"
        py="md"
        px="lg"
        style={{ borderBottom: '1px solid var(--mantine-color-default-border)' }}
      >
        <Group justify="space-between" wrap="nowrap">
          <div>
            <Title order={2}>Jira Bridge</Title>
            <Text size="sm" c="dimmed">
              Turn a Jira ticket into AI-generated content, then post it back.
              {meta.data?.model ? ` Model: ${meta.data.model}.` : ''}
              {' '}
              <Anchor
                href="https://console.groq.com/docs/legal/services-agreement"
                target="_blank"
                rel="noopener noreferrer"
              >
                Learn more
              </Anchor>
            </Text>
          </div>
          <ColorSchemeToggle />
        </Group>
      </Box>

      <Container size="md" py="xl">
        <Stack gap="lg">
          {meta.data && !meta.data.configured && (
            <Alert color="red" icon={<IconAlertTriangle size={18} />} title="Server not configured">
              The server is missing its shared Jira URL or AI service key. Ask the administrator to configure
              them before running.
            </Alert>
          )}
          <RunnerPage />
        </Stack>
      </Container>
    </Box>
  );
}
