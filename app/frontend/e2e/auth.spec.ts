import { test, expect } from '@playwright/test';
import { login, E2E_EMAIL, E2E_PASSWORD } from './helpers';

test.describe('Authentication', () => {
  test('logs in with valid credentials and reaches an authenticated page', async ({ page }) => {
    await login(page, E2E_EMAIL, E2E_PASSWORD);
    // Successful login navigates to /models (LoginPage's onSubmit) and the
    // navbar switches to the authenticated nav set.
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
  });

  test('rejects invalid credentials with an error and stays on the login page', async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByLabel(/^Email Address/i).fill(E2E_EMAIL);
    await page.getByLabel(/^Password/i).fill('wrong-password');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Backend returns DRF's SimpleJWT default detail message, which the
    // toast surfaces verbatim (see utils/api.ts login()'s errorData.message fallback).
    await expect(page.getByText(/no active account found/i)).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test('navigating to a protected page while logged out redirects to login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/auth\/login/);
  });
});
