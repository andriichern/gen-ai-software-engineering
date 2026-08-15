import { json } from '@sveltejs/kit';
import { readFile } from 'node:fs/promises';
import { STATUS_PATH } from '$lib/server/paths.js';
import { isRunning, getLastError } from '$lib/server/runState.js';

export async function GET() {
	let status = { run_started_at: null, run_completed_at: null, stages: {} };
	try {
		const raw = await readFile(STATUS_PATH, 'utf-8');
		status = JSON.parse(raw);
	} catch (err) {
		if (err.code !== 'ENOENT') {
			return json({ error: `failed to read status.json: ${err.message}` }, { status: 500 });
		}
	}

	return json({ ...status, running: isRunning(), error: getLastError() });
}
