/**
 * graceFetch — fetch wrapper with automatic timeout.
 * Drop-in replacement for fetch() that adds AbortSignal.timeout.
 *
 * Usage:
 *   import { graceFetch } from '../api/graceFetch';
 *   const res = await graceFetch('/api/health', { timeout: 5000 });
 */

const DEFAULT_TIMEOUT = 15000; // 15 seconds

export async function graceFetch(url, options = {}) {
  const { timeout = DEFAULT_TIMEOUT, ...fetchOptions } = options;

  // If caller already provided a signal, don't override it
  if (fetchOptions.signal) {
    return fetch(url, fetchOptions);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(`Request to ${url} timed out after ${timeout}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export default graceFetch;
