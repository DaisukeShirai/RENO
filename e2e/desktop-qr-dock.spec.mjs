import { test, expect } from '@playwright/test';
import { installAppStubs } from './support/app-fixtures.mjs';

test('PC表示時だけスマホで開くQRコードを常駐表示する', async ({ page }) => {
  await installAppStubs(page);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('/');
  await expect(page.locator('#app')).toBeVisible();

  const dock = page.locator('#desktopQrDock');
  await expect(dock).toBeVisible();
  await expect(dock).toContainText('スマホで開く');
  await expect(dock.locator('img')).toBeVisible();

  await page.setViewportSize({ width: 1023, height: 800 });
  await expect(dock).toBeHidden();
});
