/** F011 user flows against fake APIs; no development data or real provider. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {
  openSettings,
  showWorkspaceView,
  logoutFromMenu,
  ensureSidebar,
} from './workspace-actions.mjs';
import { catalog, citation } from './state-loader.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const streams = [],
  requests = [];
const fence = String.fromCharCode(96).repeat(3);
const answer =
  '# Technical answer\n\n- One\n- Two\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n' +
  fence +
  'js\nconst x = 1;\n' +
  fence +
  '\n\n[Safe](https://example.test/docs) [Blocked](javascript:alert(1))\n\n<script>window.injected=true</script>\n<img src="https://invalid.test/track">';
const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/chat') {
    let body = '';
    for await (const chunk of req) body += chunk;
    requests.push(JSON.parse(body));
    res.writeHead(200, { 'Content-Type': 'text/event-stream' });
    const send = (type, data) => {
      if (!res.destroyed) res.write('event: ' + type + '\ndata: ' + JSON.stringify(data) + '\n\n');
    };
    let finish;
    const done = new Promise((resolve) => (finish = resolve));
    streams.push({ send, finish, res });
    send('delta', { text: answer });
    await done;
    send('completed', {});
    res.end();
    return;
  }
  const target = path.resolve(root, '.' + url.pathname.replace(/\/$/, '/index.html'));
  if (!target.startsWith(root + path.sep)) {
    res.writeHead(403).end();
    return;
  }
  try {
    const mime = {
      '.js': 'text/javascript',
      '.css': 'text/css',
      '.png': 'image/png',
      '.svg': 'image/svg+xml',
    };
    res.setHeader('Content-Type', mime[path.extname(target)] || 'text/html');
    res.end(await readFile(target));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = 'http://127.0.0.1:' + server.address().port;
let browser,
  checks = 0,
  searches = 0;
const errors = [],
  outside = [];
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.RUVIE_BROWSER_PATH || undefined,
  });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 768 },
    locale: 'vi-VN',
    deviceScaleFactor: 2,
    permissions: ['clipboard-read', 'clipboard-write'],
  });
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  page.on('pageerror', (e) => errors.push(e.message));
  await page.route('**/*', async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (route.request().url().startsWith('https://invalid.test')) {
      outside.push(route.request().url());
      return route.abort();
    }
    const json = (value, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(value) });
    if (pathname === '/auth/session')
      return json({ user: { id: 'u', display_name: 'Nguyễn An' }, csrf_token: 'csrf' });
    if (pathname === '/auth/logout') return route.fulfill({ status: 204 });
    if (pathname === '/projects') return json({ items: [{ id: 'p', name: 'Project', code: 'P' }] });
    if (pathname === '/models') return json(catalog);
    if (pathname === '/llm/connection')
      return json({
        source: 'personal',
        base_url: 'https://provider.test/v1',
        has_api_key: true,
        selected_model_id: 'one',
      });
    if (pathname === '/documents/retrieve') {
      searches++;
      assert.deepEqual(JSON.parse(route.request().postData()), { query: 'install', limit: 10 });
      return json([
        { chunk_id: 'ch', document_id: 'd', text: 'Readable <script>excerpt</script>', citation },
      ]);
    }
    if (pathname === '/documents/upload')
      return json({ document_id: 'd', revision_id: 'r', job_id: 'j', status: 'pending' }, 202);
    if (pathname === '/documents/revisions/r/status')
      return json({ revision_id: 'r', status: 'ready', error_code: null });
    return route.continue();
  });
  await page.goto(origin);
  await page.getByRole('button', { name: 'Chọn model', exact: true }).waitFor();
  await page.locator('#question').fill('Original');
  await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
  await page.locator('.answer').getByRole('heading', { name: 'Technical answer' }).waitFor();
  assert.equal(await page.locator('.answer table').count(), 1);
  assert.equal(await page.locator('.answer pre').innerText(), 'const x = 1;');
  checks += 2;
  assert.equal(await page.locator('.answer a').count(), 1);
  assert.equal(await page.evaluate(() => window.injected), undefined);
  assert.deepEqual(outside, []);
  checks += 3;
  streams[0].send('delta', {
    text: '\n\n' + Array(40).fill('Long readable paragraph.').join('\n\n'),
  });
  await page.waitForFunction(() =>
    document.querySelector('.answer').innerText.includes('Long readable paragraph.'),
  );
  assert.ok(
    await page
      .locator('.conversation')
      .evaluate((e) => e.scrollHeight - e.scrollTop - e.clientHeight < 80),
    'streamed Markdown follows the new rendered height',
  );
  checks++;
  await page.locator('.conversation').evaluate((e) => {
    e.scrollTop = 0;
    e.dispatchEvent(new Event('scroll'));
  });
  await page.locator('.jump-bottom').waitFor();
  streams[0].send('delta', { text: '\n\nReader tail' });
  await page.getByText('Reader tail', { exact: true }).waitFor();
  assert.equal(await page.locator('.conversation').evaluate((e) => e.scrollTop), 0);
  checks++;
  await page.locator('.jump-bottom').click();
  assert.ok(
    await page
      .locator('.conversation')
      .evaluate((e) => e.scrollHeight - e.scrollTop - e.clientHeight < 80),
  );
  checks++;
  streams[0].send('citations', { citations: [citation] });
  assert.equal(await page.locator('.sources').count(), 0);
  checks++;
  await page.getByRole('button', { name: 'Dừng trả lời', exact: true }).click();
  await page.getByText('Đã dừng', { exact: true }).waitFor();
  assert.ok((await page.locator('.answer').innerText()).includes('Technical answer'));
  assert.equal(await page.locator('.sources').count(), 0);
  checks += 2;
  await page.getByRole('button', { name: 'Thử lại câu trả lời', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.response-status'));
  await page.waitForFunction(() => document.querySelector('.answer h1'));
  assert.equal(requests.length, 2);
  assert.deepEqual(requests[1], { message: 'Original', model_id: 'one' });
  assert.equal(await page.locator('.turn').count(), 1);
  checks += 3;
  streams[1].send('citations', { citations: [citation] });
  streams[1].finish();
  await page.getByRole('button', { name: 'Trả lời lại', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Sao chép code', exact: true }).click();
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), 'const x = 1;');
  checks++;
  await page.getByRole('button', { name: 'Sao chép câu trả lời', exact: true }).click();
  assert.equal(
    (await page.evaluate(() => navigator.clipboard.readText())).replaceAll(
      String.fromCharCode(13) + String.fromCharCode(10),
      String.fromCharCode(10),
    ),
    answer,
  );
  checks++;
  await page.evaluate(() =>
    Object.defineProperty(navigator.clipboard, 'writeText', {
      configurable: true,
      value: async () => {
        throw new Error('denied');
      },
    }),
  );
  await page.getByRole('button', { name: 'Sao chép code', exact: true }).click();
  await page
    .getByText('Không thể sao chép. Hãy chọn và sao chép nội dung thủ công.', { exact: true })
    .waitFor();
  checks++;
  await openSettings(page, 'general');
  await page.locator('#account-language').selectOption('ru-RU');
  await page
    .getByText('Не удалось скопировать. Выделите и скопируйте текст вручную.', { exact: true })
    .waitFor();
  checks++;
  await page.locator('#account-language').selectOption('vi-VN');
  await page.locator('.settings-dialog').press('Escape');
  await page.locator('.auth-toast-close').click();
  await page.getByRole('button', { name: 'Thu gọn code', exact: true }).click();
  assert.equal(await page.locator('.answer pre').isVisible(), false);
  await page.getByRole('button', { name: 'Hiện code', exact: true }).click();
  assert.equal(await page.locator('.answer pre').isVisible(), true);
  checks += 2;
  await page.locator('.sources summary').click();
  await page.locator('.sources').getByRole('button', { name: 'Guide', exact: true }).click();
  await page.locator('.source-dialog').waitFor({ state: 'visible' });
  assert.equal(await page.locator('.source-dialog details').getAttribute('open'), null);
  checks++;
  await page.locator('.source-dialog').press('Escape');
  assert.equal(
    await page.locator('.sources button').evaluate((e) => e === document.activeElement),
    true,
  );
  checks++;
  await page.locator('#question').fill('Retained draft');
  await page.locator('.attach-trigger').click();
  await page.locator('.upload-dialog').waitFor({ state: 'visible' });
  assert.equal(await page.locator('.upload-form').count(), 1);
  checks++;
  await page.getByLabel('Project', { exact: true }).selectOption('p');
  await page.getByLabel('Tên tài liệu', { exact: true }).fill('Retained title');
  await page.getByLabel('Phần mềm', { exact: true }).fill('CAD');
  await page.getByLabel('Phiên bản', { exact: true }).fill('1');
  await page
    .getByLabel('File', { exact: true })
    .setInputFiles({ name: 'guide.txt', mimeType: 'text/plain', buffer: Buffer.from('guide') });
  await page.locator('.upload-dialog').press('Escape');
  assert.equal(await page.locator('#question').inputValue(), 'Retained draft');
  checks++;
  await showWorkspaceView(page, 'Tài liệu');
  assert.equal(
    await page.getByLabel('File', { exact: true }).evaluate((e) => e.files[0].name),
    'guide.txt',
  );
  checks++;
  await page.getByRole('button', { name: 'Tải lên', exact: true }).click();
  await page.getByText('Sẵn sàng', { exact: true }).waitFor();
  checks++;
  await showWorkspaceView(page, 'Tìm kiếm');
  const box = page.getByRole('searchbox');
  await box.fill('install');
  assert.equal(searches, 0);
  await box.press('Enter');
  await page.locator('.search-results button').first().waitFor();
  assert.equal(searches, 1);
  await page.locator('.search-results button').first().click();
  assert.ok(
    (await page.locator('.search-detail').innerText()).includes(
      'Readable <script>excerpt</script>',
    ),
  );
  assert.equal(await page.evaluate(() => window.injected), undefined);
  checks += 3;
  await openSettings(page, 'general');
  await page.locator('#account-language').selectOption('ru-RU');
  await page.locator('.settings-dialog').press('Escape');
  assert.equal(await box.inputValue(), 'install');
  checks++;
  await mkdir(fileURLToPath(new URL('../../logs/f011/', import.meta.url)), { recursive: true });
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/f011/search-desktop.png', import.meta.url)),
  });
  await page.setViewportSize({ width: 375, height: 812 });
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
    true,
  );
  checks++;
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/f011/search-mobile.png', import.meta.url)),
  });
  await ensureSidebar(page);
  await page.locator('.sidebar-brand').click();
  for (const size of [
    { width: 1920, height: 1080 },
    { width: 1366, height: 768 },
    { width: 1280, height: 605 },
    { width: 1024, height: 600 },
    { width: 768, height: 1024 },
    { width: 375, height: 812 },
    { width: 320, height: 568 },
    { width: 640, height: 360 },
  ]) {
    await page.setViewportSize(size);
    await page.locator('.send-button').scrollIntoViewIfNeeded();
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      true,
      'Markdown viewport has no horizontal page overflow',
    );
    assert.equal(await page.locator('.send-button').isVisible(), true);
    checks += 2;
    await page.screenshot({
      path: fileURLToPath(new URL('../../logs/f011/chat-' + size.width + '.png', import.meta.url)),
    });
  }
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.locator('.attach-trigger').click();
  await page.locator('.upload-dialog').waitFor({ state: 'visible' });
  assert.equal(
    await page
      .locator('.upload-dialog')
      .evaluate((e) => e.getBoundingClientRect().right <= innerWidth),
    true,
  );
  checks++;
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/f011/upload-zoom.png', import.meta.url)),
  });
  await page.locator('.upload-dialog').press('Escape');
  await logoutFromMenu(page);
  await page.locator('.auth-page').waitFor();
  assert.equal(await page.locator('.search-results,.upload-dialog,.source-dialog').count(), 0);
  checks++;
  assert.deepEqual(errors, []);
  console.log('F011 UX browser: ' + checks + ' checks passed');
} finally {
  for (const stream of streams) stream.finish();
  if (browser) await browser.close();
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
}
