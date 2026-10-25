/** F010 responsive/focus checks against the built application and isolated HTTP fixtures. */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { openSettings, closeSettings, showWorkspaceView } from './workspace-actions.mjs';
const ru = JSON.parse(
  await readFile(
    new URL('../src/lib/i18n/locales/ru-RU/translation.json', import.meta.url),
    'utf8',
  ),
);
const sizes = [
  [1920, 1080],
  [1366, 768],
  [1280, 605],
  [1024, 600],
  [640, 360],
];
export async function runWorkspaceAccessibilityChecks(browser, origin) {
  let checks = 0;
  for (const [width, height] of sizes) {
    const context = await browser.newContext({
      viewport: { width, height },
      deviceScaleFactor: width === 640 ? 2 : 1,
      locale: 'ru-RU',
    });
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/*', (route) => {
      const api = new URL(route.request().url()).pathname;
      const json = (data) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) });
      if (api === '/auth/session')
        return json({
          user: {
            id: 'layout',
            system_role: 'user',
            display_name: 'Длинное имя пользователя '.repeat(5),
          },
          csrf_token: 'csrf',
        });
      if (api === '/projects')
        return json({ items: [{ id: 'p', name: 'Название проекта '.repeat(10), code: 'CODE' }] });
      if (api === '/llm/connection')
        return json({
          source: 'server',
          base_url: 'https://example.test/v1',
          has_api_key: true,
          selected_model_id: 'a',
        });
      if (api === '/models')
        return json({
          models: [{ id: 'a', name: 'Модель с длинным названием '.repeat(8) }],
          selected_model_id: 'a',
          selection_required: false,
        });
      if (api === '/chat')
        return route.fulfill({
          contentType: 'text/event-stream',
          body: 'event: delta\ndata: {"text":"Completed answer"}\n\nevent: citations\ndata: {"citations":[]}\n\nevent: completed\ndata: {}\n\n',
        });
      return route.continue();
    });
    async function bounds() {
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        true,
        `horizontal overflow ${width}`,
      );
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight + 1),
        true,
        `root overflow ${height}`,
      );
    }
    async function visibleFocus() {
      assert.equal(
        await page.evaluate(() => {
          const focused = document.activeElement;
          // Theme radios expose their focus ring and hit target on the label.
          const e = focused?.matches('input[type=radio]') ? focused.closest('label') : focused;
          if (!e || e === document.body) return false;
          const r = e.getBoundingClientRect();
          const hit = document.elementFromPoint(
            Math.min(innerWidth - 1, Math.max(1, r.left + r.width / 2)),
            Math.min(innerHeight - 1, Math.max(1, r.top + r.height / 2)),
          );
          return (
            r.width > 0 &&
            r.height > 0 &&
            r.top < innerHeight &&
            r.bottom > 0 &&
            (hit === e || e.contains(hit))
          );
        }),
        true,
        `focused control is reachable and not covered at ${width}x${height}: ${await page.evaluate(
          () => {
            const focused = document.activeElement;
            const target = focused?.matches('input[type=radio]')
              ? focused.closest('label')
              : focused;
            const rect = target?.getBoundingClientRect();
            return JSON.stringify({
              focused: focused?.outerHTML.slice(0, 250),
              rect,
              hit:
                rect &&
                document
                  .elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2)
                  ?.outerHTML.slice(0, 250),
              drawer: document.querySelector('.workspace-sidebar')?.getBoundingClientRect(),
            });
          },
        )}`,
      );
    }
    try {
      await page.goto(origin);
      await page.getByRole('button', { name: ru['model.choose'], exact: true }).waitFor();
      await bounds();
      const targets = await page.locator('.workspace-shell button').evaluateAll((items) =>
        items
          .filter((e) => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden')
          .map((e) => ({
            name: e.getAttribute('aria-label') || e.textContent,
            height: e.getBoundingClientRect().height,
            width: e.getBoundingClientRect().width,
          })),
      );
      // DOMRect may round a 44px target a fraction of a pixel below 44.
      assert.ok(
        targets.every((r) => r.width >= 43.99 && r.height >= 43.99),
        `primary actions have 44px targets: ${JSON.stringify(targets.filter((r) => r.width < 43.99 || r.height < 43.99))}`,
      );
      await page.locator('.skip-link').focus();
      await page.keyboard.press('Enter');
      assert.equal(
        await page.locator('#workspace-main').evaluate((e) => e === document.activeElement),
        true,
        'skip link focuses content',
      );
      await page.getByRole('button', { name: ru['model.choose'], exact: true }).click();
      await page.locator('#chat-model-search').focus();
      await visibleFocus();
      assert.equal(
        await page.locator('#chat-model-menu').evaluate((e) => {
          const r = e.getBoundingClientRect();
          return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight;
        }),
        true,
        'model popover fits viewport',
      );
      await page.locator('#chat-model-search').press('Escape');
      await page.locator('#question').fill('Draft');
      await page.locator('.send-button').scrollIntoViewIfNeeded();
      await page.locator('.send-button').focus();
      await visibleFocus();
      await page.screenshot({
        path: fileURLToPath(
          new URL(`../../logs/f010/viewport-${width}-${height}.png`, import.meta.url),
        ),
      });
      await page.locator('.chat-controls-trigger').click();
      await page.locator('.chat-controls-panel button').focus();
      await visibleFocus();
      assert.equal(
        await page
          .locator('.chat-controls-panel')
          .evaluate((e) => e.getBoundingClientRect().bottom <= innerHeight - 8),
        true,
        'Controls fit within viewport',
      );
      await page.keyboard.press('Shift+Tab');
      await visibleFocus();
      if (await page.locator('.chat-controls-panel').isVisible())
        await page.locator('.chat-controls-panel button').click();
      await openSettings(page, 'appearance');
      await bounds();
      await page.locator('#settings-tab-appearance').focus();
      await visibleFocus();
      assert.equal(await page.locator('#settings-tab-llm').count(), 0);
      for (let i = 0; i < 2; i++) {
        await page.keyboard.press('Tab');
        await visibleFocus();
      }
      await page.locator('#account-language').focus();
      await page.keyboard.press('Tab');
      assert.equal(
        await page.evaluate(() => document.activeElement.closest('.settings-embedded') === null),
        true,
        'settings page does not trap focus',
      );
      await closeSettings(page);
      await visibleFocus();
      await showWorkspaceView(page, ru['workspace.projects']);
      await bounds();
      await page.locator('.project-card').focus();
      await visibleFocus();
      await page.locator('.project-card').click();
      await page.getByLabel(ru['upload.title'], { exact: true }).fill('Preserved');
      await bounds();
      const touch = await page
        .locator('.upload-form input,.upload-form select,.upload-form button')
        .evaluateAll((items) =>
          items.map((e) => ({
            height: e.getBoundingClientRect().height,
            width: e.getBoundingClientRect().width,
          })),
        );
      assert.ok(
        touch.every((r) => r.height >= 44 && r.width >= 44),
        'upload controls have 44px touch targets',
      );
      const colors = await page.locator('.upload-submit').evaluate((e) => ({
        ink: getComputedStyle(e).color,
        bg: getComputedStyle(e).backgroundColor,
      }));
      const luminance = (color) =>
        color
          .match(/[\d.]+/g)
          .slice(0, 3)
          .map(Number)
          .map((v) => {
            v /= 255;
            return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
          })
          .reduce((total, v, i) => total + v * [0.2126, 0.7152, 0.0722][i], 0);
      const a = luminance(colors.ink),
        b = luminance(colors.bg);
      assert.ok(
        (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) >= 4.5,
        'upload action text has 4.5:1 contrast',
      );
      await showWorkspaceView(page, ru['nav.chat']);
      assert.equal(await page.locator('#question').inputValue(), 'Draft');
      await page.locator('.send-button').click();
      await page.getByText('Completed answer', { exact: true }).waitFor();
      await page.locator('.send-button').scrollIntoViewIfNeeded();
      await bounds();
      await page.emulateMedia({ reducedMotion: 'reduce' });
      assert.deepEqual(errors, []);
      checks++;
    } finally {
      await context.close();
    }
  }
  return checks;
}
