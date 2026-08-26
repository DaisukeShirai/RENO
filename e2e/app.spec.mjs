import { test, expect } from '@playwright/test';

test.describe('RENOローカル相談フロー', () => {
  test('PIN認証後にバックエンドAPIでチャットできる', async ({ page }) => {
    if (process.env.E2E_USE_REAL_API !== 'true') {
      await page.route('**/assets/reno-config.js', (route) => route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        body: 'window.RENO_CONFIG={apiUrl:"http://e2e.local/agent",mockChat:false,supabaseUrl:"https://e2e.supabase.co",supabaseAnonKey:"e2e-anon"};',
      }));
      const respond = async (route) => {
        const body = route.request().postDataJSON();
        if (body.type === 'verify_pin') {
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ token: 'e2e-token', role: 'guest' }) });
          return;
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          content: [{ type: 'text', text: 'ご相談内容を確認しました。現在の状態・ご希望の部屋・ご予算を教えてください。\n[SUGGESTIONS: 素材を探す, 概算を見る, 施工後イメージ]' }],
          usage: { count: 1, limit: 10, remaining: 9 },
        }) });
      };
      await page.route('**/agent', respond);
      await page.route('**/reno-agent', respond);
    }
    // E2E実行環境では外部CDNを使わず、Googleログイン部分だけをスタブ化する。
    await page.addInitScript(() => {
      window.supabase = {
        createClient: () => ({
          auth: {
            getSession: async () => ({ data: { session: null } }),
            signOut: async () => ({}),
            signInWithOAuth: async () => ({ data: {}, error: null }),
          },
        }),
      };
    });
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
    await expect(page.locator('#suggestions-row .chip')).toHaveCount(3);

    const summary = await page.evaluate(() => getPdfConversationSummary([
      { role: 'user', content: 'リビングを北欧風にしたいです' },
      { role: 'user', content: '予算は100〜200万円で考えています' },
    ]));
    expect(summary.room).toBe('リビング');
    expect(summary.style).toBe('北欧');
    expect(summary.budget).toBe('100〜200万円');

    const pdfState = await page.evaluate(async () => {
      let pages = 1;
      window.html2canvas = async () => ({ width: 794, height: 1123, toDataURL: () => 'data:image/jpeg;base64,local' });
      window.jspdf = { jsPDF: class {
        addImage() {}
        addPage() { pages += 1; }
        save() {}
      } };
      await generatePDF('', '', () => {});
      return { imageBlock: document.getElementById('pdf-images-block').style.display, pages };
    });
    expect(pdfState.imageBlock).toBe('none');
    expect(pdfState.pages).toBe(1);
  });
});
