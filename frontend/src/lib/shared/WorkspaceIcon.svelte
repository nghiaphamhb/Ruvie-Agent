<script lang="ts">
  let { name, size=20 }: {name:string;size?:number}=$props();
  // Knobs path reused from references/src/lib/components/icons/Knobs.svelte.
  const paths:Record<string,string>={
    chat:'M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Z',
    search:'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
    notes:'M5 3h14v18H5ZM8 7h8M8 11h8M8 15h5',
    workspace:'M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z',
    projects:'M3 7h7l2-3h8a1 1 0 0 1 1 1v14H3ZM3 10h18',
    documents:'M6 2h8l5 5v15H6ZM14 2v6h5M9 12h7M9 16h7',
    plus:'M12 4v16M4 12h16',dots:'M4 12h.1M12 12h.1M20 12h.1',
    collapse:'M3 3h18v18H3ZM8 3v18',logout:'M9 3H3v18h6M8 12h13M17 8l4 4-4 4',
    settings:'M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75'
  };
</script>
<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={paths[name]??paths.chat}/></svg>
