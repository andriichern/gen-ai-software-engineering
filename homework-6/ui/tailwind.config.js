/** @type {import('tailwindcss').Config} */
export default {
	darkMode: ['selector', '[data-theme="dark"]'],
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				surface: 'rgb(var(--color-surface) / <alpha-value>)',
				'surface-raised': 'rgb(var(--color-surface-raised) / <alpha-value>)',
				border: 'rgb(var(--color-border) / <alpha-value>)',
				text: 'rgb(var(--color-text) / <alpha-value>)',
				muted: 'rgb(var(--color-muted) / <alpha-value>)',
				accent: 'rgb(var(--color-accent) / <alpha-value>)',
				success: 'rgb(var(--color-success) / <alpha-value>)',
				warning: 'rgb(var(--color-warning) / <alpha-value>)',
				danger: 'rgb(var(--color-danger) / <alpha-value>)'
			}
		}
	},
	plugins: []
};
