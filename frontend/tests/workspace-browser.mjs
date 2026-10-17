/** F010: rendered workspace behavior, using isolated fake HTTP APIs. */
import assert from 'node:assert/strict';
import {runWorkspaceAccessibilityChecks} from './workspace-a11y-browser.mjs';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root=path.resolve(fileURLToPath(new URL('../dist/',import.meta.url)));
const mime={'.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml'};
const streams=[];
const server=createServer(async(req,res)=>{
  if(req.url==='/chat'){
    for await(const chunk of req){}
    res.writeHead(200,{'Content-Type':'text/event-stream'});
    const frame=(type,data)=>{if(!res.destroyed)res.write(`event: ${type}\ndata: ${JSON.stringify(data)}\n\n`);};
    frame('delta',{text:streams.length?'New answer':'Old answer'});
    let finish;const pending=new Promise(resolve=>{finish=resolve;});streams.push({finish,frame});
    await pending;frame('completed',{});res.end();return;
  }
  const target=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname.replace(/\/$/,'/index.html'));
  if(!target.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  try{res.setHeader('Content-Type',mime[path.extname(target)]||'text/html');res.end(await readFile(target));}
  catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
let browser;let checks=0;
try{
  browser=await chromium.launch({headless:true,executablePath:process.env.RUVIE_BROWSER_PATH||undefined});
  const page=await browser.newPage({viewport:{width:1366,height:768},locale:'vi-VN'});
  page.setDefaultTimeout(5000);
  await mkdir(fileURLToPath(new URL('../../logs/f010/',import.meta.url)),{recursive:true});
  const snap=name=>page.screenshot({path:fileURLToPath(new URL('../../logs/f010/'+name+'.png',import.meta.url))});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const calls=[];let saveRelease;let projectMode='empty';let releaseProjects;let expired=false;
  const model={models:[{id:'one',name:'First model'},{id:'two',name:'Second model'}],selected_model_id:'one',selection_required:false};
  await page.route('**/*',async route=>{
    const api=new URL(route.request().url()).pathname;
    if(!/^\/(auth|projects|models|llm|chat)(\/|$)/.test(api))return route.continue();
    const method=route.request().method();calls.push({api,method,body:route.request().postData()});
    const json=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
    if(api==='/auth/session')return json({user:{id:'user',display_name:'Nguyễn An'},csrf_token:'csrf'});
    if(api==='/auth/logout')return json({detail:'private logout detail'},503);
    if(expired&&api.startsWith('/llm'))return json({},401);
    if(api==='/projects'){
      if(projectMode==='error')return json({detail:'must-not-display'},500);
      if(projectMode==='slow')await new Promise(resolve=>{releaseProjects=resolve;});
      return json({items:projectMode==='empty'?[]:[{id:'p1',code:'ALPHA',name:'Alpha project'},{id:'p2',code:'BETA',name:'Beta project'}]});
    }
    if(api==='/models')return json(model);
    if(api==='/llm/connection'&&method==='PUT'){
      await new Promise(resolve=>{saveRelease=resolve;});model.selected_model_id='two';return json(model);
    }
    if(api==='/llm/connection')return json({source:'personal',base_url:'https://example.test/v1',has_api_key:true,selected_model_id:model.selected_model_id});
    if(api==='/llm/connection/model'){model.selected_model_id=JSON.parse(route.request().postData()).model_id;return json({selected_model_id:model.selected_model_id});}
    if(api==='/chat')return route.continue();
    return json({},404);
  });
  await page.goto(origin);
  await page.getByRole('button',{name:'Chọn model',exact:true}).waitFor();
  assert.equal(await page.getByRole('heading',{name:'Xin chào, Nguyễn An',exact:true}).count(),1,'welcome uses the session name');checks++;
  assert.equal(await page.locator('.chat-welcome img[alt="Ruvie"]').count(),1,'welcome shows the complete brand');checks++;
  const nav=page.getByRole('navigation',{name:'Điều hướng chính'});
  for(const name of ['Chat mới','Tìm kiếm','Ghi chú','Workspace','Dự án','Tài liệu'])assert.equal(await nav.getByRole('button',{name,exact:true}).count(),1);checks++;
  assert.equal(await page.locator('.composer [aria-label="Chọn model"]').count(),1,'model selector belongs to composer');
  assert.equal(calls.filter(c=>c.api==='/models').length,1,'catalog loads before opening Settings');checks++;
  await page.getByRole('button',{name:'Tóm tắt tài liệu',exact:true}).click();
  assert.equal(await page.locator('#question').inputValue(),'Tóm tắt tài liệu');assert.equal(calls.filter(c=>c.api==='/chat').length,0);checks++;
  await page.getByRole('button',{name:'Thu gọn sidebar',exact:true}).click();
  assert.equal(await page.locator('#question').inputValue(),'Tóm tắt tài liệu');
  await snap('sidebar-collapsed');
  await page.getByRole('button',{name:'Mở sidebar',exact:true}).click();checks++;
  await page.getByRole('button',{name:'Tùy chỉnh cuộc trò chuyện',exact:true}).click();
  await page.getByRole('heading',{name:'Tùy chỉnh cuộc trò chuyện',exact:true}).waitFor();await snap('controls-desktop');
  await page.getByRole('button',{name:'Đóng bảng tùy chỉnh',exact:true}).click();
  assert.equal(await page.locator('.chat-controls-trigger').evaluate(e=>e===document.activeElement),true);checks++;
  await page.locator('.account-trigger').click();
  await page.locator('.workspace-toolbar').click({position:{x:300,y:28}});
  assert.equal(await page.locator('.account-menu').isVisible(),false,'outside click closes account menu');
  await page.waitForFunction(()=>document.querySelector('.account-trigger')===document.activeElement); assert.equal(await page.locator('.account-trigger').evaluate(e=>e===document.activeElement),true,`outside click returns focus from account menu: ${await page.evaluate(()=>document.activeElement?.outerHTML.slice(0,220))}`);checks++;
  const initialGets=calls.filter(c=>c.method==='GET'&&c.api.startsWith('/llm')).length;
  await page.locator('.account-trigger').click();await page.locator('.account-settings').click();
  await page.getByRole('dialog',{name:'Cài đặt',exact:true}).waitFor();
  await page.locator('#settings-tab-general').focus();await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('#settings-tab-llm').getAttribute('aria-selected'),'true');
  assert.equal(await page.locator('#settings-tab-llm').evaluate(e=>e===document.activeElement),true);
  assert.equal(await page.locator('#llm-key').inputValue(),'');
  await page.locator('.settings-dialog').press('Escape');assert.equal(await page.locator('.settings-dialog').isVisible(),false);
  await page.locator('.account-trigger').click();await page.locator('.account-settings').click();
  await page.locator('#settings-tab-llm').click();assert.equal(calls.filter(c=>c.method==='GET'&&c.api.startsWith('/llm')).length,initialGets,'modal reopen does not reload catalog');checks++;
  await page.locator('#llm-key').fill('draft-secret');await page.getByRole('button',{name:'Kết nối',exact:true}).click();
  await page.getByRole('button',{name:'Đang xử lý…',exact:true}).waitFor();
  await page.locator('.settings-dialog').press('Escape');
  assert.equal(await page.getByRole('button',{name:'Chọn model',exact:true}).isDisabled(),true);
  saveRelease();await page.getByText('Model: Second model',{exact:true}).waitFor();
  assert.equal(calls.filter(c=>c.method==='PUT').length,1,'save keeps ownership across close');checks++;
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();await page.locator('.answer').filter({hasText:'Old answer'}).waitFor();
  await snap('chat-streaming');
  assert.equal(Object.keys(JSON.parse(calls.find(c=>c.api==='/chat').body)).sort().join(','),'message,model_id');
  await nav.getByRole('button',{name:'Chat mới',exact:true}).click();
  await page.getByRole('heading',{name:'Xin chào, Nguyễn An',exact:true}).waitFor();assert.equal(await page.locator('.answer').count(),0);checks++;
  await page.locator('#question').fill('New question');await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();
  await page.locator('.answer').filter({hasText:'New answer'}).waitFor();streams[0].finish();
  assert.equal(await page.getByRole('button',{name:'Dừng trả lời',exact:true}).isVisible(),true,'old finally cannot unlock the new stream'); assert.equal(await page.getByRole('button',{name:'Chọn model',exact:true}).isDisabled(),true);
  streams[1].frame('citations',{citations:[{citation_id:'c1',document_id:'d1',revision_id:'r1',chunk_id:'ch1',ordinal:1,start_offset:0,end_offset:10,title:'Project guide',source_hash:'hash',software:'Ruvie',software_version:'1'}]});
  streams[1].finish();await page.waitForFunction(()=>!document.querySelector('.response-status'));await snap('chat-completed');
  await page.getByText('1 nguồn tham khảo',{exact:true}).click();await page.getByText('Project guide',{exact:true}).waitFor();
  assert.ok(await page.locator('.sources summary').evaluate(e=>e.getBoundingClientRect().height>=44),'citation expansion has a 44px touch target');
  await snap('chat-citations');checks++;
  await nav.getByRole('button',{name:'Chat mới',exact:true}).click();
  await mkdir(fileURLToPath(new URL('../../logs/f010/',import.meta.url)),{recursive:true});
  await page.locator('#question').evaluate(e=>e.blur());
  await page.screenshot({path:fileURLToPath(new URL('../../logs/f010/chat-desktop.png',import.meta.url))});
  await page.locator('.account-trigger').click();await page.locator('.account-settings').click();
  await page.locator('#settings-tab-llm').click();
  await page.screenshot({path:fileURLToPath(new URL('../../logs/f010/settings-desktop.png',import.meta.url))});
  await page.locator('.settings-dialog').press('Escape');
  for(const size of [{width:1024,height:600},{width:375,height:812}]){
    await page.setViewportSize(size);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
    await page.locator('#question').fill('Preserved draft');
    if(!await nav.isVisible())await page.locator('.sidebar-open').click();
    await nav.getByRole('button',{name:'Ghi chú',exact:true}).click();
    await page.getByRole('heading',{name:'Ghi chú',exact:true}).waitFor();
    if(!await nav.isVisible())await page.locator('.sidebar-open').click();
    await page.locator('.sidebar-brand').click();
    assert.equal(await page.locator('#question').inputValue(),'Preserved draft');
    await page.locator('#question').evaluate(e=>e.blur());
    await page.screenshot({path:fileURLToPath(new URL(`../../logs/f010/chat-${size.width}.png`,import.meta.url))});checks++;
  }
  await page.setViewportSize({width:1366,height:768});
  await nav.getByRole('button',{name:'Dự án',exact:true}).click();
  await page.locator('.projects-page').getByText('Bạn chưa tham gia project nào.',{exact:true}).waitFor();checks++;
  projectMode='error';await page.locator('.projects-page').getByRole('button',{name:'Tải lại',exact:true}).click();
  await page.locator('.projects-page [role=alert]').waitFor();
  assert.ok(!(await page.locator('body').innerText()).includes('must-not-display'));checks++;
  projectMode='slow';await page.locator('.projects-page').getByRole('button',{name:'Thử lại',exact:true}).click();
  await page.locator('.projects-page [role=status]').waitFor();
  await nav.getByRole('button',{name:'Ghi chú',exact:true}).click();releaseProjects();
  await nav.getByRole('button',{name:'Dự án',exact:true}).click();
  await page.getByRole('button',{name:'Alpha project ALPHA',exact:true}).waitFor();await snap('projects-desktop');
  await page.getByRole('button',{name:'Alpha project ALPHA',exact:true}).click();
  assert.equal(await page.getByLabel('Project',{exact:true}).inputValue(),'p1');
  await page.getByLabel('Tên tài liệu',{exact:true}).fill('Retained metadata');
  await page.getByLabel('File',{exact:true}).setInputFiles({name:'retained.txt',mimeType:'text/plain',buffer:Buffer.from('content')});
  await nav.getByRole('button',{name:'Dự án',exact:true}).click();
  await page.getByRole('button',{name:'Beta project BETA',exact:true}).click();
  assert.equal(await page.getByLabel('Project',{exact:true}).inputValue(),'p2');
  assert.equal(await page.getByLabel('Tên tài liệu',{exact:true}).inputValue(),'Retained metadata');
  assert.equal(await page.getByLabel('File',{exact:true}).evaluate(e=>e.files[0].name),'retained.txt');checks++;
  await snap('documents-desktop');
  await nav.getByRole('button',{name:'Chat mới',exact:true}).click();
  await page.locator('.attach-trigger').click();
  assert.equal(await page.getByLabel('Project',{exact:true}).inputValue(),'p2');
  assert.equal(await page.getByLabel('File',{exact:true}).evaluate(e=>e.files[0].name),'retained.txt');checks++;
  await page.locator('.upload-dialog').press('Escape'); const beforePlaceholder=calls.length;
  await nav.getByRole('button',{name:'Tìm kiếm',exact:true}).click();await page.getByRole('searchbox').waitFor();
  await nav.getByRole('button',{name:'Workspace',exact:true}).click();
  for(const label of ['Models','Knowledge','Prompts','Tools','Skills'])await page.getByRole('tab',{name:label,exact:true}).click();
  await nav.getByRole('button',{name:'Thêm thư mục',exact:true}).click();
  await page.getByRole('heading',{name:'Thư mục',exact:true}).waitFor();
  assert.equal(calls.length,beforePlaceholder,'unsupported features make no API requests');checks++;
  checks+=await runWorkspaceAccessibilityChecks(browser,origin);
  await page.locator('.account-trigger').click();
  await page.locator('.account-menu').getByRole('menuitem',{name:'Đăng xuất',exact:true}).click();
  await page.locator('.auth-error[role=alert]').waitFor();
  assert.equal(await page.locator('.workspace-shell').count(),1,'logout failure retains the active workspace');
  assert.ok(!(await page.locator('body').innerText()).includes('private logout detail'));checks++;
  await page.locator('.account-trigger').click();await page.locator('.account-settings').click();await page.locator('#settings-tab-llm').click();
  expired=true;await page.locator('.llm-panel').getByRole('button',{name:'Tải lại',exact:true}).click();
  await page.getByRole('heading',{name:'Đăng nhập',exact:true}).waitFor();
  assert.equal(await page.locator('.workspace-shell,.settings-dialog,.account-menu,.chat-controls-panel').count(),0,'401 unmounts all account surfaces');checks++;
  assert.deepEqual(errors,[]);console.log(`Workspace browser: ${checks} checks passed`);
}finally{for(const s of streams)s.finish();if(browser)await browser.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
