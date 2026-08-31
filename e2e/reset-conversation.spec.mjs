import { test, expect } from '@playwright/test';
import { openApp } from './support/app-fixtures.mjs';

test.describe('会話リセット', () => {
  test('確認後に会話を初期状態へ戻し、キャンセル時は保持する', async ({ page }) => {
    await openApp(page);
    await expect(page.locator('#app')).toBeVisible({ timeout: 15_000 });

    const input = page.locator('#userInput');
    await input.fill('リビングのリフォームについて相談したいです');
    await page.locator('#sendBtn').click();
    await expect(page.locator('#chat .msg.user')).toHaveCount(1);
    await expect(page.locator('#chat .msg.agent').last()).toContainText('ご相談内容を確認しました', { timeout: 15_000 });

    const resetButton = page.locator('#chatResetBtn');
    await page.once('dialog', (dialog) => dialog.dismiss());
    await resetButton.click();
    await expect(page.locator('#chat .msg.user')).toHaveCount(1);

    await page.once('dialog', (dialog) => dialog.accept());
    await resetButton.click();
    await expect(page.locator('#chat .msg.user')).toHaveCount(0);
    await expect(page.locator('#chat .msg.agent')).toHaveCount(1);
    await expect(page.locator('#suggestions-row .chip')).toHaveCount(5);
    await expect.poll(async () => page.evaluate(() =>
      Object.keys(localStorage).filter((key) => key.startsWith('reno_chat_history_v1:'))
    )).toEqual([]);
  });
});
