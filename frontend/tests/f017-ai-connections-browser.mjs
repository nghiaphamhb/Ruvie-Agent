/** Built application against isolated HTTP boundaries; no application DB/provider. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const server = createServer(async (req, res) => {
  const pathname = new URL(req.url, 'http://local').pathname;
  const target = path.resolve(root, '.' + pathname.replace(/\/$/, '/index.html'));
  if (!target.startsWith(root + path.sep)) {
    res.writeHead(403).end();
    return;
  }
  try {
    res.setHeader(
      'Content-Type',
      {
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.png': 'image/png',
        '.svg': 'image/svg+xml',
      }[path.extname(target)] || 'text/html',
    );
    res.end(await readFile(target));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
let browser,
  checks = 0;
try {
  browser = await chromium.launch({
    executablePath: process.env.RUVIE_BROWSER_PATH,
    headless: true,
  });
  const page = await browser.newPage({ locale: 'vi-VN', viewport: { width: 1366, height: 1100 } });
  page.setDefaultTimeout(8000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  let embedding = {
    configured: false,
    base_url: null,
    has_api_key: false,
    network: { mode: 'direct', proxy_url: null },
    model_id: null,
    dimension: null,
    distance_metric: null,
    version: 0,
    updated_at: null,
  };
  let embeddingPuts = 0,
    replyPuts = 0,
    probeCalls = 0,
    mode = 'normal';
  await page.route('**/*', async (route) => {
    const api = new URL(route.request().url()).pathname,
      method = route.request().method();
    if (!/^\/(auth|admin|projects|documents|llm|models|chat)(\/|$)/.test(api))
      return route.continue();
    const json = (data, status = 200) => route.fulfill({ json: data, status });
    if (api === '/auth/session')
      return json({
        user: { id: 'actor', display_name: 'Admin', system_role: 'admin' },
        csrf_token: 'csrf',
      });
    if (api === '/auth/setup') return json({ requires_initial_admin: false });
    if (api === '/auth/presence') return route.fulfill({ status: 204 });
    if (api === '/projects') return json({ items: [] });
    if (api === '/llm/connection')
      return json({ configured: true, selected_model_id: 'a', configuration_version: 1 });
    if (api === '/models')
      return json({
        models: [{ id: 'a', name: 'Reply A' }],
        selected_model_id: 'a',
        selection_required: false,
        configuration_version: 1,
      });
    if (api === '/admin/llm/connection' && method === 'GET')
      return json({
        configured: true,
        base_url: 'https://reply.test/v1',
        has_api_key: true,
        network: { mode: 'direct', proxy_url: null },
        allowed_model_ids: ['a'],
        default_model_id: 'a',
        version: 1,
        updated_at: null,
      });
    if (api === '/admin/llm/connection' && method === 'PUT') {
      replyPuts++;
      return json({ detail: { code: 'configuration_conflict' } }, 409);
    }
    if (api === '/admin/embedding/connection' && method === 'GET') return json(embedding);
    if (api === '/admin/embedding/connection/catalog')
      return json({
        models: [
          {
            id: 'baai/bge-m3',
            name: 'BGE M3',
            dimension: null,
            supported: true,
            reason_code: null,
          },
          {
            id: 'other/model',
            name: 'Other model',
            dimension: 1024,
            supported: false,
            reason_code: 'embedding_model_unsupported',
          },
        ],
        version: embedding.version,
      });
    if (api === '/admin/embedding/connection/verify') {
      probeCalls++;
      return json({
        compatible: true,
        model_id: 'baai/bge-m3',
        dimension: 1024,
        distance_metric: 'cosine',
        version: embedding.version,
      });
    }
    if (api === '/admin/embedding/connection' && method === 'PUT') {
      embeddingPuts++;
      const body = route.request().postDataJSON();
      assert.equal(route.request().headers()['x-csrf-token'], 'csrf');
      assert.equal(body.model_id, 'baai/bge-m3');
      assert.equal(body.expected_version, embedding.version);
      if (mode === 'lost') return route.abort('failed');
      embedding = {
        configured: true,
        base_url: body.base_url,
        has_api_key: body.key_action === 'replace',
        network: body.network,
        model_id: body.model_id,
        dimension: 1024,
        distance_metric: 'cosine',
        version: embedding.version + 1,
        updated_at: null,
      };
      return json(embedding);
    }
    return json({ detail: { code: 'not_found' } }, 404);
  });
  const origin = `http://127.0.0.1:${server.address().port}`;
  await page.goto(origin + '/?view=admin-settings');
  const embed = page.locator('[data-connection="embedding"]');
  await page.locator('#llm-url').fill('https://reply-draft.test/v1');
  await page.locator('#llm-key-action').click();
  await page.getByRole('option', { name: 'Nhập key mới', exact: true }).click();
  await page.locator('#llm-key').fill('reply-draft-key');
  await page.locator('#admin-settings-tab-reply').focus();
  await page.keyboard.press('ArrowDown');
  await embed.waitFor({ state: 'visible' });
  await page.locator('#embedding-url').fill('https://embed.test/v1');
  await page.locator('#embedding-key-action').click();
  await page.getByRole('option', { name: 'Nhập key mới', exact: true }).click();
  await page.locator('#embedding-key').fill('embedding-draft-key');
  await page.locator('#admin-settings-tab-reply').click();
  assert.equal(await page.locator('#llm-key').inputValue(), 'reply-draft-key');
  assert.equal(await page.locator('#llm-url').inputValue(), 'https://reply-draft.test/v1');
  await page.locator('#admin-settings-tab-embedding').click();
  assert.equal(await page.locator('#embedding-key').inputValue(), 'embedding-draft-key');
  checks++;
  await embed.getByRole('button', { name: 'Kiểm tra kết nối', exact: true }).click();
  await embed.locator('table tbody tr').first().waitFor();
  await embed.getByRole('radio', { name: /Other model/ }).check();
  assert.equal(await embed.getByRole('radio', { name: /Other model/ }).isChecked(), true);
  assert.equal(
    await embed.getByRole('button', { name: 'Áp dụng cấu hình', exact: true }).isDisabled(),
    true,
  );
  assert.equal(embeddingPuts, 0);
  await embed.locator('.warning').waitFor();
  checks++;
  await embed.locator('.models .hint-trigger').focus();
  await embed.getByRole('tooltip').waitFor();
  await page.keyboard.press('Escape');
  assert.equal(await embed.getByRole('tooltip').isVisible(), false);
  await embed.getByRole('columnheader', { name: 'Có hỗ trợ', exact: true }).waitFor();
  await page.setViewportSize({ width: 1366, height: 650 });
  const scrolls = await page
    .locator('.view-panel')
    .filter({ has: page.locator('.system-settings') })
    .first()
    .evaluate((el) => {
      el.scrollTop = 100;
      return el.scrollTop > 0;
    });
  assert.equal(scrolls, true, 'hiding the scrollbar preserves page scrolling');
  await page.setViewportSize({ width: 1366, height: 1100 });
  const identifiers = await page
    .locator('[id]')
    .evaluateAll((elements) => elements.map((el) => el.id));
  assert.equal(
    new Set(identifiers).size,
    identifiers.length,
    'connection forms have independent IDs',
  );
  assert.equal(
    await page.locator('.system-settings .settings-tabs').getAttribute('aria-orientation'),
    'vertical',
  );
  const parent = await page.getByRole('button', { name: 'Kết nối AI', exact: true }).boundingBox();
  const child = await page.locator('.connection-child').first().boundingBox();
  assert.ok(child.x > parent.x && child.y > parent.y, 'children are indented below the category');
  const tabs = await page
    .locator('.connection-child')
    .evaluateAll((elements) => elements.map((el) => el.getBoundingClientRect().top));
  assert.ok(tabs[1] > tabs[0]);
  assert.equal(
    await page
      .locator('#ai-connection-tabs')
      .evaluate((el) => getComputedStyle(el).borderLeftWidth),
    '1px',
  );
  await page.getByRole('button', { name: 'Kết nối AI', exact: true }).click();
  assert.equal(await page.locator('.connection-child').first().isVisible(), false);
  await page.getByRole('button', { name: 'Kết nối AI', exact: true }).click();
  assert.equal(
    await embed.locator('.models').evaluate((el) => getComputedStyle(el).scrollbarWidth),
    'thin',
  );
  assert.equal(
    await page
      .locator('.view-panel')
      .first()
      .evaluate((el) => getComputedStyle(el).scrollbarWidth),
    'none',
  );
  checks++;
  await page.locator('#embedding-search').fill('baai');
  assert.equal(await embed.locator('table tbody tr').count(), 1);
  await page.locator('#embedding-search').fill('');
  await embed.getByRole('radio', { name: /BGE M3/ }).check();
  assert.equal(
    await embed.getByRole('button', { name: 'Áp dụng cấu hình', exact: true }).isDisabled(),
    true,
  );
  await embed.getByRole('button', { name: 'Kiểm tra model', exact: true }).click();
  await embed.getByRole('button', { name: 'Áp dụng cấu hình', exact: true }).waitFor();
  await embed.getByRole('button', { name: 'Áp dụng cấu hình', exact: true }).click();
  await embed.getByText('Đã áp dụng cấu hình cho tổ chức.', { exact: true }).waitFor();
  assert.equal(probeCalls, 1);
  assert.equal(embeddingPuts, 1);
  assert.equal(replyPuts, 0);
  assert.equal(await page.locator('#embedding-key').count(), 0);
  checks++;
  const stored = await page.evaluate(() => JSON.stringify({ ...localStorage }));
  assert.equal(stored.includes('draft-key'), false);
  checks++;
  await mkdir(fileURLToPath(new URL('../../logs/f017-browser/', import.meta.url)), {
    recursive: true,
  });
  for (const locale of ['vi-VN', 'en-US', 'ru-RU']) {
    await page.evaluate((locale) => localStorage.setItem('ruvie.ui.locale', locale), locale);
    await page.reload();
    await page.locator('#admin-settings-tab-embedding').click();
    await page.locator('#embedding-url').waitFor();
    assert.equal(await page.locator('html').getAttribute('lang'), locale);
    await embed.locator('.connection-actions button').click();
    await embed.getByRole('radio', { name: /Other model/ }).check();
    await embed.locator('.warning').waitFor();
    for (const theme of ['light', 'dark']) {
      await page
        .locator('.workspace-shell')
        .evaluate((el, theme) => el.setAttribute('data-theme', theme), theme);
      if (locale === 'vi-VN' && theme === 'light')
        await page.screenshot({
          path: fileURLToPath(
            new URL('../../logs/f017-browser/settings-tabs.png', import.meta.url),
          ),
        });
      await embed.screenshot({
        path: fileURLToPath(
          new URL('../../logs/f017-browser/' + locale + '-' + theme + '.png', import.meta.url),
        ),
      });
      assert.equal(await page.locator('body').evaluate((el) => el.scrollWidth <= innerWidth), true);
      checks++;
    }
  }
  await page.locator('.sidebar-brand').click();
  await page.goto(origin + '/?view=admin-settings');
  assert.equal(await page.locator('#llm-key').count(), 0);
  assert.equal(await page.locator('#embedding-key').count(), 0);
  checks++;
  assert.deepEqual(errors, []);
  checks++;
  console.log(`F017 AI connections browser: ${checks} checks passed`);
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
