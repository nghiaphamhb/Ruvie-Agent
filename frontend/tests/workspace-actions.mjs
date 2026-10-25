/** User-facing navigation helpers for workspace pages and account settings. */
const settingsReturn = new WeakMap();
export async function ensureSidebar(page) {
  await page.locator('.workspace-sidebar').waitFor({ state: 'attached' });
  const drawer = page.locator('.workspace-sidebar');
  await drawer.getByRole('button').first().waitFor();
  await page.waitForFunction(() => {
    const box = document.querySelector('.workspace-sidebar').getBoundingClientRect();
    return box.width > 1 && box.right > 1;
  });
}
export async function closeSettings(page) {
  // A reload returns before cookie/session restoration; do not traverse history in that phase.
  await page.locator('.workspace-shell').waitFor();
  const view = new URL(page.url()).searchParams.get('view');
  if (!['settings', 'admin-settings'].includes(view)) return;
  const previous = settingsReturn.get(page);
  settingsReturn.delete(page);
  if (previous) {
    for (let step = 0; step < 2 && page.url() !== previous; step++) await page.goBack();
  } else {
    await ensureSidebar(page);
    await page.locator('.sidebar-brand').click();
  }
  await page.waitForFunction(() => document.querySelector('.view-panel:not([hidden])'));
}
export async function openAccountMenu(page) {
  await closeSettings(page);
  await ensureSidebar(page);
  if (!(await page.locator('.account-menu').isVisible()))
    await page.locator('.account-trigger').click();
}
export async function openSettings(page, tab = 'llm') {
  const view = tab === 'llm' ? 'admin-settings' : 'settings';
  if (new URL(page.url()).searchParams.get('view') === view) return;
  await ensureSidebar(page);
  if (!(await page.locator('.account-menu').isVisible()))
    await page.locator('.account-trigger').click();
  const previous = page.url();
  if (tab === 'llm') {
    await page.locator('.account-admin').click();
    await page.locator('#admin-tab-setting').click();
    await page.locator('#admin-settings-heading').waitFor();
  } else {
    await page.locator('.account-settings').click();
    await page.locator('#settings-heading').waitFor();
  }
  settingsReturn.set(page, previous);
}
export async function showWorkspaceView(page, name) {
  if (['Kết nối LLM', 'LLM connection', 'Подключение LLM'].includes(name)) {
    await openSettings(page, 'llm');
    return;
  }
  await closeSettings(page);
  await ensureSidebar(page);
  const labels = {
    'Tải tài liệu': 'Tài liệu',
    'Upload documents': 'Documents',
    'Загрузить документы': 'Документы',
  };
  if (name === 'Chat' || name === 'Чат') {
    // Returning to chat preserves its draft; the explicit New chat button resets it.
    await page.locator('.sidebar-brand').click();
    return;
  }
  await page
    .getByRole('navigation')
    .getByRole('button', { name: labels[name] ?? name, exact: true })
    .click();
}
export async function logoutFromMenu(page) {
  await openAccountMenu(page);
  await page.getByRole('menuitem', { name: /^(Đăng xuất|Sign out|Выйти)$/ }).click();
}
