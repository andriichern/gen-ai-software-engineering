// Module-level state: survives across requests within this server process.
let running = false;
let lastError = null;

export function isRunning() {
	return running;
}

export function setRunning(value) {
	running = value;
}

export function getLastError() {
	return lastError;
}

export function setLastError(message) {
	lastError = message;
}
