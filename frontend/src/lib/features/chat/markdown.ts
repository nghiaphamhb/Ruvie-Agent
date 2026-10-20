import { marked } from 'marked';
/** Lex only; HTML is never inserted into the DOM. Svelte escapes every text token. */
export function tokenize(content: string) {
  return marked.lexer(content, { gfm: true });
}
/** Model output may link only to absolute HTTP(S) URLs; everything else remains text. */
export function safeLink(value: string): string | null {
  if (!/^https?:\/\//i.test(value)) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}
