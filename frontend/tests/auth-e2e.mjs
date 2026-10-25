import { logoutFromMenu } from './workspace-actions.mjs';
/** Real browser -> active API -> disposable PostgreSQL; no mocked API requests. */
import assert from 'node:assert/strict';
import { createServer, request as proxyRequest } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH);
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const mime = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};
const server = createServer(async (req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  if (/^\/(auth|admin|projects|documents|llm|models|chat)(\/|$)/.test(pathname)) {
    const upstream = proxyRequest(
      new URL(req.url, process.env.RUVIE_E2E_BACKEND_URL),
      { method: req.method, headers: req.headers },
      (received) => {
        res.writeHead(received.statusCode, received.headers);
        received.pipe(res);
      },
    );
    upstream.on('error', () => res.writeHead(502).end());
    req.pipe(upstream);
    return;
  }
  const target = path.resolve(root, '.' + pathname.replace(/\/$/, '/index.html'));
  if (!target.startsWith(root + path.sep)) {
    res.writeHead(403).end();
    return;
  }
  try {
    res.setHeader('Content-Type', mime[path.extname(target)] || 'text/html');
    res.end(await readFile(target));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) =>
  server.listen(Number(process.env.RUVIE_E2E_FRONTEND_PORT), '127.0.0.1', resolve),
);
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.RUVIE_BROWSER_PATH || undefined,
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, locale: 'vi-VN' });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const email = 'browser-new@example.test',
    password = ' original-browser-password ';
  await page.goto(origin + '/?form=register');
  await page.getByLabel('Tên hiển thị', { exact: true }).fill('Nguyễn An');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  await page.getByLabel('Nhập lại mật khẩu', { exact: true }).fill(password);
  const registration = page.waitForResponse(
    (response) =>
      response.url().endsWith('/auth/register') && response.request().method() === 'POST',
  );
  await page.locator('form:has(#password_confirmation) button[type=submit]').click();
  const response = await registration;
  assert.equal(response.status(), 201);
  const user = (await response.json()).user;
  assert.equal(user.system_role, 'admin');
  await page.locator('#admin-users-heading').waitFor();
  assert.equal(new URL(page.url()).searchParams.get('view'), 'admin-users');
  await page.getByRole('navigation', { name: 'Điều hướng chính' }).waitFor();
  assert.equal(await page.locator('.account-name').innerText(), 'Nguyễn An');
  const cookies = await page.context().cookies();
  const session = cookies.find((cookie) => cookie.name === 'ruvie_session');
  assert.ok(session.httpOnly && session.secure && session.sameSite === 'Lax');
  assert.equal(await page.evaluate(() => document.cookie.includes('ruvie_session')), false);
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
  const projects = await page.evaluate(async () => await (await fetch('/projects')).json());
  assert.deepEqual(projects, { items: [] });
  await page.reload();
  await page.getByRole('navigation', { name: 'Điều hướng chính' }).waitFor();
  await page.goto(origin + '/?form=register');
  await page.getByRole('navigation', { name: 'Điều hướng chính' }).waitFor();
  assert.equal(await page.locator('.auth-form').count(), 0);
  await logoutFromMenu(page);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  assert.equal(
    await page.getByRole('link', { name: 'Tạo tài khoản quản trị viên', exact: true }).count(),
    0,
  );
  await page.goto(origin + '/?form=register');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  assert.equal(await page.getByLabel('Tên hiển thị', { exact: true }).count(), 0);
  const blocked = await page.evaluate(
    async ({ email }) => {
      const reply = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: 'Replacement',
          email,
          password: 'replacement-password',
        }),
      });
      return { status: reply.status, body: await reply.json() };
    },
    { email: email.toUpperCase() },
  );
  assert.equal(blocked.status, 409);
  assert.equal(blocked.body.detail.code, 'setup_already_completed');
  assert.equal(await page.getByLabel('Mật khẩu', { exact: true }).inputValue(), '');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await page.getByRole('navigation', { name: 'Điều hướng chính' }).waitFor();
  const restored = await page.evaluate(async () => await (await fetch('/auth/session')).json());
  assert.equal(restored.user.id, user.id);
  assert.deepEqual(errors, []);
  console.log('Auth E2E: registration, secure session, reload, logout, duplicate and login passed');
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
