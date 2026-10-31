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
  const page = await browser.newPage({ locale: 'vi-VN', viewport: { width: 1366, height: 900 } });
  page.setDefaultTimeout(8000);
  let org = {
    configured: false,
    base_url: null,
    has_api_key: false,
    network: { mode: 'direct', proxy_url: null },
    allowed_model_ids: [],
    default_model_id: null,
    version: 0,
    updated_at: null,
  };
  let mode = 'normal',
    role = 'admin',
    puts = 0,
    adminReads = 0;
  const errors = [],
    bodies = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/*', async (route) => {
    const api = new URL(route.request().url()).pathname,
      method = route.request().method();
    if (!/^\/(auth|admin|projects|documents|llm|models|chat)(\/|$)/.test(api))
      return route.continue();
    const json = (data, status = 200) => route.fulfill({ status, json: data });
    if (api === '/auth/session')
      return json({
        user: { id: 'actor', display_name: 'Admin', system_role: role },
        csrf_token: 'csrf',
      });
    if (api === '/auth/setup') return json({ requires_initial_admin: false });
    if (api === '/auth/presence') return route.fulfill({ status: 204 });
    if (api === '/projects') return json({ items: [] });
    if (api === '/admin/users/list')
      return json({ users: [], total: 0, page: 1, page_size: 20, presence: {} });
    if (api === '/llm/connection')
      return json({
        configured: org.configured,
        selected_model_id: org.default_model_id,
        configuration_version: org.version,
      });
    if (api === '/models')
      return json({
        models: org.allowed_model_ids.map((id) => ({ id, name: id === 'a' ? 'Alpha' : 'Beta' })),
        selected_model_id: org.default_model_id,
        selection_required: !org.default_model_id,
        configuration_version: org.version,
      });
    if (api === '/admin/llm/connection/verify' && mode === 'verify-error')
      return json({ detail: { code: 'llm_provider_unavailable' } }, 502);
    if (api === '/admin/llm/connection' && method === 'GET' && mode === 'reload-error')
      return json({ detail: { code: 'llm_settings_unavailable' } }, 503);
    if (api === '/admin/llm/connection/verify')
      return json({
        models: [
          { id: 'a', name: 'Alpha' },
          { id: 'b', name: 'Beta' },
        ],
        version: org.version,
      });
    if (api === '/admin/llm/connection' && method === 'GET') {
      adminReads++;
      return json(org);
    }
    if (api === '/admin/llm/connection' && method === 'PUT') {
      puts++;
      const body = route.request().postDataJSON();
      bodies.push(body);
      assert.equal(route.request().headers()['x-csrf-token'], 'csrf');
      if (mode === 'conflict') return json({ detail: { code: 'configuration_conflict' } }, 409);
      if (mode === 'lost') return route.abort('failed');
      org = {
        configured: true,
        base_url: body.base_url,
        has_api_key:
          body.key_action === 'replace' || (body.key_action === 'keep' && org.has_api_key),
        network: body.network,
        allowed_model_ids: body.allowed_model_ids,
        default_model_id: body.default_model_id,
        version: org.version + 1,
        updated_at: null,
      };
      return json(org);
    }
    return json({ detail: { code: 'not_found' } }, 404);
  });
  const origin = `http://127.0.0.1:${server.address().port}`;
  await page.goto(origin + '/?view=admin-settings');
  const form = page.locator('[data-connection="reply"]');
  await form.getByText('Chưa có cấu hình được áp dụng.').waitFor();
  const surface = await form.evaluate((el) => ({
    border: getComputedStyle(el).borderTopWidth,
    background: getComputedStyle(el).backgroundColor,
  }));
  assert.equal(surface.border, '0px');
  assert.equal(surface.background, 'rgba(0, 0, 0, 0)');
  assert.equal(await page.locator('#llm-key-action svg.key-chevron').count(), 1);
  checks++;
  assert.equal(
    await page.locator('[data-sonner-toast]').count(),
    0,
    'Initial form load stays quiet',
  );
  await page.locator('#llm-key-action').focus();
  await page.keyboard.press('ArrowDown');
  await page.getByRole('listbox').waitFor();
  assert.equal(
    await page.getByRole('option', { name: 'Giữ key hiện tại', exact: true }).isDisabled(),
    true,
  );
  await page.keyboard.press('End');
  await page.keyboard.press('Escape');
  assert.equal(
    await page.locator('#llm-key-action').evaluate((el) => el === document.activeElement),
    true,
  );
  checks++;
  await page.locator('#llm-key-hint-trigger').focus();
  await page.getByRole('tooltip').waitFor();
  assert.match(await page.getByRole('tooltip').innerText(), /thiết lập lần đầu/);
  await page.keyboard.press('Escape');
  await page.getByRole('tooltip').waitFor({ state: 'hidden' });
  assert.equal(
    await form
      .getByText('Thay đổi key chỉ có hiệu lực sau khi áp dụng cấu hình.', { exact: true })
      .isVisible(),
    false,
  );
  checks++;
  await page.locator('#llm-url').fill('https://provider.test/v1');
  await page.locator('#llm-key-action').click();
  await page.getByRole('option', { name: 'Nhập key mới', exact: true }).click();
  await page.locator('#llm-key').fill('draft-private-key');
  await form.getByRole('button', { name: 'Kiểm tra kết nối', exact: true }).click();
  await form.getByRole('checkbox', { name: /Cho phép sử dụng Beta b/ }).check();
  await form.getByRole('radio', { name: /Mặc định Beta b/ }).check();
  await page.locator('[data-sonner-toast]').filter({ hasText: 'Đã tải danh sách model' }).waitFor();
  assert.equal(await form.locator('table tbody tr').count(), 2);
  await mkdir(fileURLToPath(new URL('../../logs/f016-mockup/', import.meta.url)), {
    recursive: true,
  });
  await page.setViewportSize({ width: 1366, height: 1300 });
  for (const theme of ['light', 'dark']) {
    await page
      .locator('.workspace-shell')
      .evaluate((el, theme) => el.setAttribute('data-theme', theme), theme);
    await form.screenshot({
      style: '[data-sonner-toaster]{visibility:hidden}',
      path: fileURLToPath(new URL('../../logs/f016-mockup/' + theme + '.png', import.meta.url)),
    });
  }
  checks++;
  await form.getByRole('checkbox', { name: /Cho phép sử dụng Beta b/ }).uncheck();
  await form.getByText('Chưa chọn model mặc định', { exact: true }).waitFor();
  await form.getByRole('checkbox', { name: /Cho phép sử dụng Beta b/ }).check();
  await form.getByRole('radio', { name: /Mặc định Beta b/ }).check();
  checks++;
  await form.getByText('Mặc định: Beta', { exact: false }).waitFor();
  assert.equal(puts, 0);
  checks++;
  await form.getByRole('button', { name: 'Áp dụng cấu hình', exact: true }).click();
  await form.getByText('Đã áp dụng cấu hình cho tổ chức.').waitFor();
  assert.equal(puts, 1);
  assert.deepEqual(bodies[0].allowed_model_ids, ['b']);
  assert.equal(bodies[0].default_model_id, 'b');
  assert.equal(bodies[0].expected_version, 0);
  assert.equal(await page.locator('#llm-key').count(), 0);
  checks++;
  await form.getByRole('button', { name: 'Kiểm tra kết nối', exact: true }).click();
  mode = 'conflict';
  await form.getByRole('button', { name: 'Áp dụng cấu hình', exact: true }).click();
  await form.getByText(/Admin khác đã đổi cấu hình/).waitFor();
  assert.equal(puts, 2);
  checks++;
  mode = 'normal';
  await form.getByRole('button', { name: 'Tải lại', exact: true }).click();
  await page.locator('[data-sonner-toast]').filter({ hasText: 'Đã tải lại cấu hình' }).waitFor();
  await page.locator('#llm-key-action').click();
  await page.getByRole('option', { name: 'Nhập key mới', exact: true }).click();
  await page.locator('#llm-key').fill('hidden-secret');
  await page.locator('.sidebar-brand').click();
  await page.goto(origin + '/?view=admin-settings');
  await page.locator('#llm-key-action').waitFor();
  assert.equal(await page.locator('#llm-key').count(), 0);
  checks++;
  await form.getByRole('button', { name: 'Kiểm tra kết nối', exact: true }).click();
  mode = 'lost';
  await form.getByRole('button', { name: 'Áp dụng cấu hình', exact: true }).click();
  await form.getByText(/Chưa xác định kết quả lưu/).waitFor();
  assert.equal(puts, 3);
  checks++;
  mode = 'verify-error';
  await form.getByRole('button', { name: 'Kiểm tra kết nối', exact: true }).click();
  await page.locator('[data-sonner-toast][data-type="error"]').waitFor();
  mode = 'reload-error';
  await form.getByRole('button', { name: 'Tải lại', exact: true }).click();
  await page
    .locator('[data-sonner-toast][data-type="error"]')
    .filter({ hasText: /cấu hình|kết nối/ })
    .waitFor();
  checks++;
  mode = 'normal';
  const reads = adminReads;
  role = 'user';
  await page.goto(origin);
  await page.locator('#chat-model-menu').waitFor({ state: 'attached' });
  assert.equal(adminReads, reads);
  assert.equal(await page.locator('#llm-key').count(), 0);
  checks++;
  assert.deepEqual(errors, []);
  checks++;
  console.log(`F016 organization integration: ${checks} checks passed`);
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
