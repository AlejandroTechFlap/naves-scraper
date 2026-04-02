/**
 * API key storage helpers.
 * Uses localStorage (private admin tool — no expiry needed).
 */

const STORAGE_KEY = "naves_api_key";

export function saveApiKey(key: string): void {
  localStorage.setItem(STORAGE_KEY, key);
}

export function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(STORAGE_KEY);
}

export function removeApiKey(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function isAuthenticated(): boolean {
  return !!getApiKey();
}
