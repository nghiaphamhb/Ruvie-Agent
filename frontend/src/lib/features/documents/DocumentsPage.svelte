<script lang="ts">
  import { type Snippet } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  let { children }: { children: Snippet } = $props();
</script>

<h1 class="view-heading" id="documents-heading" data-view-heading tabindex="-1">
  {$i18n.t('nav.documents')}
</h1>
{@render children()}
