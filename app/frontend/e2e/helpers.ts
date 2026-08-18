import { Page, expect } from '@playwright/test';

export const E2E_EMAIL = 'e2e@vetimage.test';
export const E2E_PASSWORD = 'E2ePlaywright123!';

/** Log in through the real UI form and wait for the redirect off /auth/login. */
export async function login(page: Page, email = E2E_EMAIL, password = E2E_PASSWORD) {
  await page.goto('/auth/login');
  // Anchored regex, not an exact string: required fields render a literal
  // trailing "*" in the label text (e.g. "Password*"), not CSS content.
  await page.getByLabel(/^Email Address/i).fill(email);
  await page.getByLabel(/^Password/i).fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).not.toHaveURL(/\/auth\/login/, { timeout: 15_000 });
}
