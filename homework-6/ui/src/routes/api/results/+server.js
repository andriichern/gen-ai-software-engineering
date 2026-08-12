import { json } from '@sveltejs/kit';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { RESULTS_DIR } from '$lib/server/paths.js';

// The per-transaction verdict lives only in shared/results/{transaction_id}.json --
// report.json carries the aggregate counts and nothing per-record. Reporting is the
// sole writer of this directory, so a file here is always a finished record.
export async function GET() {
	let names;
	try {
		names = (await readdir(RESULTS_DIR)).filter((n) => n.endsWith('.json'));
	} catch (err) {
		if (err.code === 'ENOENT') {
			return json({ results: [] });
		}
		return json({ error: `failed to read results/: ${err.message}` }, { status: 500 });
	}

	const results = [];
	for (const name of names.sort()) {
		try {
			const raw = await readFile(path.join(RESULTS_DIR, name), 'utf-8');
			const record = JSON.parse(raw);
			results.push({
				transaction_id: record.transaction_id,
				amount: record.amount,
				currency: record.currency,
				verdict: record.verdict,
				fraud_flagged: record.fraud_flagged,
				reason: record.reason,
				stage_outcomes: record.stage_outcomes ?? {}
			});
		} catch (err) {
			// A record that is unreadable or mid-write is reported as such rather than
			// failing the whole response -- the rest of the run is still worth showing.
			results.push({
				transaction_id: name.replace(/\.json$/, ''),
				verdict: null,
				fraud_flagged: false,
				reason: `unreadable result file: ${err.message}`,
				stage_outcomes: {}
			});
		}
	}

	return json({ results });
}
