<script lang="ts">
  import { i18n } from '../../i18n/index.ts';
  import logo from '../../assets/brand/ruvie-logo.png';
  let { name }: { name: string } = $props();
</script>

<!-- Greeting hierarchy adapted from references/chat/Placeholder.svelte. -->
<div class="chat-welcome">
  <img src={logo} alt="Ruvie" />
  <h1 id="chat-heading" data-view-heading tabindex="-1">
    {$i18n.t('workspace.greeting', { name })}
  </h1>
  <p>{$i18n.t('chat.welcomeHelp')}</p>
</div>

<style>
  .chat-welcome {
    text-align: center;
    margin: 0 0 32px;
  }
  img {
    display: block;
    width: 220px;
    height: auto;
    margin: 0 auto 18px;
    filter: var(--brand-filter, brightness(0) invert(1));
  }
  h1 {
    margin: 0;
    font-size: clamp(24px, 3vw, 32px);
    font-weight: 500;
    line-height: 1.3;
    overflow-wrap: anywhere;
  }
  p {
    margin: 10px 0 0;
    color: var(--muted);
    font-size: 18px;
  }
</style>
