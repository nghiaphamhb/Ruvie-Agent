/** User-facing navigation helpers for the workspace sidebar and account Settings dialog. */
export async function ensureSidebar(page){
  await page.locator('.workspace-sidebar').waitFor({state:'attached'});
  if(!await page.locator('.workspace-sidebar').isVisible())await page.locator('.sidebar-open').click();
}
export async function closeSettings(page){
  if(await page.locator('.settings-dialog').isVisible())await page.locator('.settings-dialog').press('Escape');
}
export async function openAccountMenu(page){
  await closeSettings(page);await ensureSidebar(page);
  if(!await page.locator('.account-menu').isVisible())await page.locator('.account-trigger').click();
}
export async function openSettings(page,tab='llm'){
  if(!await page.locator('.settings-dialog').isVisible()){
    await openAccountMenu(page);await page.locator('.account-settings').click();
  }
  await page.locator('#settings-tab-'+tab).click();
}
export async function showWorkspaceView(page,name){
  if(['Kết nối LLM','LLM connection','Подключение LLM'].includes(name)){await openSettings(page,'llm');return;}
  await closeSettings(page);await ensureSidebar(page);
  const labels={'Tải tài liệu':'Tài liệu','Upload documents':'Documents','Загрузить документы':'Документы'};
  await page.getByRole('navigation').getByRole('button',{name:labels[name]??name,exact:true}).click();
}
export async function logoutFromMenu(page){
  await openAccountMenu(page);await page.locator('.account-menu button:not(.account-settings)').click();
}
