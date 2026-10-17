import {readFile} from 'node:fs/promises';
import {compileModule} from 'svelte/compiler';
import {transform} from 'esbuild';

/** Compile the real runes module, keeping HTTP boundaries real in owner tests. */
export async function loadState(relativePath) {
  const url = new URL(relativePath, import.meta.url);
  const source = await readFile(url, 'utf8').catch(() => null);
  if (source === null) return null;
  const transformed = await transform(source,{loader:'ts',format:'esm',target:'esnext'});
  const compiled = compileModule(transformed.code, {filename:url.pathname, generate:'client'}).js.code;
  const code = compiled.replace(/from ['"]([^'"]+)['"]/g, (_, specifier) => {
    const resolved = specifier.startsWith('.') ? new URL(specifier, url).href : import.meta.resolve(specifier);
    return "from '" + resolved + "'";
  });
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
export const catalog = {models:[{id:'one',name:'One'},{id:'two',name:'Two'}],selected_model_id:'one',selection_required:false};
export const citation = {citation_id:'c',document_id:'d',revision_id:'r',chunk_id:'ch',ordinal:1,start_offset:0,end_offset:8,title:'Guide',source_hash:'hash',software:'CAD',software_version:'1'};
export const json = (data,status=200) => new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
export const frame = (type,data) => new TextEncoder().encode('event: '+type+'\ndata: '+JSON.stringify(data)+'\n\n');
