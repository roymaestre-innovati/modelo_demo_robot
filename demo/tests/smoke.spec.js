import { test, expect } from '@playwright/test';

// Mismas comprobaciones para cada perfil; lo que cambia es la firma visual de la cara.
const MODELS = {
  robin: {
    label: 'Robin',
    minMeshes: 30,
    // ojos/boca de la pantalla: cian
    facePixel: (r, g, b) => r < 140 && g > 170 && b > 200,
    minFacePixels: 200,
  },
  ignis: {
    label: 'Ignis',
    minMeshes: 10,
    // esclerotica de los ojos: casi blanco (el fondo de Ignis es oscuro)
    facePixel: (r, g, b) => r > 225 && g > 225 && b > 220,
    minFacePixels: 200,
  },
};

/** Cuenta pixeles de la captura (60 % superior) que cumplen el predicado. */
async function countPixels(page, predicate) {
  const b64 = (await page.screenshot()).toString('base64');
  return page.evaluate(async ({ b64, fn }) => {
    const test = new Function(`return (${fn})`)();
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const off = document.createElement('canvas');
    off.width = img.width; off.height = img.height;
    const ctx = off.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const { data } = ctx.getImageData(0, 0, off.width, Math.floor(off.height * 0.6));
    let n = 0;
    for (let i = 0; i < data.length; i += 4) if (test(data[i], data[i + 1], data[i + 2])) n++;
    return n;
  }, { b64, fn: predicate.toString() });
}

for (const [id, cfg] of Object.entries(MODELS)) {
  test(`${cfg.label} carga, muestra la cara y completa el ciclo de "Hablar"`, async ({ page }) => {
    const errors = [];
    page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()));
    page.on('pageerror', (err) => errors.push(String(err)));

    await page.goto(id === 'robin' ? '/' : `/?model=${id}`);
    await page.waitForFunction(() => window.__robin?.ready === true, null, { timeout: 30_000 });

    const info = await page.evaluate(() => {
      const r = window.__robin;
      let meshes = 0;
      r.model.traverse((o) => o.isMesh && meshes++);
      return { clips: r.clips, faceTextureIsCanvas: r.faceTextureIsCanvas, meshes, state: r.state,
        profile: r.profile, alias: window.__demo === r, selected: document.getElementById('model').value };
    });
    expect(info.profile).toBe(id);
    expect(info.alias).toBe(true);
    expect(info.selected).toBe(id);
    expect(info.clips).toEqual(expect.arrayContaining(['idle', 'talk_1', 'talk_2', 'talk_3']));
    expect(info.faceTextureIsCanvas).toBe(true);
    expect(info.meshes).toBeGreaterThan(cfg.minMeshes);
    expect(info.state).toBe('idle');

    const fps = await page.evaluate(() => new Promise((res) => {
      let n = 0; const t0 = performance.now();
      const tick = () => (performance.now() - t0 < 1000 ? (n++, requestAnimationFrame(tick)) : res(n));
      requestAnimationFrame(tick);
    }));
    console.log(`${id}: fps headless ${fps}`);
    await page.screenshot({ path: `tests/output/${id}_idle.png` });
    expect(await countPixels(page, cfg.facePixel)).toBeGreaterThan(cfg.minFacePixels);

    // ciclo completo: listening -> thinking -> speaking -> idle
    await page.getByRole('button', { name: 'Hablar' }).click();
    await page.waitForFunction(() => window.__robin.state === 'listening');
    await page.waitForFunction(() => window.__robin.state === 'thinking', null, { timeout: 10_000 });
    await page.waitForFunction(() => window.__robin.state === 'speaking', null, { timeout: 10_000 });

    // Ignis: la mandibula se mueve durante el habla (se muestrea el angulo real del hueso)
    let maxJaw = 0;
    if (id === 'ignis') {
      maxJaw = await page.evaluate(() => new Promise((res) => {
        let m = 0; const t0 = performance.now();
        const tick = () => {
          m = Math.max(m, window.__robin.face.jawAngleDeg);
          performance.now() - t0 < 1500 ? requestAnimationFrame(tick) : res(m);
        };
        requestAnimationFrame(tick);
      }));
    } else {
      await page.waitForTimeout(1500);
    }
    await page.screenshot({ path: `tests/output/${id}_speaking.png` });
    await page.waitForFunction(() => window.__robin.state === 'idle', null, { timeout: 25_000 });

    const after = await page.evaluate(() => ({
      mouthChanges: window.__robin.face.mouthChanges,
      pending: window.__robin.visemes.queue.length,
      talks: window.__robin.body.talkHistory,
      mouth: window.__robin.face.mouth,
      eyes: window.__robin.face.eyes,
    }));
    expect(after.mouthChanges).toBeGreaterThan(fps >= 20 ? 30 : 8); // a pocos FPS varios visemas caen en un frame
    expect(after.pending).toBe(0);
    if (fps >= 20) expect(after.talks.length).toBeGreaterThanOrEqual(2); // ~8-10 s de habla: al menos 2 gestos
    for (let i = 1; i < after.talks.length; i++) expect(after.talks[i]).not.toBe(after.talks[i - 1]);
    expect(after.mouth).toBe('REST');
    expect(after.eyes).toBe('neutral');

    if (id === 'ignis') {
      expect(maxJaw).toBeGreaterThan(5);
      // tras el suavizado (~60 ms) la mandibula vuelve a reposo
      await page.waitForTimeout(500);
      const restJaw = await page.evaluate(() => window.__robin.face.jawAngleDeg);
      console.log(`ignis: Jaw max ${maxJaw.toFixed(1)}° durante el habla, ${restJaw.toFixed(2)}° en reposo`);
      expect(restJaw).toBeLessThan(0.5);
    }

    await page.keyboard.press('f');
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `tests/output/${id}_full.png` });

    expect(errors).toEqual([]);
  });
}
