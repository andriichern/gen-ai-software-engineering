import { json } from '@sveltejs/kit';
import { spawn } from 'node:child_process';
import { PIPELINE_ROOT, ORCHESTRATOR_PATH } from '$lib/server/paths.js';
import { isRunning, setRunning, setLastError } from '$lib/server/runState.js';

export async function POST() {
	if (isRunning()) {
		return json(
			{ started: false, error: 'a pipeline run is already in progress' },
			{ status: 409 }
		);
	}

	setRunning(true);
	setLastError(null);

	const child = spawn('python3', [ORCHESTRATOR_PATH], { cwd: PIPELINE_ROOT });

	let stderr = '';
	child.stderr.on('data', (chunk) => {
		stderr += chunk.toString();
	});

	child.on('error', (err) => {
		setRunning(false);
		setLastError(`failed to start orchestrator: ${err.message}`);
	});

	child.on('close', (code) => {
		setRunning(false);
		if (code !== 0) {
			setLastError(stderr.trim() || `orchestrator exited with code ${code}`);
		}
	});

	return json({ started: true });
}
