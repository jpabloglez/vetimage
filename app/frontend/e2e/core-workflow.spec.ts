import path from 'path';
import { fileURLToPath } from 'url';
import { test, expect } from '@playwright/test';
import { login } from './helpers';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SAMPLE_DICOM = path.join(__dirname, 'fixtures', 'sample-cr.dcm');

// PatientName tag baked into the fixture — used to find this run's task/report
// among any left over from previous runs (the E2E DB is not reset per-run).
const FIXTURE_PATIENT = 'E2E^TestDog';

test.describe('Core workflow: upload -> analyze -> report', () => {
  test.setTimeout(120_000);

  test('runs the full loop through the real UI, backend, and reference AI service', async ({ page }) => {
    await login(page);

    await test.step('Upload a study and dispatch AI analysis', async () => {
      await page.goto('/analyze');
      await page.getByRole('button', { name: 'New Analysis' }).click();

      // DragDropUploadZone's file input is hidden but Playwright can still
      // target it directly; it's the first of two uploaders on this step.
      await page.locator('input[type="file"]').first().setInputFiles(SAMPLE_DICOM);

      await expect(page.getByRole('heading', { name: 'Recommended Model' })).toBeVisible({
        timeout: 20_000,
      });
      const selectButton = page.getByRole('button', { name: 'Select This Model' });
      await expect(selectButton).toBeEnabled();
      await selectButton.click();

      await expect(page.getByText(/Analysis submitted/i)).toBeVisible({ timeout: 10_000 });
    });

    await test.step('Wait for the real dispatch -> webhook -> COMPLETED lifecycle', async () => {
      await page.getByRole('button', { name: 'Worklist' }).click();
      const row = page.locator('tbody tr').first();
      const refreshButton = page.getByRole('button', { name: 'Refresh' });
      // The worklist has no auto-refresh/WebSocket — status only updates on
      // refetch, so poll by clicking Refresh (the Celery worker dispatches to
      // the live vet-thorax-service and the webhook flips status asynchronously).
      await expect(async () => {
        await refreshButton.click();
        await expect(row).toContainText('Completed');
      }).toPass({ timeout: 60_000, intervals: [1000, 2000, 3000] });
    });

    await test.step('Generate a report from the completed task', async () => {
      const row = page.locator('tbody tr').first();
      await row.getByRole('button', { name: 'Report' }).click();
      await expect(page.getByText(/Report created successfully/i)).toBeVisible({ timeout: 10_000 });
    });

    await test.step('The report appears on the Dashboard and opens the embedded viewer', async () => {
      await page.goto('/dashboard');
      const patientLink = page.getByRole('link', { name: FIXTURE_PATIENT }).first();
      await expect(patientLink).toBeVisible({ timeout: 15_000 });
      await patientLink.click();

      await expect(page).toHaveURL(/\/reports\/[\w-]+/);
      await expect(page.getByText('Patient Name')).toBeVisible();
      await expect(page.getByText(FIXTURE_PATIENT)).toBeVisible();

      // The PDF loads as an authenticated blob object URL, not a bare path.
      const iframe = page.locator('iframe');
      await expect(iframe).toHaveAttribute('src', /^blob:/, { timeout: 15_000 });
    });
  });
});
