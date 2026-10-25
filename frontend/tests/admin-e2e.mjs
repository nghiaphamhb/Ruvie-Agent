/** Real account creation UI -> active API -> disposable PostgreSQL. Only a response is dropped. */
import assert from 'node:assert/strict';
import { createServer, request as proxyRequest } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const { chromium } = createRequire(import.meta.url)(process.env.RUVIE_PLAYWRIGHT_PATH);
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
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
    res.setHeader(
      'Content-Type',
      {
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
      }[path.extname(target)] || 'text/html',
    );
    res.end(await readFile(target));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) =>
  server.listen(Number(process.env.RUVIE_E2E_FRONTEND_PORT), '127.0.0.1', resolve),
);
const origin = `http://127.0.0.1:${server.address().port}`;
const password = ' provisioned-password-123 ';
let browser;
const errors = [];
let checks = 0;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.RUVIE_BROWSER_PATH,
  });
  async function login(email, secret = password) {
    const context = await browser.newContext({ locale: 'vi-VN' });
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(origin);
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Mật khẩu', { exact: true }).fill(secret);
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await page.locator('.workspace-shell').waitFor();
    return page;
  }
  const session = (page) => page.evaluate(async () => (await fetch('/auth/session')).json());
  async function administration(page) {
    await page.locator('.account-trigger').click();
    await page.getByRole('menuitem', { name: 'Quản trị', exact: true }).click();
    await page.locator('#admin-users-heading').waitFor();
  }
  async function form(page, email, role = 'user', secret = password) {
    await page.locator('#admin-users-heading').locator('..').getByRole('button').click();
    await page.locator('#admin-name').fill(email.split('@')[0]);
    await page.locator('#admin-email').fill(email);
    await page.locator('#admin-password').fill(secret);
    await page.locator('#admin-role').selectOption(role);
  }
  async function create(page, email, role = 'user') {
    const before = await session(page),
      cookies = await page.context().cookies();
    await form(page, email, role);
    const response = page.waitForResponse(
      (reply) =>
        new URL(reply.url()).pathname === '/admin/users' && reply.request().method() === 'POST',
    );
    await page
      .getByRole('form')
      .getByRole('button', { name: 'Tạo tài khoản', exact: true })
      .click();
    const reply = await response;
    assert.equal(reply.status(), 201);
    assert.equal((await reply.allHeaders())['set-cookie'], undefined);
    await page.getByRole('heading', { name: 'Đã tạo tài khoản', exact: true }).waitFor();
    assert.deepEqual(await session(page), before);
    assert.deepEqual(await page.context().cookies(), cookies);
    assert.equal(await page.locator('#admin-password').count(), 0);
    checks++;
    return (await reply.json()).user;
  }
  const actor = await login('alpha@example.test', 'f005-test-password');
  await administration(actor);
  const original = await session(actor);
  const user = await create(actor, 'employee@accounts.test');
  const admin = await create(actor, 'manager@accounts.test', 'admin');
  assert.equal(user.system_role, 'user');
  assert.equal(admin.system_role, 'admin');
  assert.equal(Number.isFinite(Date.parse(user.created_at)), true);
  assert.equal(Number.isFinite(Date.parse(admin.created_at)), true);
  const previousEmployeeSession = await login('employee@accounts.test');
  await actor.getByRole('button', { name: 'Chỉnh sửa employee', exact: true }).waitFor();
  await actor.getByRole('button', { name: 'Chỉnh sửa employee', exact: true }).click();
  const editUser = actor.getByRole('dialog', { name: 'Chỉnh sửa người dùng' });
  await editUser.waitFor();
  const replacementPassword = '  reset-password-456  ';
  await editUser.getByLabel('Mật khẩu mới').fill(replacementPassword);
  const resetResponse = actor.waitForResponse(
    (reply) =>
      new URL(reply.url()).pathname === `/admin/users/${user.id}` &&
      reply.request().method() === 'PATCH',
  );
  await editUser.getByRole('button', { name: 'Lưu', exact: true }).click();
  assert.equal((await resetResponse).status(), 200);
  await actor
    .getByText('Mật khẩu đã được cập nhật và các phiên của người dùng đã đăng xuất.', {
      exact: true,
    })
    .waitFor();
  assert.equal(await editUser.isVisible(), true);
  assert.equal(await editUser.getByLabel('Mật khẩu mới').inputValue(), '');
  assert.equal(
    await previousEmployeeSession.evaluate(async () => (await fetch('/auth/session')).status),
    401,
  );
  await previousEmployeeSession.context().close();
  const replacementLogin = await login('employee@accounts.test', replacementPassword);
  assert.equal((await session(replacementLogin)).user.id, user.id);
  await replacementLogin.context().close();
  await editUser.getByRole('button', { name: 'Đóng', exact: true }).click();
  checks++;
  await form(actor, 'EMPLOYEE@accounts.test', 'admin', 'different-password-123');
  await actor.getByRole('form').getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await actor.locator('#admin-email-error').waitFor();
  assert.equal(await actor.locator('#admin-password').inputValue(), '');
  await actor.getByRole('button', { name: 'Hủy', exact: true }).click();
  checks++;

  // Let the real backend commit, then lose only its response. Verify by exact email; never POST again.
  let posts = 0;
  await actor.route('**/admin/users', async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    posts++;
    const response = await route.fetch({ maxRetries: 0, maxRedirects: 0 });
    assert.equal(response.status(), 201);
    await route.abort();
  });
  await form(actor, 'lost@accounts.test');
  await actor.getByRole('form').getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await actor.getByText('Chưa xác định được kết quả tạo tài khoản.', { exact: false }).waitFor();
  assert.equal(await actor.locator('#admin-password').inputValue(), '');
  await actor.getByRole('button', { name: 'Kiểm tra email đã gửi', exact: true }).click();
  await actor
    .getByRole('heading', { name: 'Tài khoản hiện có để đối chiếu', exact: true })
    .waitFor();
  assert.equal(
    await actor.getByRole('heading', { name: 'Đã tạo tài khoản', exact: true }).count(),
    0,
  );
  assert.equal(posts, 1);
  assert.deepEqual(await session(actor), original);
  checks++;
  await actor.unroute('**/admin/users');
  await actor
    .getByRole('dialog', { name: 'Tạo tài khoản', exact: true })
    .getByRole('button', { name: 'Hủy', exact: true })
    .click();

  // Commit a password reset in PostgreSQL, drop only its PATCH response, and ensure
  // the UI verifies the actor session without reading target metadata or retrying.
  const lostAccount = await actor.evaluate(async () => {
    const response = await fetch('/admin/users?email=lost%40accounts.test');
    return (await response.json()).users[0];
  });
  await actor
    .getByRole('searchbox', { name: 'Tìm theo tên hoặc email' })
    .fill('lost@accounts.test');
  await actor.getByRole('button', { name: 'Chỉnh sửa lost', exact: true }).waitFor();
  await actor.getByRole('button', { name: 'Chỉnh sửa lost', exact: true }).click();
  const uncertainEdit = actor.getByRole('dialog', { name: 'Chỉnh sửa người dùng' });
  let resetPatches = 0,
    metadataReads = 0;
  const watchMetadata = (request) => {
    const url = new URL(request.url());
    if (url.pathname === `/admin/users/${lostAccount.id}` && request.method() === 'GET')
      metadataReads++;
  };
  actor.on('request', watchMetadata);
  await actor.route(`**/admin/users/${lostAccount.id}`, async (route) => {
    if (route.request().method() !== 'PATCH') return route.continue();
    resetPatches++;
    const committed = await route.fetch({ maxRetries: 0, maxRedirects: 0 });
    assert.equal(committed.status(), 200);
    await route.abort();
  });
  const uncertainResetPassword = '  uncertain-reset-789  ';
  await uncertainEdit.getByLabel('Mật khẩu mới').fill(uncertainResetPassword);
  await uncertainEdit.getByRole('button', { name: 'Lưu', exact: true }).click();
  await actor
    .getByText('Chưa xác nhận được thay đổi. Hãy kiểm tra lại thông tin và thử sau.', {
      exact: true,
    })
    .waitFor();
  assert.equal(resetPatches, 1);
  assert.equal(metadataReads, 0);
  assert.equal(await uncertainEdit.isVisible(), true);
  actor.off('request', watchMetadata);
  await actor.unroute(`**/admin/users/${lostAccount.id}`);
  const resetRecipient = await login('lost@accounts.test', uncertainResetPassword);
  assert.equal((await session(resetRecipient)).user.id, lostAccount.id);
  await resetRecipient.context().close();
  checks++;

  for (const [email, role, secret] of [
    ['employee@accounts.test', 'user', replacementPassword],
    ['manager@accounts.test', 'admin', password],
  ]) {
    const page = await login(email, secret);
    const identity = await session(page);
    assert.equal(identity.user.system_role, role);
    const isolation = await page.evaluate(async (revision) => {
      const identity = await (await fetch('/auth/session')).json();
      const projects = await (await fetch('/projects')).json();
      const status = await fetch('/documents/revisions/' + revision + '/status');
      const retrieval = await fetch('/documents/retrieve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': identity.csrf_token },
        body: JSON.stringify({ query: 'F012_PRIVATE_GUIDE' }),
      });
      const answer = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': identity.csrf_token },
        body: JSON.stringify({ message: 'F012_PRIVATE_GUIDE' }),
      });
      const lookup = await fetch('/admin/users?email=alpha%40example.test');
      return {
        projects,
        status: status.status,
        retrieved: await retrieval.text(),
        answer: await answer.text(),
        lookup: lookup.status,
      };
    }, process.env.RUVIE_E2E_PRIVATE_REVISION);
    assert.deepEqual(isolation.projects, { items: [] });
    assert.equal(isolation.status, 404);
    assert.equal(isolation.lookup, role === 'user' ? 403 : 200);
    assert.equal(isolation.retrieved.includes('F012_PRIVATE_GUIDE'), false);
    assert.equal(isolation.answer.includes(process.env.RUVIE_E2E_PRIVATE_REVISION), false);
    assert.match(isolation.answer, /event: completed/);
    checks++;
    await page.goto(origin + '/?view=admin-users');
    if (role === 'user') {
      await page.locator('#question').waitFor();
      assert.equal(await page.locator('.account-admin').count(), 0);
    } else {
      await page.locator('#admin-users-heading').waitFor();
      await create(page, 'delegated-user@accounts.test');
      await create(page, 'delegated-admin@accounts.test', 'admin');
    }
  }
  const lost = await login('lost@accounts.test', uncertainResetPassword);
  assert.equal((await session(lost)).user.system_role, 'user');
  checks++;
  assert.deepEqual(await session(actor), original);
  assert.equal(
    await actor.evaluate(() =>
      JSON.stringify({ ...localStorage, ...sessionStorage }).includes('provisioned-password'),
    ),
    false,
  );
  assert.deepEqual(errors, []);
  console.log(
    `Admin E2E: ${checks} groups passed; real creation, recipient login, delegation, isolation and response loss`,
  );
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
