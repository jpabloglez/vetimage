/**
 * Client-side half of idle-session expiry.
 *
 * Two things have to hold, and both are easy to regress silently:
 *
 * 1. A poll on a timer must be marked as background, or the backend counts it
 *    as the user being present and an abandoned workstation stays signed in.
 * 2. A 401 that means "you went idle" must not be met with a token refresh.
 *    The refresh token is already blacklisted, so retrying turns one 401 into
 *    two and the user sees a generic failure instead of the real reason.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { apiClient, IDLE_TIMEOUT_CODE } from '../api';

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

const headersOf = (call: unknown[]) =>
  ((call[1] as RequestInit).headers ?? {}) as Record<string, string>;

describe('idle-session handling in the API client', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    apiClient.setAccessToken('test-access-token');
  });

  afterEach(() => {
    apiClient.setAccessToken(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('marks a background poll so it does not postpone the timeout', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ results: [] }));

    await apiClient.getNotifications({ background: true });

    expect(headersOf(fetchMock.mock.calls[0])['X-Background-Request']).toBe('1');
  });

  it('does not mark a request the user made', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ results: [] }));

    await apiClient.getNotifications();

    expect(headersOf(fetchMock.mock.calls[0])['X-Background-Request']).toBeUndefined();
  });

  it('gives up rather than refreshing when the session went idle', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: 'Signed out.', code: IDLE_TIMEOUT_CODE }, 401),
    );
    const listener = vi.fn();
    window.addEventListener('auth:session-idle', listener);

    await expect(apiClient.getNotifications()).rejects.toThrow(/inactivity/i);

    // One call: the original. A refresh attempt would be a second.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalled();
    expect(apiClient.getAccessToken()).toBeNull();

    window.removeEventListener('auth:session-idle', listener);
  });

  it('still refreshes on an ordinary expired-token 401', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ detail: 'Token expired' }, 401))
      .mockResolvedValueOnce(jsonResponse({ access: 'fresh-token' }))
      .mockResolvedValueOnce(jsonResponse({ results: [] }));

    await apiClient.getNotifications();

    // Original, refresh, retry — the fallback path must survive this change.
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
