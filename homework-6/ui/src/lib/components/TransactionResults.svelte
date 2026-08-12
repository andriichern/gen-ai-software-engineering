<script>
	let { results = [] } = $props();

	// The four stages that annotate a transaction. Reporting is terminal and owns
	// the verdict itself, so it is not one of the outcomes listed per record.
	const STAGES = [
		{ key: 'validation_result', label: 'Validation' },
		{ key: 'fraud_result', label: 'Fraud' },
		{ key: 'compliance_result', label: 'Compliance' },
		{ key: 'settlement_result', label: 'Settlement' }
	];

	const VERDICT_TONE = {
		SETTLED: 'success',
		HELD: 'warning',
		REJECTED: 'danger',
		INCOMPLETE: 'muted'
	};

	// A stage is "did not run" when its annotation is absent entirely -- which is
	// exactly what drives an INCOMPLETE verdict.
	function stagesFor(outcomes) {
		return STAGES.map(({ key, label }) => ({ label, ran: outcomes?.[key] != null }));
	}
</script>

<div class="rounded-lg border border-border bg-surface-raised p-4">
	<h2 class="mb-3 text-sm font-medium text-muted">Transactions</h2>

	{#if results.length === 0}
		<p class="text-sm text-muted">No results yet.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-border text-left text-xs text-muted">
						<th class="py-2 pr-3 font-medium">Transaction</th>
						<th class="py-2 pr-3 font-medium">Verdict</th>
						<th class="py-2 pr-3 font-medium">Fraud</th>
						<th class="py-2 pr-3 font-medium">Stages run</th>
						<th class="py-2 font-medium">Reason</th>
					</tr>
				</thead>
				<tbody>
					{#each results as r (r.transaction_id)}
						<tr class="border-b border-border last:border-b-0 align-top">
							<td class="py-2 pr-3 font-mono text-xs text-text">
								{r.transaction_id}
								{#if r.amount}
									<span class="block text-muted">{r.amount} {r.currency ?? ''}</span>
								{/if}
							</td>
							<td class="py-2 pr-3">
								<span
									class="font-medium"
									class:text-success={VERDICT_TONE[r.verdict] === 'success'}
									class:text-warning={VERDICT_TONE[r.verdict] === 'warning'}
									class:text-danger={VERDICT_TONE[r.verdict] === 'danger'}
									class:text-muted={VERDICT_TONE[r.verdict] === 'muted' || !r.verdict}
								>
									{r.verdict ?? 'unknown'}
								</span>
							</td>
							<td class="py-2 pr-3">
								{#if r.fraud_flagged}
									<span class="text-warning">flagged</span>
								{:else}
									<span class="text-muted">—</span>
								{/if}
							</td>
							<td class="py-2 pr-3">
								<div class="flex flex-wrap gap-1">
									{#each stagesFor(r.stage_outcomes) as stage}
										<span
											class="rounded border px-1.5 py-0.5 text-xs"
											class:border-border={stage.ran}
											class:text-text={stage.ran}
											class:border-danger={!stage.ran}
											class:text-danger={!stage.ran}
											title={stage.ran ? 'ran' : 'did not run'}
										>
											{stage.label}{stage.ran ? '' : ' ✕'}
										</span>
									{/each}
								</div>
							</td>
							<td class="py-2 text-xs text-muted">{r.reason ?? '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
