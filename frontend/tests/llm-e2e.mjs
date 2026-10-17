import {showWorkspaceView,openSettings,closeSettings,openAccountMenu,logoutFromMenu,ensureSidebar} from './workspace-actions.mjs';
/** Called by the Python E2E fixture. Proxy real APIs; never mock browser requests. */
import assert from 'node:assert/strict';
import { createServer, request as proxyRequest } from 'node:http';
import { mkdir, readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH);
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  if (/^\/(auth|projects|documents|llm|models|chat)(\/|$)/.test(pathname)) {
    const upstream = proxyRequest(new URL(request.url, process.env.RUVIE_E2E_BACKEND_URL), {
      method: request.method, headers: request.headers
    }, (received) => {
      response.writeHead(received.statusCode, received.headers);
      received.pipe(response);
    });
    upstream.on('error', () => { response.writeHead(502).end(); });
    request.pipe(upstream);
    return;
  }
  const target = path.resolve(root, '.' + pathname.replace(/\/$/, '/index.html'));
  if (!target.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
  try {
    response.setHeader('Content-Type', target.endsWith('.js') ? 'text/javascript' : target.endsWith('.css') ? 'text/css' : 'text/html');
    response.end(await readFile(target));
  } catch { response.writeHead(404).end(); }
});
await new Promise((resolve) => server.listen(Number(process.env.RUVIE_E2E_FRONTEND_PORT), '127.0.0.1', resolve));
let browser;
try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.RUVIE_BROWSER_PATH || undefined });
  const page = await browser.newPage({locale: 'vi-VN', viewport: { width: 1280, height: 720 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  const picker = page.getByRole('button', { name: 'Chọn model', exact: true });
  async function login(account) {
    await page.getByLabel('Email', { exact: true }).fill(`${account}@example.test`);
    await page.getByLabel('Mật khẩu', { exact: true }).fill(process.env.RUVIE_E2E_PASSWORD);
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await picker.waitFor();
    await page.waitForFunction(() => !document.querySelector('[aria-label="Chọn model"]').disabled);
  }
  async function showView(name) {
    await showWorkspaceView(page,name);
  }
  async function connect(key) {
    await showView('Kết nối LLM');
    await page.getByLabel('Base URL', { exact: true }).fill(process.env.RUVIE_E2E_PROVIDER_URL);
    await page.getByLabel('API key (tùy chọn)', { exact: true }).fill(key);
    await page.getByRole('button', { name: 'Kết nối', exact: true }).click();
    await page.getByText('Đã lưu kết nối.', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('API key (tùy chọn)', { exact: true }).inputValue(), '');
  }
  async function chat(title, forbidden) {
    await showView('Chat');
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Where do I install the plugin?');
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await page.getByText('Answer from Alpha\'s guide.', { exact: true }).waitFor();
    const sources = page.locator('summary').filter({ hasText: 'nguồn tham khảo' });
    try { await sources.click({ timeout: 3000 }); }
    catch (error) {
      console.error('Layout:', await page.evaluate(() => ['.workspace-content', '.chat-view', '.conversation', '.composer-area', 'summary'].map((selector) => {
        const element = document.querySelector(selector);
        return { selector, height: element.getBoundingClientRect().height, scrollHeight: element.scrollHeight };
      })));
      await mkdir(fileURLToPath(new URL('../../logs/', import.meta.url)), { recursive: true });
      await page.screenshot({ path: fileURLToPath(new URL('../../logs/f006-e2e-layout.png', import.meta.url)), fullPage: true });
      throw error;
    }
    await page.getByText(title, { exact: true }).waitFor();
    assert.equal(await page.getByText(forbidden, { exact: true }).count(), 0);
  }
  const logout = () => logoutFromMenu(page);
  await login('alpha');
  await connect('alpha-provider-key');
  await showView('Chat');
  await picker.click();
  await page.getByRole('option', { name: /^B b/ }).click();
  await page.getByText('Model: B', { exact: false }).waitFor();
  await chat('Alpha guide', 'Beta guide');
  await page.reload();
  await page.getByText('Model: B', { exact: false }).waitFor();
  await logout();
  await login('beta');
  assert.ok((await picker.innerText()).includes('Model: A'), 'Beta must not inherit Alpha selection');
  await connect('beta-provider-key');
  await page.setViewportSize({ width: 1024, height: 600 });
  await chat('Beta guide', 'Alpha guide');
  await logout();
  await login('alpha');
  await page.getByText('Model: B', { exact: false }).waitFor();
  assert.equal(await page.getByLabel('API key (tùy chọn)', { exact: true }).inputValue(), '');
  assert.equal(await page.evaluate(() => localStorage.length), 0);
  assert.deepEqual(errors, []);
  console.log('Browser E2E: 2 accounts passed (model, credentials, citations, reload, login).');
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
