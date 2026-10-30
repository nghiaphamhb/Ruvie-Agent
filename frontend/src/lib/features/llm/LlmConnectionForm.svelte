<script lang="ts">
  import AiConnectionForm from '../ai-connections/AiConnectionForm.svelte';
  import type { createOrganizationLlmState } from './organization-llm-state.svelte.ts';
  let {
    state,
    active = false,
    disabled = false,
    visible = true,
  }: {
    state: ReturnType<typeof createOrganizationLlmState>;
    active?: boolean;
    disabled?: boolean;
    visible?: boolean;
  } = $props();
</script>

<AiConnectionForm {state} {active} {disabled} {visible} />
