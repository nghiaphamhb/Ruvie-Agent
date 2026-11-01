/** F019 desktop history acceptance at the HTTP boundary, with no application database. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root = fileURLToPath(new URL('../dist/', import.meta.url));
const server = createServer(async (req, res) => {
  const target = path.resolve(
    root,
    '.' + new URL(req.url, 'http://test').pathname.replace(/\/$/, '/index.html'),
  );
  if (!target.startsWith(root)) return res.writeHead(403).end();
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
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.RUVIE_BROWSER_PATH || undefined,
});
try {
  for (const locale of ['en-US', 'vi-VN', 'ru-RU']) {
    const labels = JSON.parse(
      await readFile(
        new URL(`../src/lib/i18n/locales/${locale}/translation.json`, import.meta.url),
        'utf8',
      ),
    );
    const context = await browser.newContext({
      viewport: { width: 1366, height: 900 },
      locale,
      colorScheme: locale === 'ru-RU' ? 'dark' : 'light',
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    let historyUnavailable = false;
    let chat = null,
      turns = [],
      serial = 0;
    await page.route('**/*', async (route) => {
      const request = route.request(),
        url = new URL(request.url()),
        api = url.pathname,
        method = request.method();
      const json = (data, status = 200) =>
        route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
      if (api === '/auth/setup') return json({ requires_initial_admin: false });
      if (api === '/auth/session')
        return json({
          user: { id: 'owner', display_name: 'Owner', system_role: 'user' },
          csrf_token: 'csrf',
        });
      if (api === '/auth/presence') return json({});
      if (api === '/projects') return json({ items: [] });
      if (api === '/llm/connection')
        return json({ configured: true, configuration_version: 1, selected_model_id: 'one' });
      if (api === '/models')
        return json({
          models: [{ id: 'one', name: 'One' }],
          selected_model_id: 'one',
          selection_required: false,
          configuration_version: 1,
        });
      if (api === '/conversations') return json({ items: chat ? [chat] : [], next_cursor: null });
      if (api.startsWith('/conversations/')) {
        if (method === 'GET' && historyUnavailable)
          return json({ detail: { code: 'history_unavailable' } }, 503);
        if (method === 'PATCH') {
          assert.equal(request.headers()['x-csrf-token'], 'csrf');
          chat = { ...chat, title: request.postDataJSON().title, version: chat.version + 1 };
          return json(chat);
        }
        if (method === 'DELETE') {
          chat = null;
          turns = [];
          return route.fulfill({ status: 204 });
        }
        return chat
          ? json({ conversation: chat, turns, next_cursor: null })
          : json({ detail: { code: 'conversation_not_found' } }, 404);
      }
      if (api === '/chat') {
        const body = request.postDataJSON();
        assert.match(body.request_id, /^[a-f0-9-]{36}$/);
        assert.equal(request.headers()['x-csrf-token'], 'csrf');
        chat ??= {
          id: '00000000-0000-0000-0000-000000000001',
          title: body.message,
          version: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        const turn = {
          id: 'turn' + ++serial,
          question: body.message,
          answer: 'Saved answer ' + serial,
          model_id: 'one',
          attempt_id: 'attempt' + serial,
          status: 'completed',
          citations: [],
          content_unavailable: false,
        };
        turns.push(turn);
        return route.fulfill({
          contentType: 'text/event-stream',
          body: `event: accepted\ndata: ${JSON.stringify({ conversation_id: chat.id, turn_id: turn.id, attempt_id: turn.attempt_id })}\n\nevent: delta\ndata: ${JSON.stringify({ text: turn.answer })}\n\nevent: completed\ndata: {}\n\n`,
        });
      }
      return route.continue();
    });
    await page.goto(origin);
    const handle = page.getByRole('separator');
    await handle.waitFor();
    const initialWidth = await page
      .locator('.workspace-sidebar')
      .evaluate((el) => el.getBoundingClientRect().width);
    const bounds = await handle.boundingBox();
    await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + 100);
    await page.mouse.down();
    assert.equal(await handle.evaluate((el) => getComputedStyle(el).outlineStyle), 'none');
    assert.equal(
      await handle.evaluate((el) => getComputedStyle(el).backgroundColor),
      'rgba(0, 0, 0, 0)',
    );
    await page.mouse.move(bounds.x + 100, bounds.y + 100);
    await page.mouse.up();
    assert.ok(
      (await page
        .locator('.workspace-sidebar')
        .evaluate((el) => el.getBoundingClientRect().width)) >
        initialWidth + 80,
    );
    const wider = await handle.boundingBox();
    await page.mouse.move(wider.x + wider.width / 2, wider.y + 100);
    await page.mouse.down();
    await page.mouse.move(wider.x - 60, wider.y + 100);
    await page.mouse.up();
    assert.ok(
      (await page
        .locator('.workspace-sidebar')
        .evaluate((el) => el.getBoundingClientRect().width)) <
        initialWidth + 60,
    );
    await handle.focus();
    await page.keyboard.press('Home');
    assert.equal(await handle.getAttribute('aria-valuenow'), '220');
    await page.keyboard.press('End');
    assert.equal(await handle.getAttribute('aria-valuenow'), '480');
    await page.keyboard.press('ArrowLeft');
    assert.equal(await handle.getAttribute('aria-valuenow'), '464');
    await page.keyboard.press('Home');
    await page.locator('#question').fill('History question');
    await page.waitForFunction(() => !document.querySelector('#question')?.disabled);
    await page.locator('#question').press('Enter');
    await page.getByText('Saved answer 1', { exact: true }).waitFor();
    assert.equal(new URL(page.url()).searchParams.get('conversation'), chat.id);
    assert.equal(
      await page
        .locator('.chat-view')
        .getByRole('button', { name: labels['history.refresh'], exact: true })
        .count(),
      0,
    );
    const row = page.locator('.workspace-sidebar .history-row').first();
    await row.hover();
    const pin = row.getByRole('button', { name: labels['history.pinSoon'], exact: true });
    assert.equal(await pin.count(), 1);
    assert.equal(await pin.isDisabled(), true);
    assert.equal(await pin.locator('svg').count(), 1);
    assert.equal(await row.evaluate((el) => getComputedStyle(el).borderRadius), '6px');
    assert.notEqual(
      await row.evaluate((el) => getComputedStyle(el).backgroundColor),
      'rgba(0, 0, 0, 0)',
    );
    await page.reload();
    await page.getByText('Saved answer 1', { exact: true }).waitFor();
    historyUnavailable = true;
    await page.reload();
    const refresh = page
      .locator('.chat-view')
      .getByRole('button', { name: labels['history.refresh'], exact: true });
    await refresh.waitFor();
    historyUnavailable = false;
    await refresh.click();
    await page.getByText('Saved answer 1', { exact: true }).waitFor();
    assert.equal(await refresh.count(), 0);
    await page.locator('#question').fill('Next question');
    await page.locator('#question').press('Enter');
    await page.getByText('Saved answer 2', { exact: true }).waitFor();
    assert.equal(turns.length, 2);
    await page
      .locator('.sidebar-links')
      .getByRole('button', { name: labels['workspace.newChat'], exact: true })
      .click();
    await page.locator('.chat-welcome').waitFor();
    assert.equal(serial, 2);
    assert.ok(chat);
    await page.goBack();
    await page.getByText('Saved answer 2', { exact: true }).waitFor();
    await page.goForward();
    await page.locator('.chat-welcome').waitFor();
    await page.goBack();
    await page.getByText('Saved answer 2', { exact: true }).waitFor();
    const sidebar = page.locator('.sidebar-sections');
    await sidebar.locator('summary').click();
    await sidebar.getByRole('button', { name: labels['history.rename'], exact: true }).click();
    const dialog = page.locator('dialog[open]');
    await dialog.locator('input').fill('x'.repeat(121));
    assert.equal(
      await dialog.getByRole('button', { name: labels['history.save'], exact: true }).isDisabled(),
      true,
    );
    await dialog.locator('input').fill('😀'.repeat(120));
    assert.equal(
      await dialog.getByRole('button', { name: labels['history.save'], exact: true }).isEnabled(),
      true,
    );
    await dialog.locator('input').fill('Renamed history');
    await dialog.getByRole('button', { name: labels['history.save'], exact: true }).click();
    await sidebar.getByRole('button', { name: 'Renamed history', exact: true }).waitFor();
    await sidebar.locator('summary').focus();
    await page.keyboard.press('Enter');
    await sidebar.getByRole('button', { name: labels['history.delete'], exact: true }).click();
    assert.ok((await dialog.textContent()).includes('Renamed history'));
    await dialog.getByRole('button', { name: labels['history.cancel'], exact: true }).click();
    assert.ok(chat);
    assert.equal(
      await sidebar.locator('summary').evaluate((element) => element === document.activeElement),
      true,
      'Cancelling deletion restores focus to the conversation menu',
    );
    await sidebar.locator('summary').click();
    await sidebar.getByRole('button', { name: labels['history.delete'], exact: true }).click();
    await dialog.getByRole('button', { name: labels['history.delete'], exact: true }).click();
    await page.locator('.chat-welcome').waitFor();
    assert.equal(chat, null);
    assert.equal(new URL(page.url()).searchParams.has('conversation'), false);
    assert.deepEqual(errors, []);
    await context.close();
    console.log(`PASS F019 history flow ${locale}`);
  }
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
