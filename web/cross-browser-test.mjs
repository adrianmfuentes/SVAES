import { chromium, firefox, webkit } from 'playwright';
import { mkdirSync } from 'fs';

const OUT = 'cross-browser-screenshots';
mkdirSync(OUT, { recursive: true });

const BASE = 'http://localhost:4200';

const browsers = [
  { name: 'chromium', launch: chromium },
  { name: 'firefox',  launch: firefox  },
  { name: 'webkit',   launch: webkit   },
];

for (const { name, launch } of browsers) {
  console.log(`\n=== ${name.toUpperCase()} ===`);
  const browser = await launch.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: 'light',
    reducedMotion: 'reduce', // triggers existing opacity:1 fallback for animated rows
  });
  const page = await ctx.newPage();

  // ── Landing page ──────────────────────────────────────────────
  await page.goto(BASE, { waitUntil: 'networkidle' });
  // Force any remaining animations to their end state
  await page.evaluate(() => document.getAnimations().forEach(a => { a.currentTime = 1e9; }));
  await page.screenshot({ path: `${OUT}/${name}-landing.png`, fullPage: false });

  const paper = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--paper').trim()
  );
  const ink = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--ink').trim()
  );
  const colorScheme = await page.evaluate(() =>
    getComputedStyle(document.documentElement).colorScheme
  );
  console.log(`  title:        ${await page.title()}`);
  console.log(`  --paper:      ${paper}`);
  console.log(`  --ink:        ${ink}`);
  console.log(`  color-scheme: ${colorScheme}`);

  // ── Auth/login page ────────────────────────────────────────────
  await page.goto(`${BASE}/auth/login`, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.getAnimations().forEach(a => { a.currentTime = 1e9; }));
  await page.screenshot({ path: `${OUT}/${name}-login.png`, fullPage: false });
  console.log(`  login: ${await page.title()} @ ${page.url()}`);

  // ── App dashboard (will redirect to auth — shows auth wall) ────
  await page.goto(`${BASE}/app/dashboard`, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.getAnimations().forEach(a => { a.currentTime = 1e9; }));
  await page.screenshot({ path: `${OUT}/${name}-dashboard.png`, fullPage: false });
  console.log(`  dashboard redirect: ${page.url()}`);

  await browser.close();
}

console.log('\n=== DONE — screenshots saved to cross-browser-screenshots/ ===');
