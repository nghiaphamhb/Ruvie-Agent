import { mount } from 'svelte';
import App from './App.svelte';
import './styles/base.css';
import './styles/workspace.css';
import { initI18n } from './lib/i18n/index.ts';

// Resolve the locale before the first visible UI or auth request.
void initI18n().then(() => mount(App, { target: document.getElementById('app')! }));
