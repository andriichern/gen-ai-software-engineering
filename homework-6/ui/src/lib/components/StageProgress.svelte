<script>
	let { stages = {} } = $props();

	const STAGE_ORDER = ['validation', 'fraud_detection', 'compliance', 'settlement', 'reporting'];
	const STAGE_LABELS = {
		validation: 'Validation',
		fraud_detection: 'Fraud Detection',
		compliance: 'Compliance Check',
		settlement: 'Settlement',
		reporting: 'Reporting'
	};

	function stateOf(s) {
		if (!s) return 'pending';
		if (s.start && !s.end) return 'running';
		if (s.end) return 'done';
		return 'pending';
	}

	// Computed together, in one pass, so a stage's `state` and its `s` data can
	// never desync across two separately-evaluated expressions in the template.
	let rows = $derived(
		STAGE_ORDER.map((stage) => {
			const s = stages[stage];
			return { stage, s, state: stateOf(s) };
		})
	);
</script>

<div class="rounded-lg border border-border bg-surface-raised p-4">
	<h2 class="mb-3 text-sm font-medium text-muted">Pipeline stages</h2>
	<ol class="flex flex-col gap-2">
		{#each rows as row (row.stage)}
			<li class="flex items-center justify-between rounded-md border border-border px-3 py-2">
				<div class="flex items-center gap-3">
					<span
						class="h-2.5 w-2.5 rounded-full"
						class:bg-muted={row.state === 'pending'}
						class:bg-accent={row.state === 'running'}
						class:bg-success={row.state === 'done'}
						aria-hidden="true"
					></span>
					<span class="text-sm text-text">{STAGE_LABELS[row.stage]}</span>
				</div>
				<div class="text-xs text-muted">
					{#if row.state === 'pending'}
						pending
					{:else if row.state === 'running'}
						running…
					{:else}
						processed {row.s?.processed} · passed {row.s?.passed} · failed {row.s?.failed}
					{/if}
				</div>
			</li>
		{/each}
	</ol>
</div>
