<script>
	let { report } = $props();

	const COUNT_LABELS = {
		validated: 'Validated',
		rejected: 'Rejected',
		flagged: 'Flagged',
		held: 'Held',
		settled: 'Settled'
	};

	const COUNT_TONE = {
		validated: 'text',
		rejected: 'danger',
		flagged: 'warning',
		held: 'warning',
		settled: 'success'
	};

	let maxBucket = $derived(Math.max(1, ...Object.values(report.risk_score_distribution ?? {})));
</script>

<div class="flex flex-col gap-4">
	<div class="rounded-lg border border-border bg-surface-raised p-4">
		<h2 class="mb-1 text-sm font-medium text-muted">Run summary</h2>
		<p class="text-xs text-muted">
			{report.total_records} transactions · generated {new Date(
				report.generated_at
			).toLocaleString()}
		</p>
	</div>

	<div class="grid grid-cols-2 gap-3 sm:grid-cols-5">
		{#each Object.entries(report.counts ?? {}) as [key, value]}
			<div class="rounded-lg border border-border bg-surface-raised p-4">
				<p class="text-xs text-muted">{COUNT_LABELS[key] ?? key}</p>
				<p
					class="mt-1 text-2xl font-semibold"
					class:text-text={COUNT_TONE[key] === 'text'}
					class:text-danger={COUNT_TONE[key] === 'danger'}
					class:text-warning={COUNT_TONE[key] === 'warning'}
					class:text-success={COUNT_TONE[key] === 'success'}
				>
					{value}
				</p>
			</div>
		{/each}
	</div>

	<div class="rounded-lg border border-border bg-surface-raised p-4">
		<h2 class="mb-3 text-sm font-medium text-muted">Risk score distribution</h2>
		<div class="flex flex-col gap-2">
			{#each Object.entries(report.risk_score_distribution ?? {}) as [bucket, count]}
				<div class="flex items-center gap-3">
					<span class="w-24 shrink-0 text-xs text-muted">{bucket}</span>
					<div class="h-3 flex-1 overflow-hidden rounded-full bg-surface">
						<div
							class="h-full rounded-full bg-accent"
							style="width: {(count / maxBucket) * 100}%"
						></div>
					</div>
					<span class="w-6 shrink-0 text-right text-xs text-muted">{count}</span>
				</div>
			{/each}
		</div>
	</div>

	<div class="rounded-lg border border-border bg-surface-raised p-4">
		<h2 class="mb-3 text-sm font-medium text-muted">Settled value by currency</h2>
		<table class="w-full text-sm">
			<tbody>
				{#each Object.entries(report.total_settled_value_by_currency ?? {}) as [currency, amount]}
					<tr class="border-t border-border first:border-t-0">
						<td class="py-1.5 text-muted">{currency}</td>
						<td class="py-1.5 text-right font-mono text-text">{amount}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
