import { fileURLToPath } from 'node:url';
import path from 'node:path';

// This file lives at <pipeline-root>/ui/src/lib/server/paths.js
// dirname(this file) = .../ui/src/lib/server -> up 4 levels reaches <pipeline-root>
export const PIPELINE_ROOT = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	'../../../..'
);
export const SHARED_DIR = path.join(PIPELINE_ROOT, 'shared');
export const RESULTS_DIR = path.join(SHARED_DIR, 'results');
export const STATUS_PATH = path.join(SHARED_DIR, 'status.json');
export const REPORT_PATH = path.join(SHARED_DIR, 'report.json');
export const ORCHESTRATOR_PATH = path.join(PIPELINE_ROOT, 'orchestrator.py');
