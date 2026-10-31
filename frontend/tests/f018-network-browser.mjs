/** Real Chromium coverage of both network forms against isolated HTTP boundaries. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const screenshots = fileURLToPath(new URL('../../logs/f018-browser/', import.meta.url));
const server = createServer(async (req, res) => {
  const pathname = new URL(req.url, 'http://local').pathname;
  const target = path.resolve(root, '.' + pathname.replace(/\/$/, '/index.html'));
  if (!target.startsWith(root + path.sep)) return res.writeHead(403).end();
  try {
    res.setHeader(
      'Content-Type',
      { '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png' }[path.extname(target)] ||
        'text/html',
    );
    res.end(await readFile(target));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
let browser;
let checks = 0;
try {
  browser = await chromium.launch({
    executablePath: process.env.RUVIE_BROWSER_PATH,
    headless: true,
  });
  await mkdir(screenshots, { recursive: true });
  for (const locale of ['vi-VN', 'en-US', 'ru-RU']) {
    const messages = JSON.parse(
      await readFile(
        new URL('../src/lib/i18n/locales/' + locale + '/translation.json', import.meta.url),
        'utf8',
      ),
    );
    for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ locale, viewport: { width: 1000, height: 1100 } });
      await context.addInitScript(
        ({ locale, theme }) => {
          localStorage.setItem('ruvie.ui.locale', locale);
          localStorage.setItem('ruvie.ui.theme.actor', theme);
        },
        { locale, theme },
      );
      const page = await context.newPage();
      page.setDefaultTimeout(8000);
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      const stored = {
        reply: {
          configured: true,
          base_url: 'https://reply.test',
          has_api_key: true,
          network: { mode: 'direct', proxy_url: null },
          allowed_model_ids: ['a'],
          default_model_id: 'a',
          version: 1,
          updated_at: null,
        },
        embedding: {
          configured: true,
          base_url: 'https://embed.test',
          has_api_key: true,
          network: { mode: 'direct', proxy_url: null },
          model_id: 'baai/bge-m3',
          dimension: 1024,
          distance_metric: 'cosine',
          version: 1,
          updated_at: null,
        },
      };
      const writes = [];
      let invalidNetwork = false;
      await page.route('**/*', async (route) => {
        const api = new URL(route.request().url()).pathname;
        if (!/^\/(auth|admin|projects|documents|llm|models|chat)(\/|$)/.test(api))
          return route.continue();
        const json = (data) => route.fulfill({ json: data });
        if (api === '/auth/session')
          return json({
            user: { id: 'actor', display_name: 'Admin', system_role: 'admin' },
            csrf_token: 'csrf',
          });
        if (api === '/auth/setup') return json({ requires_initial_admin: false });
        if (api === '/auth/presence') return route.fulfill({ status: 204 });
        if (api === '/projects') return json({ items: [] });
        if (api === '/llm/connection')
          return json({
            configured: true,
            selected_model_id: 'a',
            configuration_version: stored.reply.version,
          });
        if (api === '/models')
          return json({
            models: [{ id: 'a', name: 'Reply A' }],
            selected_model_id: 'a',
            selection_required: false,
            configuration_version: stored.reply.version,
          });
        const kind = api.startsWith('/admin/embedding/') ? 'embedding' : 'reply';
        const metadata = stored[kind];
        if (api === '/admin/llm/connection' || api === '/admin/embedding/connection') {
          if (route.request().method() === 'PUT') {
            const body = route.request().postDataJSON();
            assert.equal(route.request().headers()['x-csrf-token'], 'csrf');
            assert.equal(body.expected_version, metadata.version);
            writes.push({ kind, network: body.network });
            stored[kind] = { ...metadata, network: body.network, version: metadata.version + 1 };
          }
          return json(stored[kind]);
        }
        if (invalidNetwork && (api.endsWith('/catalog') || api.endsWith('/verify')))
          return route.fulfill({
            status: 422,
            json: { detail: { code: 'invalid_network_configuration' } },
          });
        if (api === '/admin/embedding/connection/verify')
          return json({
            compatible: true,
            model_id: 'baai/bge-m3',
            dimension: 1024,
            distance_metric: 'cosine',
            version: metadata.version,
          });
        if (api.endsWith('/probe'))
          return json({ success: true, model_id: 'a', version: metadata.version });
        if (api.endsWith('/catalog') || api.endsWith('/verify'))
          return json({
            models:
              kind === 'embedding'
                ? [
                    {
                      id: 'baai/bge-m3',
                      name: 'BGE M3',
                      dimension: 1024,
                      supported: true,
                      reason_code: null,
                    },
                  ]
                : [{ id: 'a', name: 'Reply A' }],
            version: metadata.version,
          });
        return route.fulfill({ status: 404, json: { detail: { code: 'not_found' } } });
      });
      await page.goto(`http://127.0.0.1:${server.address().port}/?view=admin-settings`);
      for (const kind of ['reply', 'embedding']) {
        await page.locator('#admin-settings-tab-' + kind).click();
        const form = page.locator('[data-connection="' + kind + '"]');
        const prefix = kind === 'reply' ? 'llm' : 'embedding';
        const mode = form.locator('#' + prefix + '-network-mode');
        const endpoint = form.locator('#' + prefix + '-network-proxy');
        const apply = form.locator('button[type="submit"]');
        await mode.waitFor();
        assert.equal(
          await form
            .getByRole('combobox', { name: messages['ai.network.title'], exact: true })
            .count(),
          1,
        );
        assert.equal(
          await form
            .getByRole('heading', { name: messages['ai.network.title'], exact: true })
            .count(),
          0,
        );
        assert.equal(await form.locator('#' + prefix + '-connection-help').count(), 0);
        assert.equal(await mode.inputValue(), 'direct');
        assert.equal(await endpoint.count(), 0);
        await mode.focus();
        await page.keyboard.press('End');
        await page.keyboard.press('Tab');
        await endpoint.waitFor();
        assert.equal(await endpoint.getAttribute('required'), '');
        assert.equal(await apply.isDisabled(), true);
        assert.equal(writes.length, kind === 'reply' ? 0 : 2);
        await endpoint.fill('socks5://127.0.0.1:1080');
        const modeBox = await mode.boundingBox();
        const endpointBox = await endpoint.boundingBox();
        assert.ok(modeBox.width < endpointBox.width);
        assert.equal(
          await mode.evaluate((el) => getComputedStyle(el).borderRadius),
          await endpoint.evaluate((el) => getComputedStyle(el).borderRadius),
        );
        invalidNetwork = true;
        await form.locator('.connection-actions button').click();
        await page.waitForFunction(
          (el) => el.getAttribute('aria-invalid') === 'true',
          await endpoint.elementHandle(),
        );
        const errorId = prefix + '-network-error';
        assert.ok((await endpoint.getAttribute('aria-describedby')).split(' ').includes(errorId));
        assert.equal(await page.locator('#' + errorId).count(), 1);
        assert.equal(await page.locator('#' + errorId).isVisible(), true);
        invalidNetwork = false;
        const verify = async () => {
          await form.locator('.connection-actions button').click();
          if (kind === 'embedding') {
            await form.getByRole('radio', { name: /BGE M3/ }).check();
            await form.getByRole('button', { name: messages['ai.probe'], exact: true }).click();
          }
          await apply.waitFor();
          await page.waitForFunction((el) => !el.disabled, await apply.elementHandle());
        };
        await verify();
        await endpoint.fill('socks5://127.0.0.1:1081');
        assert.equal(await apply.isDisabled(), true);
        await verify();
        await form.screenshot({ path: path.join(screenshots, `${locale}-${theme}-${kind}.png`) });
        await apply.click();
        await page.waitForFunction((el) => el.disabled, await apply.elementHandle());
        assert.deepEqual(stored[kind].network, {
          mode: 'proxy',
          proxy_url: 'socks5://127.0.0.1:1081',
        });
        await mode.selectOption('direct');
        assert.equal(await endpoint.count(), 0);
        await verify();
        await apply.click();
        await page.waitForFunction((el) => el.disabled, await apply.elementHandle());
        assert.deepEqual(stored[kind].network, { mode: 'direct', proxy_url: null });
        const browserStorage = await page.evaluate(() => JSON.stringify({ ...localStorage }));
        assert.equal(browserStorage.includes('socks5://'), false);
        checks++;
      }
      await page.reload();
      await page.locator('#llm-network-mode').waitFor();
      assert.equal(await page.locator('#llm-network-mode').inputValue(), 'direct');
      assert.equal(await page.locator('#llm-network-proxy').count(), 0);
      assert.deepEqual(errors, []);
      assert.equal(await page.locator('body').evaluate((el) => el.scrollWidth <= innerWidth), true);
      await context.close();
    }
  }
  console.log(`F018 network browser: ${checks} form/locale/theme scenarios passed`);
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
