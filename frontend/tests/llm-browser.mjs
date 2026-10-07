/** Browser check against the built app and fake APIs; no dev database/provider is used.
 * Run after npm run build. RUVIE_PLAYWRIGHT_PATH/RUVIE_BROWSER_PATH may point to bundled tools.
 */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root = fileURLToPath(new URL('../dist/', import.meta.url));
const server = createServer(async (request, response) => {
  const target = path.resolve(root, '.' + new URL(request.url, 'http://localhost').pathname.replace(/\/$/, '/index.html'));
  if (!target.startsWith(root)) { response.writeHead(403).end(); return; }
  try {
    const content = await readFile(target);
    response.setHeader('Content-Type', target.endsWith('.js') ? 'text/javascript' : target.endsWith('.css') ? 'text/css' : 'text/html');
    response.end(content);
  } catch { response.writeHead(404).end(); }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let checks = 0;
try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.RUVIE_BROWSER_PATH || undefined });
  const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  let loggedIn = false;
  let expired = false;
  let failSave = false;
  let slowSave = false;
  let slowChat = false;
  let slowModels = false;
  let delayedProjects = false;
  let failProjects = false;
  const bodies = [];
  let metadata = { source: 'server', base_url: 'https://server.test/v1', has_api_key: true, selected_model_id: 'a' };
  const catalog = { models: [{ id: 'a', name: 'Model A' }, { id: 'b', name: 'Model B' }], selected_model_id: 'a', selection_required: false };
  let modelReads = 0;
  await page.route('**/*', async (route) => {
    const req = route.request();
    const api = new URL(req.url()).pathname;
    const respond = (data, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
    if (api === '/auth/session') return respond(loggedIn ? { user: { id: 'alpha', display_name: 'Alpha' }, csrf_token: 'csrf' } : {}, loggedIn ? 200 : 401);
    if (api === '/auth/login') { loggedIn = true; expired = false; return respond({ user: { id: 'alpha', display_name: 'Alpha' }, csrf_token: 'csrf' }); }
    if (api === '/auth/logout') { loggedIn = false; return respond({}); }
    // Keep login busy while the connection component mounts.
    if (api === '/projects') {
      if (failProjects) return respond({}, 503);
      const stale = delayedProjects;
      delayedProjects = false;
      await wait(stale ? 1000 : 250);
      return respond({ items: stale ? [{ id: 'old', code: 'old', name: 'Private old project' }] : [] });
    }
    if (api === '/models') { modelReads++; if (slowModels) await wait(700); return respond(catalog); }
    if (api === '/llm/connection') {
      if (expired) return respond({}, 401);
      if (req.method() === 'PUT') {
        bodies.push(req.postDataJSON());
        if (slowSave) await wait(500);
        if (failSave) return respond({ detail: 'private-key' }, 502);
        const body = req.postDataJSON();
        const same = metadata.source === 'personal' && metadata.base_url === body.base_url;
        metadata = { source: 'personal', base_url: body.base_url, has_api_key: body.api_key === undefined ? same && metadata.has_api_key : Boolean(body.api_key), selected_model_id: 'a' };
        return respond(catalog);
      }
      if (req.method() === 'DELETE') {
        metadata = { source: 'server', base_url: 'https://server.test/v1', has_api_key: true, selected_model_id: 'a' };
        return route.fulfill({ status: 204 });
      }
      return respond(metadata);
    }
    if (api === '/chat') {
      if (slowChat) await wait(700);
      return route.fulfill({ contentType: 'text/event-stream', body: 'event: delta\ndata: {"text":"Answer"}\n\nevent: completed\ndata: {}\n\n' });
    }
    return route.continue();
  });
  await page.goto(origin);
  async function login() {
    await page.getByLabel('Email', { exact: true }).fill('alpha@test.com');
    await page.getByLabel('Mật khẩu', { exact: true }).fill('test-password');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await page.getByText('Model: Model A', { exact: false }).waitFor({ timeout: 4000 });
  }
  await login();
  assert.ok(modelReads > 0, 'models must load even when login is still busy');
  checks++;
  const url = page.getByLabel('Base URL', { exact: true });
  const key = page.getByLabel('API key (tùy chọn)', { exact: true });
  const connect = page.getByRole('button', { name: 'Kết nối', exact: true });
  await key.fill('temporary-key');
  await url.fill('https://personal.test/v1');
  assert.equal(await key.inputValue(), '', 'changing URL clears typed key');
  await connect.click();
  await page.getByText('Đã lưu kết nối.', { exact: true }).waitFor();
  assert.deepEqual(bodies.at(-1), { base_url: 'https://personal.test/v1' });
  checks++;
  await key.fill('personal-key');
  await connect.click();
  await page.getByText('Đã lưu key.', { exact: false }).waitFor();
  assert.equal(await key.inputValue(), '');
  await connect.click();
  await page.getByText('Đã lưu kết nối.', { exact: true }).waitFor();
  assert.equal(Object.hasOwn(bodies.at(-1), 'api_key'), false);
  await page.getByRole('button', { name: 'Xóa key đã lưu', exact: true }).click();
  await connect.click();
  await page.getByText('Chỉ nhập key', { exact: false }).waitFor();
  assert.equal(bodies.at(-1).api_key, '');
  checks++;
  await page.reload();
  await page.getByText('Model: Model A', { exact: false }).waitFor();
  assert.equal(await url.inputValue(), 'https://personal.test/v1');
  assert.equal(await key.inputValue(), '');
  assert.equal(await page.evaluate(() => localStorage.length), 0);
  checks++;
  failSave = true;
  await url.fill('https://failed.test/v1');
  await connect.click();
  await page.getByRole('alert').filter({ hasText: 'Không lấy được model' }).waitFor();
  assert.equal(metadata.base_url, 'https://personal.test/v1');
  assert.ok(!(await page.getByRole('alert').innerText()).includes('private-key'));
  failSave = false;
  await url.fill('https://personal.test/v1');
  slowSave = true;
  const prior = bodies.length;
  await connect.click();
  assert.equal(await url.isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).isDisabled(), true);
  await page.getByText('Đã lưu kết nối.', { exact: true }).waitFor();
  assert.equal(bodies.length, prior + 1);
  slowSave = false;
  checks++;
  slowChat = true;
  await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Question');
  await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
  assert.equal(await url.isDisabled(), true);
  await page.getByText('Answer', { exact: true }).waitFor();
  await page.waitForFunction(() => !document.querySelector('#llm-url').disabled);
  checks++;
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: fileURLToPath(new URL('../../logs/f006-form-mobile.png', import.meta.url)), fullPage: true });
  const overflow = await page.evaluate(() => [...document.querySelectorAll('body *')].filter((element) => element.getBoundingClientRect().right > innerWidth + 1).map((element) => ({ tag: element.tagName, class: element.className, right: element.getBoundingClientRect().right })));
  assert.deepEqual(overflow, [], 'no mobile horizontal overflow');
  await url.focus();
  await page.keyboard.press('Tab');
  assert.equal(await key.evaluate((element) => element === document.activeElement), true);
  await page.screenshot({ path: fileURLToPath(new URL('../../logs/f006-form-mobile.png', import.meta.url)), fullPage: true });
  checks++;
  await page.getByRole('button', { name: 'Gỡ kết nối', exact: true }).click();
  await page.getByText('Đã gỡ kết nối riêng.', { exact: true }).waitFor();
  assert.equal(await url.inputValue(), 'https://server.test/v1');
  assert.equal(await key.inputValue(), '');
  assert.equal(await page.getByRole('button', { name: 'Gỡ kết nối', exact: true }).isDisabled(), true);
  checks++;
  slowModels = true;
  await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  await page.getByRole('heading', { name: 'Đăng nhập', exact: true }).waitFor();
  await wait(900);
  assert.equal(await page.getByRole('heading', { name: 'Kết nối LLM', exact: true }).count(), 0);
  slowModels = false;
  await login();
  // A pending project read must not restore account data after logout/login.
  failProjects = true;
  await page.reload();
  await page.getByText('Model: Model A', { exact: false }).waitFor();
  failProjects = false;
  delayedProjects = true;
  await page.getByRole('button', { name: 'Thử lại', exact: true }).click();
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  await page.getByRole('heading', { name: 'Đăng nhập', exact: true }).waitFor();
  await login();
  await wait(1200);
  assert.equal(await page.getByRole('option', { name: 'Private old project', exact: false }).count(), 0);
  await page.getByText('Bạn chưa tham gia project nào.', { exact: true }).waitFor();
  checks++;
  expired = true;
  await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
  await page.getByRole('heading', { name: 'Đăng nhập', exact: true }).waitFor();
  checks++;
  assert.deepEqual(errors, []);
  console.log(`Browser: ${checks} checks passed (loading, key semantics, reload, errors, locks, mobile/keyboard, logout/expiry).`);
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
