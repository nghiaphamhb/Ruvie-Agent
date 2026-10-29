import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { compile } from 'svelte/compiler';
import { render } from 'svelte/server';

const sampleLabels = {
  selectAll: 'Chọn hoặc bỏ chọn tất cả model khớp tìm kiếm.',
  heading: 'Chính sách mô hình',
  search: 'Tìm kiếm mô hình',
  allow: 'Cấp quyền',
  defaultModel: 'Mặc định',
  unavailable: 'Không khả dụng',
  empty: 'Không có mô hình nào',
  noMatches: 'Không tìm thấy kết quả phù hợp',
  help: 'Cấu hình các mô hình LLM được phép sử dụng trong tổ chức.',
};

test('table header exposes an accessible bulk checkbox', async () => {
  const Editor = await loadEditor();
  const { body } = render(Editor, {
    props: {
      id: 'bulk',
      models: sampleModels,
      allowedModelIds: [],
      defaultModelId: null,
      labels: sampleLabels,
      onchange() {},
    },
  });
  assert.match(body, /id="bulk-allow-all"/);
  assert.match(body, /aria-label="Chọn hoặc bỏ chọn tất cả model khớp tìm kiếm\."/);
});

const sampleModels = [
  { id: 'meta-llama/llama-3-8b', name: 'Llama 3 8B', available: true },
  { id: 'openai/gpt-4o', name: 'GPT-4o', available: true },
  { id: 'anthropic/claude-3-opus', name: 'Claude 3 Opus', available: false },
];

async function loadEditor() {
  const url = new URL(
    '../src/lib/features/llm/OrganizationModelPolicyEditor.svelte',
    import.meta.url,
  );
  const source = await readFile(url, 'utf8');
  const compiled = compile(source, { filename: url.pathname, generate: 'server' }).js.code;
  const code = compiled.replace(/from ['"]([^'"]+)['"]/g, (_match, specifier) => {
    const resolved = specifier.startsWith('.')
      ? new URL(specifier + (specifier.endsWith('.ts') ? '' : '.ts'), url).href
      : import.meta.resolve(specifier);
    return `from '${resolved}'`;
  });
  const module = await import(
    'data:text/javascript;base64,' + Buffer.from(code).toString('base64')
  );
  return module.default;
}

test('model policy editor renders heading, help, labels, and all model entries with ID and name', async () => {
  const Editor = await loadEditor();
  const { body } = render(Editor, {
    props: {
      id: 'org-models',
      models: sampleModels,
      allowedModelIds: ['meta-llama/llama-3-8b'],
      defaultModelId: 'meta-llama/llama-3-8b',
      disabled: false,
      error: null,
      labels: sampleLabels,
      onchange() {},
    },
  });

  // Heading & help
  assert.match(body, /Chính sách mô hình/);
  assert.match(body, /Cấu hình các mô hình LLM được phép sử dụng/);

  // Search input & label
  assert.match(body, /Tìm kiếm mô hình/);

  // Model names and IDs
  assert.match(body, /Llama 3 8B/);
  assert.match(body, /meta-llama\/llama-3-8b/);
  assert.match(body, /GPT-4o/);
  assert.match(body, /openai\/gpt-4o/);
  assert.match(body, /Claude 3 Opus/);
  assert.match(body, /anthropic\/claude-3-opus/);

  // Unavailable badge
  assert.match(body, /Không khả dụng/);
});

test('model policy editor displays empty status when models array is empty', async () => {
  const Editor = await loadEditor();
  const { body } = render(Editor, {
    props: {
      id: 'org-models',
      models: [],
      allowedModelIds: [],
      defaultModelId: null,
      disabled: false,
      error: null,
      labels: sampleLabels,
      onchange() {},
    },
  });

  assert.match(body, /Không có mô hình nào/);
  assert.match(body, /role="status"/);
});

test('model policy editor displays error message with role="alert"', async () => {
  const Editor = await loadEditor();
  const errorMessage = 'Không thể tải cấu hình chính sách mô hình';
  const { body } = render(Editor, {
    props: {
      id: 'org-models',
      models: sampleModels,
      allowedModelIds: [],
      defaultModelId: null,
      disabled: false,
      error: errorMessage,
      labels: sampleLabels,
      onchange() {},
    },
  });

  assert.match(body, /Không thể tải cấu hình chính sách mô hình/);
  assert.match(body, /role="alert"/);
});

test('model policy editor reflects checked, default and disabled semantics', async () => {
  const Editor = await loadEditor();

  // Test normal checked states
  const { body: normalBody } = render(Editor, {
    props: {
      id: 'org-models',
      models: sampleModels,
      allowedModelIds: ['meta-llama/llama-3-8b'],
      defaultModelId: 'meta-llama/llama-3-8b',
      disabled: false,
      error: null,
      labels: sampleLabels,
      onchange() {},
    },
  });

  // Checkbox for allowed model is checked
  assert.match(normalBody, /type="checkbox"[^>]*checked/);
  // Radio for default model is checked
  assert.match(normalBody, /type="radio"[^>]*checked/);

  // Claude 3 Opus is unavailable and not allowed, so its checkbox must be disabled
  // Check that disabled attribute is present for Claude's checkbox
  assert.match(normalBody, /type="checkbox"[^>]*disabled/);
  // Claude's radio must also be disabled
  assert.match(normalBody, /type="radio"[^>]*disabled/);

  // Test fully disabled component
  const { body: disabledBody } = render(Editor, {
    props: {
      id: 'org-models',
      models: sampleModels,
      allowedModelIds: ['meta-llama/llama-3-8b'],
      defaultModelId: 'meta-llama/llama-3-8b',
      disabled: true,
      error: null,
      labels: sampleLabels,
      onchange() {},
    },
  });

  // All inputs must be disabled
  const searchDisabled = disabledBody.match(/type="search"[^>]*disabled/);
  assert.ok(searchDisabled, 'Search input should be disabled when component is disabled');
});

test('model policy editor instances isolate IDs and radio groups', async () => {
  const Editor = await loadEditor();
  const { body: body1 } = render(Editor, {
    props: {
      id: 'inst-1',
      models: sampleModels,
      allowedModelIds: ['meta-llama/llama-3-8b'],
      defaultModelId: 'meta-llama/llama-3-8b',
      disabled: false,
      error: null,
      labels: sampleLabels,
      onchange() {},
    },
  });

  const { body: body2 } = render(Editor, {
    props: {
      id: 'inst-2',
      models: sampleModels,
      allowedModelIds: ['meta-llama/llama-3-8b'],
      defaultModelId: 'meta-llama/llama-3-8b',
      disabled: false,
      error: null,
      labels: sampleLabels,
      onchange() {},
    },
  });

  // Radio groups must be unique
  const radioGroup1 = body1.match(/name="([^"]+)"/)?.[1];
  const radioGroup2 = body2.match(/name="([^"]+)"/)?.[1];
  assert.ok(radioGroup1, 'Instance 1 must have a radio group name');
  assert.ok(radioGroup2, 'Instance 2 must have a radio group name');
  assert.notEqual(radioGroup1, radioGroup2, 'Radio group names must not collide');

  // Input IDs must have instance ID prefix
  assert.match(body1, /id="inst-1/);
  assert.match(body2, /id="inst-2/);
  assert.doesNotMatch(body1, /id="inst-2/);
});
