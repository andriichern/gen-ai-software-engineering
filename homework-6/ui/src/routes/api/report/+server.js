import { json } from '@sveltejs/kit';
import { readFile } from 'node:fs/promises';
import { REPORT_PATH } from '$lib/server/paths.js';

export async function GET() {
	try {
		const raw = await readFile(REPORT_PATH, 'utf-8');
		return json(JSON.parse(raw));
	} catch (err) {
		if (err.code === 'ENOENT') {
			return json({ error: 'no report available yet' }, { status: 404 });
		}
		return json({ error: `failed to read report.json: ${err.message}` }, { status: 500 });
	}
}
