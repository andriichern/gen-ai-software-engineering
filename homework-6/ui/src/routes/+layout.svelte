<script>
	import '../app.css';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';

	let { children } = $props();
</script>

<div class="min-h-screen bg-surface text-text">
	<header class="border-b border-border">
		<div class="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
			<h1 class="text-base font-semibold">Transaction Pipeline</h1>
			<ThemeToggle />
		</div>
	</header>
	<main class="mx-auto max-w-3xl px-6 py-6">
		{@render children()}
	</main>
</div>
