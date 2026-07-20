import { create } from 'zustand';

import { CREDS_STORAGE_KEY } from '../../config/constants';
import { decryptString, encryptString, type EncryptedBlob } from './crypto';

interface StoredPlain {
  v: 1;
  remember: true;
  encrypted: false;
  email: string;
  token: string;
}
interface StoredEncrypted extends EncryptedBlob {
  v: 1;
  remember: true;
  encrypted: true;
  email: string;
}
type Stored = StoredPlain | StoredEncrypted;

interface CredentialsState {
  email: string;
  token: string;
  remember: boolean;
  encrypt: boolean;
  passphrase: string; // in-memory only; never persisted
  locked: boolean; // an encrypted token is stored but not yet decrypted this session
  hydrated: boolean;

  setEmail: (v: string) => void;
  setToken: (v: string) => void;
  setRemember: (v: boolean) => void;
  setEncrypt: (v: boolean) => void;
  setPassphrase: (v: string) => void;

  hydrate: () => void;
  unlock: () => Promise<void>;
  persist: () => Promise<void>;
  forget: () => void;
}

function readStored(): Stored | null {
  try {
    const raw = localStorage.getItem(CREDS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Stored) : null;
  } catch {
    return null;
  }
}

export const useCredentials = create<CredentialsState>((set, get) => ({
  email: '',
  token: '',
  remember: false,
  encrypt: false,
  passphrase: '',
  locked: false,
  hydrated: false,

  setEmail: (email) => set({ email }),
  setToken: (token) => set({ token }),
  setRemember: (remember) => {
    if (!remember) {
      try {
        localStorage.removeItem(CREDS_STORAGE_KEY);
      } catch {
        /* storage unavailable - ignore */
      }
      set({ token: '', remember: false, encrypt: false, passphrase: '', locked: false });
      return;
    }
    set({ remember: true });
  },
  setEncrypt: (encrypt) => set({ encrypt }),
  setPassphrase: (passphrase) => set({ passphrase }),

  hydrate: () => {
    if (get().hydrated) return;
    const data = readStored();
    if (!data) {
      set({ hydrated: true });
      return;
    }
    if (data.encrypted) {
      // Email + flags load immediately; the token stays locked until unlocked.
      set({ email: data.email ?? '', remember: true, encrypt: true, locked: true, hydrated: true });
    } else {
      set({ email: data.email ?? '', token: data.token ?? '', remember: true, encrypt: false, hydrated: true });
    }
  },

  unlock: async () => {
    const data = readStored();
    if (!data || !data.encrypted) return;
    const token = await decryptString(
      { salt: data.salt, iv: data.iv, ciphertext: data.ciphertext },
      get().passphrase,
    );
    set({ token, locked: false });
  },

  persist: async () => {
    const { remember, encrypt, email, token, passphrase } = get();
    if (!remember) {
      try {
        localStorage.removeItem(CREDS_STORAGE_KEY);
      } catch {
        /* storage unavailable - ignore */
      }
      return;
    }
    try {
      // Never silently fall back to plaintext when the user selected encryption.
      if (encrypt && !passphrase) return;
      if (encrypt) {
        const blob = await encryptString(token, passphrase);
        const stored: StoredEncrypted = { v: 1, remember: true, encrypted: true, email, ...blob };
        localStorage.setItem(CREDS_STORAGE_KEY, JSON.stringify(stored));
      } else {
        const stored: StoredPlain = { v: 1, remember: true, encrypted: false, email, token };
        localStorage.setItem(CREDS_STORAGE_KEY, JSON.stringify(stored));
      }
    } catch {
      /* storage unavailable - ignore */
    }
  },

  forget: () => {
    try {
      localStorage.removeItem(CREDS_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    set({ token: '', remember: false, encrypt: false, passphrase: '', locked: false });
  },
}));
