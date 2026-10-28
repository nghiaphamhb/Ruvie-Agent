/** Password change UI against the active API and disposable PostgreSQL fixture. */
import assert from 'node:assert/strict';
import { createServer, request as proxyRequest } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const { chromium } = createRequire(import.meta.url)(process.env.RUVIE_PLAYWRIGHT_PATH);
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const server = createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  if (/^\/(auth|admin|projects|documents|llm|models|chat)(\/|$)/.test(pathname)) {
    const upstream = proxyRequest(
      new URL(req.url, process.env.RUVIE_E2E_BACKEND_URL),
      { method: req.method, headers: req.headers },
      (response) => {
        res.writeHead(response.statusCode, response.headers);
        response.pipe(res);
      },
    );
    upstream.on('error', () => res.writeHead(502).end());
    req.pipe(upstream);
    return;
  }
  const target = path.resolve(root, '.' + pathname.replace(/\/$/, '/index.html'));
  if (!target.startsWith(root + path.sep)) return res.writeHead(403).end();
  readFile(target).then(
    (body) => {
      res.setHeader(
        'Content-Type',
        {
          '.js': 'text/javascript',
          '.css': 'text/css',
          '.svg': 'image/svg+xml',
          '.png': 'image/png',
        }[path.extname(target)] || 'text/html',
      );
      res.end(body);
    },
    () => res.writeHead(404).end(),
  );
});
await new Promise((resolve) =>
  server.listen(Number(process.env.RUVIE_E2E_FRONTEND_PORT), '127.0.0.1', resolve),
);
const origin = `http://127.0.0.1:${server.address().port}`;
const currentPassword = process.env.RUVIE_E2E_CURRENT_PASSWORD;
const newPassword = process.env.RUVIE_E2E_NEW_PASSWORD;
let browser;
const contexts = [];
const errors = [];
let checks = 0;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.RUVIE_BROWSER_PATH || undefined,
  });
  async function signIn(email, password) {
    const context = await browser.newContext({ locale: 'vi-VN' });
    contexts.push(context);
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(origin);
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await page.locator('.workspace-shell').waitFor();
    return { context, page };
  }
  const actorEmail = process.env.RUVIE_E2E_ACTOR_EMAIL;
  const otherEmail = process.env.RUVIE_E2E_OTHER_EMAIL;
  const actorA1 = await signIn(actorEmail, currentPassword);
  const actorA2 = await signIn(actorEmail, currentPassword);
  const otherB1 = await signIn(otherEmail, process.env.RUVIE_E2E_OTHER_PASSWORD);
  const before = await actorA1.page.evaluate(async () => (await fetch('/auth/session')).json());
  const cookiesBefore = await actorA1.context.cookies();

  await actorA1.page.locator('.account-trigger').click();
  await actorA1.page.getByRole('menuitem', { name: 'Cài đặt', exact: true }).click();
  await actorA1.page.getByRole('tab', { name: 'Tài khoản' }).click();
  await actorA1.page.getByLabel('Mật khẩu hiện tại', { exact: true }).fill(currentPassword);
  await actorA1.page.getByLabel('Mật khẩu mới', { exact: true }).fill(newPassword);
  await actorA1.page.getByLabel('Xác nhận mật khẩu mới', { exact: true }).fill(newPassword);
  const changed = actorA1.page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/auth/password' &&
      response.request().method() === 'POST',
  );
  await actorA1.page.getByRole('button', { name: 'Đổi mật khẩu' }).click();
  const response = await changed;
  assert.equal(response.status(), 204);
  const headers = await response.allHeaders();
  assert.equal(headers['cache-control'], 'no-store');
  assert.equal(headers['set-cookie'], undefined);
  await actorA1.page
    .locator('[data-sonner-toast]')
    .filter({ hasText: 'Đã đổi mật khẩu' })
    .waitFor();
  assert.equal(
    await actorA1.page.getByLabel('Mật khẩu hiện tại', { exact: true }).inputValue(),
    '',
  );
  assert.deepEqual(
    await actorA1.page.evaluate(async () => (await fetch('/auth/session')).json()),
    before,
  );
  assert.deepEqual(await actorA1.context.cookies(), cookiesBefore);
  assert.equal(await actorA2.page.evaluate(async () => (await fetch('/auth/session')).status), 401);
  assert.equal(await otherB1.page.evaluate(async () => (await fetch('/auth/session')).status), 200);
  checks += 5;

  const probe = await browser.newContext({ locale: 'vi-VN' });
  contexts.push(probe);
  const login = (password) =>
    probe.request.post(`${origin}/auth/login`, {
      headers: { Origin: origin },
      data: { email: actorEmail, password },
    });
  assert.equal((await login(currentPassword)).status(), 401);
  assert.equal((await login(newPassword)).status(), 200);
  checks += 2;
  assert.deepEqual(errors, []);
} finally {
  for (const context of contexts) await context.close();
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
console.log(`F014 password-change E2E checks passed: ${checks}`);
