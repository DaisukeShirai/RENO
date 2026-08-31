import { test, expect } from '@playwright/test';

const installStubs = async (page) => {
  // 比較テストでは外部CDNの状態に左右されないようSupabaseを固定する。
  await page.route('**/cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js', (route) => route.abort());
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
  const respond = async (route) => {
    const body = route.request().postDataJSON();
    const response = body.type === 'verify_pin' || body.type === 'demo_login'
      ? { token: 'parity-token', role: 'guest' }
      : body.type === 'get_usage'
        ? { plan: 'standard', count: 0, limit: 10, remaining: 10, unlimited: false }
      : { content: [{ type: 'text', text: 'ご相談内容を確認しました。\n[SUGGESTIONS: 素材を探す, 概算を見る, 施工後イメージ]' }] };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(response) });
  };
  await page.route('**/agent', respond);
  await page.route('**/reno-agent', respond);
};

test('React版が現行index.htmlと同じDOM・表示になる', async ({ page, context }) => {
  const legacy = await context.newPage();
  await Promise.all([installStubs(page), installStubs(legacy)]);

  await Promise.all([
    page.goto('http://127.0.0.1:4173/'),
    legacy.goto('http://127.0.0.1:4174/'),
  ]);
  await Promise.all([
    expect(page.locator('#app')).toBeVisible({ timeout: 15_000 }),
    expect(legacy.locator('#app')).toBeVisible({ timeout: 15_000 }),
  ]);

  const stableCss = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
  await Promise.all([page.addStyleTag({ content: stableCss }), legacy.addStyleTag({ content: stableCss })]);

  const [reactApp, legacyApp] = await Promise.all([
    page.locator('#app').evaluate((element) => element.outerHTML),
    legacy.locator('#app').evaluate((element) => element.outerHTML),
  ]);
  expect(reactApp).toBe(legacyApp);

  const [reactImage, legacyImage] = await Promise.all([
    page.screenshot({ animations: 'disabled' }),
    legacy.screenshot({ animations: 'disabled' }),
  ]);
  expect(reactImage.equals(legacyImage)).toBe(true);
});
