<script lang="ts">
  import OrganizationModelPolicyEditor from '../../src/lib/features/llm/OrganizationModelPolicyEditor.svelte';

  interface ModelItem {
    id: string;
    name: string;
    available: boolean;
  }

  interface Labels {
    heading: string;
    search: string;
    allow: string;
    defaultModel: string;
    unavailable: string;
    empty: string;
    noMatches: string;
    help: string;
  }

  let id = $state('f016-editor');
  let models = $state<ModelItem[]>([
    { id: 'meta-llama/llama-3-8b', name: 'Llama 3 8B', available: true },
    { id: 'openai/gpt-4o', name: 'GPT-4o', available: true },
    { id: 'anthropic/claude-3-opus', name: 'Claude 3 Opus', available: false },
    { id: 'mistralai/mistral-large-2407', name: 'Mistral Large 2', available: true },
  ]);
  let allowedModelIds = $state<string[]>(['meta-llama/llama-3-8b']);
  let defaultModelId = $state<string | null>('meta-llama/llama-3-8b');
  let disabled = $state(false);
  let error = $state<string | null>(null);
  let autoApply = $state(true);

  let labels = $state<Labels>({
    heading: 'Chính sách mô hình',
    search: 'Tìm kiếm mô hình',
    allow: 'Cấp quyền',
    defaultModel: 'Mặc định',
    unavailable: 'Không khả dụng',
    empty: 'Không có mô hình nào',
    noMatches: 'Không tìm thấy kết quả phù hợp',
    help: 'Cấu hình các mô hình LLM được phép sử dụng trong tổ chức.',
  });

  const callbacks = $state<{ allowedModelIds: string[]; defaultModelId: string | null }[]>([]);

  function handleModelChange(next: { allowedModelIds: string[]; defaultModelId: string | null }) {
    callbacks.push(next);
    if (autoApply) {
      allowedModelIds = next.allowedModelIds;
      defaultModelId = next.defaultModelId;
    }
  }

  if (typeof globalThis !== 'undefined') {
    (globalThis as unknown as { __f016Harness: unknown }).__f016Harness = {
      getCallbacks: () => [...callbacks],
      clearCallbacks: () => {
        callbacks.length = 0;
      },
      setProps: (next: {
        id?: string;
        models?: ModelItem[];
        allowedModelIds?: string[];
        defaultModelId?: string | null;
        disabled?: boolean;
        error?: string | null;
        labels?: Labels;
        autoApply?: boolean;
      }) => {
        if (next.id !== undefined) id = next.id;
        if (next.models !== undefined) models = next.models;
        if (next.allowedModelIds !== undefined) allowedModelIds = next.allowedModelIds;
        if (next.defaultModelId !== undefined) defaultModelId = next.defaultModelId;
        if (next.disabled !== undefined) disabled = next.disabled;
        if (next.error !== undefined) error = next.error;
        if (next.labels !== undefined) labels = next.labels;
        if (next.autoApply !== undefined) autoApply = next.autoApply;
      },
      getProps: () => ({
        id,
        models,
        allowedModelIds,
        defaultModelId,
        disabled,
        error,
        labels,
        autoApply,
      }),
      setAutoApply: (val: boolean) => {
        autoApply = val;
      },
    };
  }
</script>

<div class="test-harness">
  <OrganizationModelPolicyEditor
    {id}
    {models}
    {allowedModelIds}
    {defaultModelId}
    {disabled}
    {error}
    {labels}
    onchange={handleModelChange}
  />
</div>

<style>
  .test-harness {
    padding: 24px;
    max-width: 800px;
    margin: 0 auto;
    font-family: var(--font-family, system-ui, sans-serif);
  }
</style>
