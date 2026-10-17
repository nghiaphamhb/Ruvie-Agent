<script lang="ts">
  import {onDestroy} from 'svelte';
  import {i18n} from '../../i18n/index.ts';
  import {tokenize,safeLink} from './markdown.ts';
  import CodeBlock from './CodeBlock.svelte';
  let {content}:{content:string}=$props();let tokens=$state<any[]>([]);
  let latest='',frame:number|null=null;
  // Adapted from references Markdown.updateHandler: parse at most once per frame.
  $effect(()=>{latest=content;if(frame===null)frame=requestAnimationFrame(()=>{frame=null;tokens=tokenize(latest);});});
  onDestroy(()=>{if(frame!==null)cancelAnimationFrame(frame);});
</script>
{#snippet renderTokens(items:any[])}
  {#each items as token}
    {#if token.type==='heading'}<svelte:element this={'h'+token.depth}>{@render renderTokens(token.tokens??[])}</svelte:element>
    {:else if token.type==='paragraph'}<p>{@render renderTokens(token.tokens??[])}</p>
    {:else if token.type==='text'}{#if token.tokens}{@render renderTokens(token.tokens)}{:else}{token.text}{/if}
    {:else if token.type==='strong'}<strong>{@render renderTokens(token.tokens??[])}</strong>
    {:else if token.type==='em'}<em>{@render renderTokens(token.tokens??[])}</em>
    {:else if token.type==='del'}<del>{@render renderTokens(token.tokens??[])}</del>
    {:else if token.type==='codespan'}<code>{token.text}</code>
    {:else if token.type==='code'}<CodeBlock code={token.text} language={token.lang??''}/>
    {:else if token.type==='blockquote'}<blockquote>{@render renderTokens(token.tokens??[])}</blockquote>
    {:else if token.type==='list'}<svelte:element this={token.ordered?'ol':'ul'} start={token.ordered?token.start:undefined}>{#each token.items as item}<li>{@render renderTokens(item.tokens??[])}</li>{/each}</svelte:element>
    {:else if token.type==='table'}<!-- svelte-ignore a11y_no_noninteractive_tabindex (Wide tables must be keyboard-scrollable.) --><div class="table-scroll" role="region" aria-label={$i18n.t('chat.table')} tabindex="0"><table><thead><tr>{#each token.header as cell}<th>{@render renderTokens(cell.tokens??[])}</th>{/each}</tr></thead><tbody>{#each token.rows as row}<tr>{#each row as cell}<td>{@render renderTokens(cell.tokens??[])}</td>{/each}</tr>{/each}</tbody></table></div>
    {:else if token.type==='link'}{@const href=safeLink(token.href)}{#if href}<a {href} target="_blank" rel="noopener noreferrer">{@render renderTokens(token.tokens??[])}</a>{:else}{@render renderTokens(token.tokens??[])}{/if}
    {:else if token.type==='br'}<br/>
    {:else if token.type==='hr'}<hr/>
    {:else if token.type!=='space'}{token.raw??token.text??''}
    {/if}
  {/each}
{/snippet}
<div class="markdown">{@render renderTokens(tokens)}</div>
<style>
  .markdown{overflow-wrap:anywhere;min-width:0;line-height:1.75;}p{margin:0 0 14px;}
  h1,h2,h3,h4,h5,h6{line-height:1.4;margin:22px 0 12px;}h1{font-size:24px;}h2{font-size:21px;}h3{font-size:18px;}
  ul,ol{padding-left:24px;margin:10px 0 16px;}li{margin:6px 0;}blockquote{margin:16px 0;padding:4px 16px;border-left:3px solid var(--accent);color:var(--muted);}
  a{color:var(--accent);text-decoration:underline;}code{font-family:ui-monospace,Consolas,monospace;font-size:.9em;background:var(--soft);border-radius:4px;padding:2px 4px;}
  .table-scroll{max-width:100%;overflow:auto;margin:16px 0;}table{border-collapse:collapse;min-width:100%;font-size:14px;}th,td{text-align:left;border:1px solid var(--border);padding:9px 12px;min-width:90px;}th{background:var(--soft);}
</style>
