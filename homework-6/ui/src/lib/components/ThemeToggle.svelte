<script>
	import { theme } from '$lib/theme.js';
</script>

<button
	type="button"
	onclick={() => theme.toggle()}
	class="inline-flex items-center gap-2 rounded-md border border-border bg-surface-raised px-3 py-1.5 text-sm text-text hover:border-accent"
	aria-label="Toggle color theme"
>
	{#if $theme === 'dark'}
		<span aria-hidden="true">☀</span> Light
	{:else}
		<span aria-hidden="true">☾</span> Dark
	{/if}
</button>
