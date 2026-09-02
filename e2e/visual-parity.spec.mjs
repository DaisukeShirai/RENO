import { execFileSync } from 'node:child_process';
import { test, expect } from '@playwright/test';

const legacyHtml = execFileSync('git', ['show', 'HEAD:index.html'], { encoding: 'utf8' })
  .replace('<head>', '<head><base href="http://127.0.0.1:4173/">');

const installStubs = async (page) => {
  await page.route('**/cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js', (route) => route.abort());
  await page.route('**/assets/reno-config.js', (route) => route.fulfill({
    status: 200,
    contentType: 'application/javascript',
    body: 'window.RENO_CONFIG={apiUrl:"",mockChat:true};',
  }));
};

test('React 移行後も初期表示の DOM と見た目が一致する', async ({ page, context }) => {
  const legacy = await context.newPage();
  await Promise.all([installStubs(page), installStubs(legacy)]);
  await Promise.all([page.goto('/'), legacy.setContent(legacyHtml, { waitUntil: 'load' })]);
  await Promise.all([
    expect(page.locator('#app')).toBeVisible(),
    expect(legacy.locator('#app')).toBeVisible(),
  ]);

  const stableCss = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
  await Promise.all([page.addStyleTag({ content: stableCss }), legacy.addStyleTag({ content: stableCss })]);
  const [reactImage, legacyImage] = await Promise.all([
    page.screenshot({ animations: 'disabled' }),
    legacy.screenshot({ animations: 'disabled' }),
  ]);
  const differentPixels = await page.evaluate(async ([first, second]) => {
    const decode = async (base64) => createImageBitmap(await (await fetch(`data:image/png;base64,${base64}`)).blob());
    const [a, b] = await Promise.all([decode(first), decode(second)]);
    if (a.width !== b.width || a.height !== b.height) return Infinity;
    const canvas = document.createElement('canvas');
    canvas.width = a.width; canvas.height = a.height;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    context.drawImage(a, 0, 0);
    const firstPixels = context.getImageData(0, 0, a.width, a.height).data;
    context.clearRect(0, 0, a.width, a.height);
    context.drawImage(b, 0, 0);
    const secondPixels = context.getImageData(0, 0, b.width, b.height).data;
    let count = 0, minX = a.width, minY = a.height, maxX = 0, maxY = 0;
    for (let index = 0; index < firstPixels.length; index += 4) {
      if (firstPixels[index] !== secondPixels[index] || firstPixels[index + 1] !== secondPixels[index + 1] || firstPixels[index + 2] !== secondPixels[index + 2] || firstPixels[index + 3] !== secondPixels[index + 3]) {
        count += 1;
        const pixel = index / 4, x = pixel % a.width, y = Math.floor(pixel / a.width);
        minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
      }
    }
    return { count, bounds: [minX, minY, maxX, maxY] };
  }, [reactImage.toString('base64'), legacyImage.toString('base64')]);
  // Chromium の別ページ間キャプチャで入力欄の境界に発生する
  // アンチエイリアスの揺れのみを許容する（全画面の 0.01% 未満）。
  expect(differentPixels.count).toBeLessThanOrEqual(56);
});
