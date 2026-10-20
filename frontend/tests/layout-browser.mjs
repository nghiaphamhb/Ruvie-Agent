import {
  showWorkspaceView,
  closeSettings,
  openAccountMenu,
  ensureSidebar,
} from './workspace-actions.mjs';
/** Desktop and 200% zoom-equivalent CSS viewport checks; no mobile navigation. */
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

export async function runLayoutChecks(browser, origin) {
  let checks = 0;
  // 640x360 CSS pixels at 2x reproduces the layout/pixels of 1280x720 at 200% zoom.
  for (const size of [
    { width: 1280, height: 720, scale: 1 },
    { width: 1024, height: 600, scale: 1 },
    { width: 640, height: 360, scale: 2 },
  ]) {
    const page = await browser.newPage({
      locale: 'vi-VN',
      viewport: { width: size.width, height: size.height },
      deviceScaleFactor: size.scale,
    });
    page.setDefaultTimeout(5000);
    const errors = [];
    const requests = [];
    page.on('request', (request) => requests.push(new URL(request.url()).pathname));
    const citation = {
      citation_id: 'c',
      document_id: 'd'.repeat(70),
      revision_id: 'r'.repeat(70),
      chunk_id: 'ch'.repeat(35),
      ordinal: 1,
      start_offset: 0,
      end_offset: 10,
      title: 'Long source title '.repeat(15),
      source_hash: 'hash'.repeat(40),
      software: 'Ruvie',
      software_version: '1',
    };
    page.on('pageerror', (error) => errors.push(error.message));
    const models = {
      models: [{ id: 'long', name: 'Model with a long provider name '.repeat(8) }],
      selected_model_id: 'long',
      selection_required: false,
    };
    await page.route('**/*', (route) => {
      const api = new URL(route.request().url()).pathname;
      const json = (data) =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) });
      if (api === '/auth/session')
        return json({
          user: { id: 'layout', display_name: 'Long account name '.repeat(8) },
          csrf_token: 'csrf',
        });
      if (api === '/projects')
        return json({ items: [{ id: 'p', code: 'P', name: 'Long project name '.repeat(8) }] });
      if (api === '/llm/connection')
        return json({
          source: 'server',
          base_url: 'https://example.test/v1',
          has_api_key: true,
          selected_model_id: 'long',
        });
      if (api === '/models') return json(models);
      if (api === '/chat')
        return route.fulfill({
          contentType: 'text/event-stream',
          body: `event: delta\ndata: ${JSON.stringify({ text: '<b>Plain answer</b>\n' + 'Long answer line\n'.repeat(80) })}\n\nevent: citations\ndata: ${JSON.stringify({ citations: [citation] })}\n\nevent: completed\ndata: {}\n\n`,
        });
      if (api === '/llm/connection/model') return json({ selected_model_id: 'long' });
      return route.continue();
    });
    const nav = page.getByRole('navigation', { name: 'Điều hướng chính' });
    const show = (name) => showWorkspaceView(page, name);
    async function bounds() {
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        true,
        'no horizontal page overflow',
      );
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight + 1),
        true,
        'only application regions scroll',
      );
      assert.equal(
        size.width > 800 ? await nav.isVisible() : await page.locator('.sidebar-open').isVisible(),
        true,
        'navigation is reachable at every viewport',
      );
    }
    try {
      await page.goto(origin);
      await page.getByRole('button', { name: 'Chọn model', exact: true }).waitFor();
      await bounds();
      await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Long question '.repeat(80));
      await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).scrollIntoViewIfNeeded();
      assert.equal(
        await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).isVisible(),
        true,
      );
      await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
      const sources = page.getByText('1 nguồn tham khảo', { exact: true });
      try {
        await sources.click();
      } catch (error) {
        console.log(
          'Source geometry',
          size,
          await page.evaluate(() =>
            ['.workspace-toolbar', '.chat-view', '.conversation', '.composer-area', 'summary'].map(
              (selector) => {
                const e = document.querySelector(selector);
                return {
                  selector,
                  rect: e.getBoundingClientRect().toJSON(),
                  height: e.clientHeight,
                  scroll: e.scrollHeight,
                };
              },
            ),
          ),
        );
        throw error;
      }
      await page.getByText(citation.title, { exact: true }).waitFor();
      assert.equal(await page.locator('.answer b').count(), 0, 'answer remains plain text');
      await page.locator('.source-title').click();
      await page.locator('.source-dialog details summary').click();
      for (const value of [citation.document_id, citation.revision_id, citation.source_hash])
        await page.getByText(value, { exact: true }).scrollIntoViewIfNeeded();
      await bounds();
      assert.deepEqual(
        requests.filter((path) => /^\/(files|documents|retrieval)(\/|$)/.test(path)),
        [],
        'opening sources never fetches blob/content',
      );
      await page.locator('.source-dialog').press('Escape');
      await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).scrollIntoViewIfNeeded();
      await page.screenshot({
        path: fileURLToPath(
          new URL(`../../logs/f007-chat-${size.width}-${size.scale}x.png`, import.meta.url),
        ),
      });
      await show('Tải tài liệu');
      await page
        .getByLabel('Tên tài liệu', { exact: true })
        .fill('Long document title '.repeat(20));
      await page.getByLabel('File', { exact: true }).setInputFiles({
        name: 'Long-file-name-'.repeat(10) + '.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('text'),
      });
      await page.locator('.upload-submit').scrollIntoViewIfNeeded();
      await bounds();
      await page.screenshot({
        path: fileURLToPath(
          new URL(`../../logs/f007-upload-${size.width}-${size.scale}x.png`, import.meta.url),
        ),
      });
      await show('Kết nối LLM');
      await page
        .getByLabel('Base URL', { exact: true })
        .fill('https://' + 'provider-name-'.repeat(20) + 'test/v1');
      await page.getByRole('button', { name: 'Kết nối', exact: true }).scrollIntoViewIfNeeded();
      await bounds();
      await page.screenshot({
        path: fileURLToPath(
          new URL(`../../logs/f007-llm-${size.width}-${size.scale}x.png`, import.meta.url),
        ),
      });
      checks++;
      await closeSettings(page);
      await ensureSidebar(page);
      await nav.getByRole('button', { name: 'Chat', exact: true }).focus();
      await page.keyboard.press('Enter');
      assert.notEqual(
        await page.locator('.composer').evaluate((e) => getComputedStyle(e).outlineStyle),
        'none',
        'keyboard focus is visible',
      );
      assert.equal(
        await page.locator('#question').evaluate((e) => e === document.activeElement),
        true,
      );
      for (let i = 0; i < 12; i++) {
        await page.keyboard.press('Tab');
        assert.equal(
          await page.evaluate(() => Boolean(document.activeElement.closest('[hidden]'))),
          false,
          'hidden panels never receive Tab',
        );
      }
      const picker = page.getByRole('button', { name: 'Chọn model', exact: true });
      await picker.click();
      await page.getByRole('combobox', { name: 'Tìm model', exact: true }).fill('long');
      await page.keyboard.press('Escape');
      assert.equal(await picker.evaluate((e) => e === document.activeElement), true);
      await openAccountMenu(page);
      await page.getByRole('menuitem', { name: 'Đăng xuất', exact: true }).scrollIntoViewIfNeeded();
      await bounds();
      checks++;
      const themed = ['.upload-panel'];
      const spaced = ['.upload-panel'];
      const beforeSpace = await page.evaluate(
        (selectors) => selectors.map((s) => getComputedStyle(document.querySelector(s)).padding),
        spaced,
      );
      const before = await page.evaluate(
        (selectors) =>
          selectors.map((s) => getComputedStyle(document.querySelector(s)).borderRadius),
        themed,
      );
      await page.evaluate(() => {
        const style = document.documentElement.style;
        style.setProperty('--radius', '24px');
        style.setProperty('--space', '10px');
        style.setProperty('--font-family', 'monospace');
        document
          .querySelector('.workspace-shell')
          .style.setProperty('--soft', 'rgb(220, 230, 240)');
      });
      const after = await page.evaluate(
        (selectors) =>
          selectors.map((s) => getComputedStyle(document.querySelector(s)).borderRadius),
        themed,
      );
      const afterSpace = await page.evaluate(
        (selectors) => selectors.map((s) => getComputedStyle(document.querySelector(s)).padding),
        spaced,
      );
      assert.ok(
        afterSpace.every((value, index) => value !== beforeSpace[index]),
        'existing upload retains spacing token',
      );
      assert.ok(
        after.every((value, index) => value !== before[index]),
        'existing upload retains radius token',
      );
      assert.ok(
        await page
          .locator('.workspace-sidebar')
          .evaluate((e) => getComputedStyle(e).fontFamily.includes('monospace')),
        'font variable reaches UI',
      );
      assert.equal(
        await nav
          .getByRole('button', { name: 'Chat mới', exact: true })
          .evaluate((e) => getComputedStyle(e).backgroundColor),
        'rgb(220, 230, 240)',
      );
      await page.evaluate(() => {
        document.documentElement.removeAttribute('style');
        document.querySelector('.workspace-shell').removeAttribute('style');
      });
      checks++;
      const colors = await page.evaluate(() => {
        const sample = document.createElement('span');
        document.querySelector('.workspace-shell').append(sample);
        const read = (name) => {
          sample.style.color = `var(${name})`;
          return getComputedStyle(sample).color;
        };
        const pairs = [
          ['--ink', '--paper'],
          ['--ink', '--soft'],
          ['--muted', '--paper'],
          ['--muted', '--surface'],
          ['--error', '--error-bg'],
          ['--surface', '--accent'],
        ].map((pair) => pair.map(read));
        sample.remove();
        return pairs;
      });
      const luminance = (color) =>
        color
          .match(/[\d.]+/g)
          .slice(0, 3)
          .map(Number)
          .map((v) => {
            v /= 255;
            return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
          })
          .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
      for (const [foreground, background] of colors) {
        const a = luminance(foreground),
          b = luminance(background);
        assert.ok(
          (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) >= 4.5,
          `contrast ${foreground} on ${background}`,
        );
      }
      await page.emulateMedia({ reducedMotion: 'reduce' });
      assert.equal(
        await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches),
        true,
      );
      assert.ok(
        await page.evaluate(() => {
          const dot = document.createElement('span');
          dot.className = 'status-dot';
          document.body.append(dot);
          const duration = parseFloat(getComputedStyle(dot).animationDuration);
          dot.remove();
          return duration <= 0.01;
        }),
        'reduced motion disables repeated loading animation',
      );
      assert.deepEqual(errors, []);
      checks++;
    } finally {
      await page.close();
    }
  }
  return checks;
}
