import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { createInstance } from 'i18next';
async function core(){const result=await import('../src/lib/i18n/index.ts').catch(()=>null);assert.ok(result,'Locale core must exist and import without DOM');return result;}
async function catalogs(){return Promise.all(['vi-VN','en-US','ru-RU'].map(async locale=>JSON.parse(await readFile(new URL(`../src/lib/i18n/locales/${locale}/translation.json`,import.meta.url),'utf8'))));}

test('resolver respects storage, browser priority, base tags and invalid tags',async()=>{
 const {resolveInitialLocale}=await core();
 for(const [saved,preferred,expected] of [['ru-RU',['en-US'],'ru-RU'],['bad',['en-GB','ru-RU'],'en-US'],[null,['fr-FR','ru'],'ru-RU'],['',['VI-vn'],'vi-VN'],[null,['en_bad','fr'],'vi-VN'],[null,[],'vi-VN'],['ru',['en-US'],'en-US'],[null,['RU-ru'],'ru-RU']]) assert.equal(resolveInitialLocale(saved,preferred),expected);
});
test('messages react to locale changes and reject unsupported locale',async()=>{
 const {initI18n,setLocale,i18n}=await core();await initI18n();let state;const unsubscribe=i18n.subscribe(value=>{state=value;});
 try{await setLocale('en-US');assert.equal(state.t('auth.login'),'Sign in');await setLocale('ru-RU');assert.equal(state.t('auth.login'),'Войти');await setLocale('invalid');assert.equal(state.locale,'ru-RU');assert.equal(state.message({key:'llm.errors.providerUnavailable'}),'Не удалось получить модели. Проверьте URL и API-ключ и повторите попытку.');}finally{unsubscribe();await setLocale('vi-VN');}
});
test('initialization is idempotent and preserves manual locale',async()=>{
 const {initI18n,setLocale,i18n}=await core();await initI18n();await setLocale('ru-RU');await initI18n();const off=i18n.subscribe(state=>assert.equal(state.locale,'ru-RU'));off();await setLocale('vi-VN');
});
test('catalogs cover logical keys, plural forms, nonempty values and placeholders',async()=>{
 const [vi,en,ru]=await catalogs();const base=key=>key.replace(/_(one|few|many|other)$/,'');const logical=data=>[...new Set(Object.keys(data).map(base))].sort();const placeholders=value=>[...value.matchAll(/{{\s*(\w+)\s*}}/g)].map(match=>match[1]).sort();
 assert.deepEqual(logical(vi),logical(en));assert.deepEqual(logical(ru),logical(en));
 for(const data of [vi,en,ru])for(const [key,value]of Object.entries(data)){assert.equal(typeof value,'string');assert.ok(value.trim(),key);const english=en[key]??en[base(key)+'_other'];assert.ok(english,key);assert.deepEqual(placeholders(value),placeholders(english),key);}
 for(const suffix of ['one','few','many','other'])assert.ok(ru['citations.count_'+suffix]);
});
test('missing and empty translations fall back to explicit English',async()=>{
 const {translationOptions}=await core();const instance=createInstance();await instance.init({...translationOptions,lng:'ru-RU',resources:{'en-US':{translation:{known:'Known',empty:'Filled'}},'ru-RU':{translation:{empty:''}}}});assert.equal(instance.t('known'),'Known');assert.equal(instance.t('empty'),'Filled');
});
test('Russian plural forms and English singular use raw count',async()=>{
 const {initI18n,setLocale,i18n}=await core();await initI18n();let state;const off=i18n.subscribe(value=>{state=value;});
 try{await setLocale('ru-RU');for(const[count,word]of[[0,'источников'],[1,'источник'],[2,'источника'],[5,'источников'],[11,'источников'],[21,'источник'],[22,'источника'],[25,'источников']])assert.equal(state.t('citations.count',{count,formattedCount:String(count)}),`${count} ${word}`);await setLocale('en-US');assert.equal(state.t('citations.count',{count:1,formattedCount:'1'}),'1 source');assert.equal(state.t('citations.count',{count:2,formattedCount:'2'}),'2 sources');}finally{off();await setLocale('vi-VN');}
});
test('binary file sizes retain boundaries and locale decimals',async()=>{
 const {formatFileSize}=await core();assert.equal(formatFileSize(1023,'en-US'),'1,023 B');assert.equal(formatFileSize(1024,'en-US'),'1.0 KiB');assert.equal(formatFileSize(1536,'en-US'),'1.5 KiB');assert.equal(formatFileSize(1536,'ru-RU'),'1,5 KiB');assert.equal(formatFileSize(1048576,'en-US'),'1.0 MiB');
});
test('API failures carry safe message keys instead of frozen translated strings',async()=>{
 const {LlmApiError}=await import('../src/lib/features/llm/llm-api.ts');
 assert.deepEqual(new LlmApiError(502).uiMessage,{key:'llm.errors.providerUnavailable'});
 const {DocumentsApiError}=await import('../src/lib/features/documents/documents-api.ts');
 assert.deepEqual(new DocumentsApiError(401).uiMessage,{key:'common.errors.session'});
 const {ChatApiError}=await import('../src/lib/features/chat/chat-api.ts');
 assert.deepEqual(new ChatApiError('interrupted').uiMessage,{key:'chat.errors.interrupted'});
});

test('safe error keys translate in all locales without depending on the DOM', async () => {
  const { initI18n, setLocale, i18n } = await core();
  const { LlmApiError } = await import('../src/lib/features/llm/llm-api.ts');
  const { DocumentsApiError } = await import('../src/lib/features/documents/documents-api.ts');
  const { ChatApiError } = await import('../src/lib/features/chat/chat-api.ts');
  const { message } = await import('../src/lib/i18n/messages.ts');
  const errors = [message('auth.errors.credentials'), message('common.errors.network'),
    ...[401,403,422,502,503].map(status => new LlmApiError(status).uiMessage),
    new DocumentsApiError(500).uiMessage,
    ...['auth_required','invalid_request','model_unavailable','provider_unavailable','generation_failed','network_error','interrupted','protocol_error'].map(code => new ChatApiError(code).uiMessage)];
  await initI18n();
  let state;
  const off = i18n.subscribe(value => { state = value; });
  try {
    const data = await catalogs();
    for (const [index, locale] of ['vi-VN','en-US','ru-RU'].entries()) {
      await setLocale(locale);
      for (const error of errors) assert.equal(state.message(error), data[index][error.key]);
      for (const count of [0,1,2,5,11,21,22,25]) assert.ok(!state.t('citations.count', {count}).includes('citations.count'));
    }
  } finally { off(); await setLocale('vi-VN'); }
});

test('English covers every literal UI key used by components', async () => {
  const { readdir } = await import('node:fs/promises');
  const [, english] = await catalogs();
  const sourceDir = new URL('../src/', import.meta.url);
  async function components(dir){
    const entries=await readdir(dir,{withFileTypes:true});
    const result=[];
    for(const entry of entries){
      if(entry.name.toLowerCase()==='archive')continue;
      const url=new URL(entry.name+(entry.isDirectory()?'/':''),dir);
      if(entry.isDirectory())result.push(...await components(url));
      else if(entry.name.endsWith('.svelte'))result.push(url);
    }
    return result;
  }
  const files = await components(sourceDir);
  for (const file of files) {
    const source = await readFile(file, 'utf8');
    for (const [,key] of source.matchAll(/(?:\$i18n\.t|uiMessage)\('([^']+)'/g)) {
      assert.ok(english[key]?.trim() || english[key + '_other']?.trim(), `${file.pathname}: ${key}`);
    }
  }
});
