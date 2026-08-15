import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const STORAGE_KEY = 'pipeline-ui-theme';

function createThemeStore() {
	const initial = browser
		? document.documentElement.getAttribute('data-theme') || 'light'
		: 'light';
	const { subscribe, update } = writable(initial);

	return {
		subscribe,
		toggle() {
			update((current) => {
				const next = current === 'dark' ? 'light' : 'dark';
				if (browser) {
					document.documentElement.setAttribute('data-theme', next);
					localStorage.setItem(STORAGE_KEY, next);
				}
				return next;
			});
		}
	};
}

export const theme = createThemeStore();
