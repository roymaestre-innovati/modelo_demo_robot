import { test, expect } from '@playwright/test';

test('Robin carga, muestra la cara y completa el ciclo de "Hablar"', async ({ page }) => {
  const errors = [];
  page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()));
  page.on('pageerror', (err) => errors.push(String(err)));

  await page.goto('/');
  await page.waitForFunction(() => window.__robin?.ready === true, null, { timeout: 30_000 });

  const info = await page.evaluate(() => {
    const r = window.__robin;
    let meshes = 0;
    r.model.traverse((o) => o.isMesh && meshes++);
    return { clips: r.clips, faceTextureIsCanvas: r.faceTextureIsCanvas, meshes, state: r.state };
  });
  expect(info.clips).toEqual(expect.arrayContaining(['idle', 'talk_1', 'talk_2', 'talk_3']));
  expect(info.faceTextureIsCanvas).toBe(true);
  expect(info.meshes).toBeGreaterThan(30);
  expect(info.state).toBe('idle');

  const fps = await page.evaluate(() => new Promise((res) => {
    let n = 0; const t0 = performance.now();
    const tick = () => (performance.now() - t0 < 1000 ? (n++, requestAnimationFrame(tick)) : res(n));
    requestAnimationFrame(tick);
  }));
  console.log(`fps headless: ${fps}`);
  await page.screenshot({ path: 'tests/output/robin_idle.png' });

  // pixeles de la captura: debe haber cian (ojos/boca de la pantalla)
  const shot = (await page.screenshot()).toString('base64');
  const cyan = await page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const off = document.createElement('canvas');
    off.width = img.width; off.height = img.height;
    const ctx = off.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const { data } = ctx.getImageData(0, 0, off.width, Math.floor(off.height * 0.6));
    let n = 0;
    for (let i = 0; i < data.length; i += 4) if (data[i] < 140 && data[i + 1] > 170 && data[i + 2] > 200) n++;
    return n;
  }, shot);
  expect(cyan).toBeGreaterThan(200);

  // ciclo completo: listening -> thinking -> speaking -> idle
  await page.getByRole('button', { name: 'Hablar' }).click();
  await page.waitForFunction(() => window.__robin.state === 'listening');
  await page.waitForFunction(() => window.__robin.state === 'thinking', null, { timeout: 10_000 });
  await page.waitForFunction(() => window.__robin.state === 'speaking', null, { timeout: 10_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'tests/output/robin_speaking.png' });
  await page.waitForFunction(() => window.__robin.state === 'idle', null, { timeout: 20_000 });

  const after = await page.evaluate(() => ({
    mouthChanges: window.__robin.face.mouthChanges,
    pending: window.__robin.visemes.queue.length,
    talks: window.__robin.body.talkHistory,
    mouth: window.__robin.face.mouth,
    eyes: window.__robin.face.eyes,
  }));
  expect(after.mouthChanges).toBeGreaterThan(fps >= 20 ? 30 : 8); // a pocos FPS varios visemas caen en un frame
  expect(after.pending).toBe(0);
  if (fps >= 20) expect(after.talks.length).toBeGreaterThanOrEqual(2); // ~8 s de habla: al menos 2 gestos
  for (let i = 1; i < after.talks.length; i++) expect(after.talks[i]).not.toBe(after.talks[i - 1]);
  expect(after.mouth).toBe('REST');
  expect(after.eyes).toBe('neutral');

  await page.keyboard.press('f');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: 'tests/output/robin_full.png' });

  expect(errors).toEqual([]);
});
