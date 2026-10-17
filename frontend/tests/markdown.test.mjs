import assert from 'node:assert/strict';
import test from 'node:test';
import {readFile} from 'node:fs/promises';
test('Markdown keeps technical structure and restricts links before rendering',async()=>{
  const source=await readFile(new URL('../src/lib/features/chat/markdown.ts',import.meta.url),'utf8').catch(()=>null);
  assert.ok(source,'Safe Markdown token adapter must exist');
  const {tokenize,safeLink}=await import('../src/lib/features/chat/markdown.ts');
  const fence=String.fromCharCode(96).repeat(3);
  const tokens=tokenize('# Heading\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n'+fence+'js\nconst x = 1;');
  assert.equal(tokens[0].type,'heading');assert.ok(tokens.some(t=>t.type==='table'));
  assert.equal(tokens.at(-1).type,'code');assert.equal(tokens.at(-1).text,'const x = 1;');
  for(const url of ['javascript:alert(1)','data:text/html,hi','file:///secret','blob:abc','//example.test','/relative','mailto:user@test'])assert.equal(safeLink(url),null);
  assert.equal(safeLink('https://example.test/docs'),'https://example.test/docs');
});
