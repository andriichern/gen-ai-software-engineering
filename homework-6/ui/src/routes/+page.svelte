<script>
	import { onMount, onDestroy } from 'svelte';
	import StageProgress from '$lib/components/StageProgress.svelte';
	import ReportDashboard from '$lib/components/ReportDashboard.svelte';

	let status = $state(null);
	let report = $state(null);
	let runError = $state(null);
	let triggerError = $state(null);
	let connectionError = $state(null);
	let pollHandle = null;

	function isComplete(s) {
		return Boolean(s && s.run_completed_at && !s.running);
	}

	async function fetchStatus() {
		try {
			const res = await fetch('/api/status');
			status = await res.json();
			runError = status.error;
			connectionError = null;
		} catch (err) {
			connectionError = `lost connection to the dev server: ${err.message}`;
			return;
		}

		if (isComplete(status)) {
			stopPolling();
			await fetchReport();
		}
	}

	async function fetchReport() {
		try {
			const res = await fetch('/api/report');
			if (res.ok) {
				report = await res.json();
			}
			connectionError = null;
		} catch (err) {
			connectionError = `lost connection to the dev server: ${err.message}`;
		}
	}

	function startPolling() {
		stopPolling();
		pollHandle = setInterval(fetchStatus, 1000);
	}

	function stopPolling() {
		if (pollHandle) {
			clearInterval(pollHandle);
			pollHandle = null;
		}
	}

	async function triggerRun() {
		triggerError = null;
		runError = null;
		report = null;

		let res;
		try {
			res = await fetch('/api/run', { method: 'POST' });
		} catch (err) {
			connectionError = `lost connection to the dev server: ${err.message}`;
			return;
		}
		const body = await res.json();
		if (!res.ok) {
			triggerError = body.error;
			return;
		}
		connectionError = null;
		// Reset optimistically: the orchestrator hasn't wiped/rewritten shared/status.json
		// yet, so an immediate fetch here would still show the previous run's stage data.
		status = {
			run_started_at: null,
			run_completed_at: null,
			stages: {},
			running: true,
			error: null
		};
		startPolling();
	}

	onMount(async () => {
		await fetchStatus();
		if (status?.running || (status?.run_started_at && !isComplete(status))) {
			startPolling();
		}
	});

	onDestroy(stopPolling);

	let running = $derived(Boolean(status?.running));
</script>

<div class="flex flex-col gap-6">
	<div class="flex items-center justify-between">
		<p class="text-sm text-muted">Trigger a pipeline run and watch it progress live.</p>
		<button
			type="button"
			onclick={triggerRun}
			disabled={running}
			class="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
		>
			{running ? 'Running…' : 'Run Pipeline'}
		</button>
	</div>

	{#if connectionError}
		<p class="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
			{connectionError}
		</p>
	{/if}

	{#if triggerError}
		<p class="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
			{triggerError}
		</p>
	{/if}

	{#if runError}
		<p class="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
			{runError}
		</p>
	{/if}

	{#if status && (status.run_started_at || running)}
		<StageProgress stages={status.stages} />
	{/if}

	{#if report}
		<ReportDashboard {report} />
	{/if}
</div>
