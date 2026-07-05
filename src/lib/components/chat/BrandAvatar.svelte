<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let alt = '';
	export let className = '';
	export let sizeClass = 'size-8';
</script>

<span
	class={`inline-flex ${sizeClass} items-center justify-center overflow-hidden rounded-full bg-white ring-1 ring-slate-200/80 shadow-sm dark:bg-white dark:ring-white/10 ${className}`.trim()}
>
	<img
		src={`${WEBUI_BASE_URL}/static/favicon.png`}
		class="size-full object-cover"
		{alt}
		aria-hidden={alt === ''}
		draggable="false"
	/>
</span>
