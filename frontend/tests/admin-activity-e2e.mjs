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
let browser;
const contexts = [];
const errors = [];
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.RUVIE_BROWSER_PATH || undefined,
  });
  async function login(email) {
    const context = await browser.newContext({ locale: 'vi-VN' });
    contexts.push(context);
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(origin);
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Mật khẩu', { exact: true }).fill(currentPassword);
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await page.locator('.workspace-shell').waitFor();
    return { context, page };
  }
  const admin = await login('alpha@example.test');
  const target1 = await login('beta@example.test');
  const target2 = await login('beta@example.test');
  const other = await login('gamma@example.test');
  await admin.page.goto(origin + '/?view=admin-users');
  const lock = admin.page.getByRole('button', { name: /Khóa tài khoản/ }).first();
  await lock.waitFor();
  const row = admin.page.getByRole('row').filter({ hasText: 'beta@example.test' });
  await row.getByRole('button', { name: /Khóa tài khoản/ }).click();
  await admin.page
    .getByRole('dialog', { name: 'Khóa tài khoản?' })
    .getByRole('button', { name: 'Khóa tài khoản', exact: true })
    .click();
  await row.getByRole('button', { name: /Mở lại tài khoản/ }).waitFor();
  const probeContext = await browser.newContext({ locale: 'vi-VN' });
  contexts.push(probeContext);
  const probe = await probeContext.newPage();
  await probe.goto(origin);
  const disabled = await probe.evaluate(async (password) => {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'beta@example.test', password }),
    });
    return { status: response.status, body: await response.json() };
  }, currentPassword);
  assert.equal(disabled.status, 403);
  assert.equal(disabled.body.detail.code, 'account_disabled');
  const wrong = await probe.evaluate(
    async () =>
      (
        await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'beta@example.test', password: 'wrong-password' }),
        })
      ).status,
  );
  assert.equal(wrong, 401);
  assert.equal(await probe.evaluate(async () => (await fetch('/auth/session')).status), 401);
  assert.equal(await target1.page.evaluate(async () => (await fetch('/auth/session')).status), 401);
  assert.equal(await target2.page.evaluate(async () => (await fetch('/auth/session')).status), 401);
  assert.equal(await other.page.evaluate(async () => (await fetch('/auth/session')).status), 200);
  assert.equal(await admin.page.evaluate(async () => (await fetch('/auth/session')).status), 200);
  await row.getByRole('button', { name: /Mở lại tài khoản/ }).click();
  await admin.page
    .getByRole('dialog', { name: 'Mở lại tài khoản?' })
    .getByRole('button', { name: 'Mở lại tài khoản', exact: true })
    .click();
  await row.getByRole('button', { name: /Khóa tài khoản/ }).waitFor();
  assert.equal(await target1.page.evaluate(async () => (await fetch('/auth/session')).status), 401);
  assert.equal(await target2.page.evaluate(async () => (await fetch('/auth/session')).status), 401);
  const fresh = await login('beta@example.test');
  assert.equal(await fresh.page.evaluate(async () => (await fetch('/auth/session')).status), 200);
  assert.deepEqual(errors, []);
  console.log('F015 activity E2E checks passed: 5');
} finally {
  for (const context of contexts) await context.close();
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
