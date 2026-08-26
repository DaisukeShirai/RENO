import { test, expect } from '@playwright/test';

test.describe('RENOローカル相談フロー', () => {
  test('PIN認証後にバックエンドAPIでチャットできる', async ({ page }) => {
    const pin = process.env.E2E_PIN || '5678';
    await page.goto(`/?pin=${pin}`);

    await expect(page.locator('#pinScreen')).toBeHidden({ timeout: 15_000 });
    await expect(page.locator('#app')).toBeVisible();

    const input = page.locator('#userInput');
    await expect(input).toBeVisible();
    await input.fill('リビングのリフォームについて相談したいです');
    await page.locator('#sendBtn').click();

    await expect(page.locator('#chat .msg.user')).toContainText('リビング', { timeout: 5_000 });
    await expect(page.locator('#chat .msg.agent').last()).toContainText('ご相談内容を確認しました', { timeout: 15_000 });
  });
});
