import { useState } from 'react';
import {
  Alert,
  Anchor,
  Button,
  Card,
  Checkbox,
  Collapse,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconChevronDown, IconChevronUp, IconLock, IconInfoCircle } from '@tabler/icons-react';

import { ATLASSIAN_TOKEN_URL } from '../../config/constants';
import { useCredentials } from './useCredentials';

interface Props {
  emailError?: string;
  tokenError?: string;
  passphraseError?: string;
}

export function CredentialsPanel({ emailError, tokenError, passphraseError }: Props) {
  const [expanded, setExpanded] = useState(true);
  const {
    email,
    token,
    remember,
    encrypt,
    passphrase,
    locked,
    setEmail,
    setToken,
    setRemember,
    setEncrypt,
    setPassphrase,
    unlock,
    forget,
  } = useCredentials();

  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  const handleUnlock = async () => {
    setUnlocking(true);
    setUnlockError(null);
    try {
      await unlock();
    } catch {
      setUnlockError('Incorrect passphrase.');
    } finally {
      setUnlocking(false);
    }
  };

  return (
    <Card withBorder radius="md" padding="lg">
      <Stack gap="sm">
        <Group justify="space-between" align="center">
          <Title order={4}>Your Jira Credentials</Title>
          <Button
            variant="subtle"
            size="xs"
            rightSection={expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
            aria-expanded={expanded}
            aria-controls="jira-credentials-content"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? 'Collapse' : 'Expand'}
          </Button>
        </Group>

        <Collapse in={expanded} id="jira-credentials-content">
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              These stay in your browser and are sent only to this app to talk to Jira on your behalf. They are
              never stored on the server.
            </Text>

            <TextInput
              label="Jira email"
              description="The email address of your Atlassian account."
              placeholder="you@firemon.com"
              value={email}
              error={emailError}
              onChange={(e) => setEmail(e.currentTarget.value)}
            />

            <PasswordInput
              label="Jira API token"
              description="Used with your email as Jira Cloud basic auth. Treat it like a password."
              placeholder={locked ? 'Locked - enter your passphrase below to load it' : 'Paste your Jira API token'}
              value={token}
              error={tokenError}
              disabled={locked}
              onChange={(e) => setToken(e.currentTarget.value)}
            />

            <Text size="xs" c="dimmed">
              Don&apos;t have a Jira API token?{' '}
              <Anchor href={ATLASSIAN_TOKEN_URL} target="_blank" rel="noopener noreferrer">
                Create one here
              </Anchor>
              .
            </Text>

            <Checkbox
              label="Remember my credentials on this device"
              checked={remember}
              onChange={(e) => setRemember(e.currentTarget.checked)}
            />

            {remember && (
              <Checkbox
                label="Encrypt the saved token with a passphrase"
                checked={encrypt}
                onChange={(e) => setEncrypt(e.currentTarget.checked)}
              />
            )}

            {remember && encrypt && !locked && (
              <PasswordInput
                label="Passphrase"
                description="Encrypts the token at rest. It is never stored - you'll re-enter it next session."
                placeholder="Choose a passphrase"
                value={passphrase}
                error={passphraseError}
                onChange={(e) => setPassphrase(e.currentTarget.value)}
              />
            )}

            {locked && (
              <Alert variant="light" color="yellow" icon={<IconLock size={18} />} title="Saved token is locked">
                <Stack gap="xs">
                  <Text size="sm">Enter your passphrase to load the token you saved earlier.</Text>
                  <PasswordInput
                    placeholder="Passphrase"
                    value={passphrase}
                    error={unlockError ?? undefined}
                    onChange={(e) => setPassphrase(e.currentTarget.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleUnlock();
                    }}
                  />
                  <Group>
                    <Button size="xs" loading={unlocking} onClick={handleUnlock}>
                      Unlock
                    </Button>
                    <Button size="xs" variant="subtle" color="red" onClick={forget}>
                      Forget saved credentials
                    </Button>
                  </Group>
                </Stack>
              </Alert>
            )}

            {remember && !locked && (
              <Group justify="space-between">
                <Text size="xs" c="dimmed">
                  <IconInfoCircle size={12} style={{ verticalAlign: 'middle' }} /> Saved in this browser only.
                  Encryption protects it at rest, not against malicious scripts on this page.
                </Text>
                <Button size="xs" variant="subtle" color="red" onClick={forget}>
                  Forget saved credentials
                </Button>
              </Group>
            )}
          </Stack>
        </Collapse>
      </Stack>
    </Card>
  );
}
