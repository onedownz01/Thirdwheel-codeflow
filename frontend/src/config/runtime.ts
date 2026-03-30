const rawApiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || '';
const rawWsBase = (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim() || '';

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

function deriveWsBaseFromApiBase(apiBase: string): string | null {
  if (!apiBase) return null;
  if (apiBase.startsWith('http://')) {
    return `ws://${apiBase.slice('http://'.length)}`;
  }
  if (apiBase.startsWith('https://')) {
    return `wss://${apiBase.slice('https://'.length)}`;
  }
  return null;
}

function deriveBrowserWsBase(): string {
  if (typeof window === 'undefined') {
    return 'ws://127.0.0.1:8001';
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
}

export const API_BASE = rawApiBase ? stripTrailingSlash(rawApiBase) : '';

export const WS_BASE = rawWsBase
  ? stripTrailingSlash(rawWsBase)
  : stripTrailingSlash(deriveWsBaseFromApiBase(API_BASE) || deriveBrowserWsBase());
