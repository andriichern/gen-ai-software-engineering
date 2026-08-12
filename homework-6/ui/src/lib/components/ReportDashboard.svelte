<script>
	let { report } = $props();

	// Keys are read straight off report.json: total, settled, rejected, held,
	// incomplete, fraud_flagged, compliance_held, summary, generated_at, errors.
	const VERDICT_COUNTS = [
		{ key: 'settled', label: 'Settled', tone: 'success' },
		{ key: 'held', label: 'Held', tone: 'warning' },
		{ key: 'rejected', label: 'Rejected', tone: 'danger' },
		{ key: 'incomplete', label: 'Incomplete', tone: 'muted' }
	];

	const ATTRIBUTE_COUNTS = [
		{ key: 'fraud_flagged', label: 'Fraud-flagged', tone: 'warning' },
		{ key: 'compliance_held', label: 'Compliance holds', tone: 'warning' }
	];

	let errors = $derived(report.errors ?? []);
</script>

<div class="flex flex-col gap-4">
	<div class="rounded-lg border border-border bg-surface-raised p-4">
		<h2 class="mb-1 text-sm font-medium text-muted">Run summary</h2>
		<p class="text-sm text-text">{report.summary}</p>
		<p class="mt-1 text-xs text-muted">
			{report.total} transactions · generated {new Date(report.generated_at).toLocaleString()}
		</p>
	</div>

	<div class="rounded-lg border border-border bg-surface-raised p-4">
		<h2 class="mb-3 text-sm font-medium text-muted">Verdicts</h2>
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#each VERDICT_COUNTS as { key, label, tone }}
				<div class="rounded-lg border border-border p-3">
					<p class="text-xs text-muted">{label}</p>
					<p
						class="mt-1 text-2xl font-semibold"
						class:text-success={tone === 'success'}
						class:text-warning={tone === 'warning'}
						class:text-danger={tone === 'danger'}
						class:text-muted={tone === 'muted'}
					>
						{report[key] ?? 0}
					</p>
				</div>
			{/each}
		</div>
	</div>

	<div class="rounded-lg border border-border bg-surface-raised p-4">
		<!-- A fraud flag is never a verdict of its own -- it is an attribute of
		     whichever verdict applies, so it is counted separately from them. -->
		<h2 class="mb-3 text-sm font-medium text-muted">Attributes</h2>
		<div class="grid grid-cols-2 gap-3">
			{#each ATTRIBUTE_COUNTS as { key, label, tone }}
				<div class="rounded-lg border border-border p-3">
					<p class="text-xs text-muted">{label}</p>
					<p class="mt-1 text-2xl font-semibold" class:text-warning={tone === 'warning'}>
						{report[key] ?? 0}
					</p>
				</div>
			{/each}
		</div>
	</div>

	{#if errors.length > 0}
		<div class="rounded-lg border border-danger/40 bg-danger/10 p-4">
			<h2 class="mb-2 text-sm font-medium text-danger">Run errors</h2>
			<ul class="flex flex-col gap-1">
				{#each errors as error}
					<li class="text-sm text-danger">{error}</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
