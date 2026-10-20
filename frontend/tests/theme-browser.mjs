/** Theme UX uses fake APIs; no development account or LLM provider. */
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.RUVIE_PLAYWRIGHT_PATH||'playwright');
const root=path.resolve(fileURLToPath(new URL('../dist/',import.meta.url)));
const server=createServer(async(req,res)=>{
  const target=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname.replace(/\/$/,'/index.html'));
  if(!target.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  try{res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml'})[path.extname(target)]||'text/html');res.end(await readFile(target));}catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
let browser;let checks=0;
try{
  browser=await chromium.launch({headless:true,executablePath:process.env.RUVIE_BROWSER_PATH||undefined});
  const page=await browser.newPage({locale:'vi-VN',colorScheme:'light',viewport:{width:1440,height:1000}});
  page.setDefaultTimeout(5000);
  let user='alice';const calls=[];const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',route=>{
    const api=new URL(route.request().url()).pathname;
    const json=data=>route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
    if(!/^\/(auth|projects|models|llm)(\/|$)/.test(api))return route.continue();
    calls.push(api);
    if(api==='/auth/session')return json({user:{id:user,display_name:'Admin'},csrf_token:'csrf'});
    if(api==='/projects')return json({items:[]});
    if(api==='/models')return json({models:[{id:'nvidia/test:free',name:'NVIDIA: Nemotron 3 Super (free)'}],selected_model_id:'nvidia/test:free',selection_required:false});
    if(api==='/llm/connection')return json({source:'server',base_url:'https://example.test/v1',has_api_key:true,selected_model_id:'nvidia/test:free'});
    return json({});
  });
  const shell=page.locator('.workspace-shell');
  async function resolved(value){await page.waitForFunction(expected=>document.querySelector('.workspace-shell')?.dataset.theme===expected,value,{timeout:5000});}
  async function settings(){await page.locator('.account-trigger').click();await page.locator('.account-settings').click();await page.getByRole('tab',{name:'Hiển thị',exact:true}).click();}
  await page.goto(origin);await shell.waitFor();await resolved('light');checks++;
  await page.locator('#question').fill('Bản nháp được giữ nguyên');
  await settings();
  const system=page.getByRole('radio',{name:'Hệ thống',exact:true}),light=page.getByRole('radio',{name:'Sáng',exact:true}),dark=page.getByRole('radio',{name:'Tối',exact:true});
  assert.equal(await system.isChecked(),true);
  const before=calls.length;
  await dark.check();await resolved('dark');assert.equal(await page.locator('#question').inputValue(),'Bản nháp được giữ nguyên');
  await page.emulateMedia({colorScheme:'light'});await resolved('dark');
  await light.check();await resolved('light');
  await light.focus();await page.keyboard.press('Tab');
  assert.equal(await page.locator('.settings-close').evaluate(e=>e===document.activeElement),true,'Tab leaves the radio group and stays in Settings');
  await page.emulateMedia({colorScheme:'dark'});await resolved('light');
  assert.equal(calls.length,before,'theme changes make no API calls');checks++;
  await system.check();await resolved('dark');await page.emulateMedia({colorScheme:'light'});await resolved('light');checks++;
  await system.focus();await page.keyboard.press('ArrowRight');await resolved('light');assert.equal(await light.isChecked(),true);
  await page.keyboard.press('ArrowRight');await resolved('dark');assert.equal(await dark.isChecked(),true);checks++;
  await page.locator('.settings-dialog').press('Escape');await page.reload();await resolved('dark');checks++;
  user='bob';await page.reload();await resolved('light');await settings();assert.equal(await system.isChecked(),true);
  user='alice';await page.reload();await resolved('dark');checks++;
  await settings();await light.check();await page.locator('.settings-dialog').press('Escape');
  await page.locator('#question').fill('');
  await mkdir(fileURLToPath(new URL('../../logs/theme/',import.meta.url)),{recursive:true});
  await page.screenshot({path:fileURLToPath(new URL('../../logs/theme/light-desktop.png',import.meta.url))});
  // Verify actual text/background contrast on both themes using browser-resolved tokens.
  for(const choice of ['Sáng','Tối']){
    await settings();await page.getByRole('radio',{name:choice,exact:true}).check();
    const contrast=await shell.evaluate(element=>{
      const style=getComputedStyle(element);
      const rgb=value=>{const probe=document.createElement('span');probe.style.color=style.getPropertyValue(value);element.append(probe);const result=getComputedStyle(probe).color.match(/[\d.]+/g).slice(0,3).map(Number);probe.remove();return result;};
      const luminance=values=>values.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
      return [['--ink','--paper'],['--muted','--paper'],['--muted','--surface'],['--error','--error-bg']].map(([a,b])=>{const x=luminance(rgb(a)),y=luminance(rgb(b));return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);});
    });
    assert.ok(contrast.every(value=>value>=4.5),`${choice} text contrast: ${contrast}`);
    await page.screenshot({path:fileURLToPath(new URL(`../../logs/theme/settings-${choice==='Sáng'?'light':'dark'}.png`,import.meta.url))});
    await page.locator('.settings-dialog').press('Escape');
  }checks++;
  await settings();await light.check();await page.locator('.settings-dialog').press('Escape');
  await page.getByRole('button',{name:'Chọn model',exact:true}).click();
  assert.equal(await page.locator('.menu:popover-open').evaluate(e=>getComputedStyle(e).colorScheme),'light');
  await page.screenshot({path:fileURLToPath(new URL('../../logs/theme/model-light.png',import.meta.url))});
  await page.getByRole('combobox').press('Escape');checks++;
  await page.setViewportSize({width:375,height:812});
  await page.locator('.sidebar-open').click();await settings();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:fileURLToPath(new URL('../../logs/theme/light-mobile.png',import.meta.url))});checks++;
  await page.locator('.settings-dialog').press('Escape');
  await page.addInitScript(()=>{Object.defineProperty(window,'localStorage',{get(){throw Error('blocked');}});});
  await page.reload();await resolved('light');await page.locator('.sidebar-open').click();await settings();await dark.check();await resolved('dark');checks++;
  assert.deepEqual(errors,[]);
  console.log(`Theme browser: ${checks} checks passed`);
}finally{await browser?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
