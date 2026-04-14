/**
 * Theme System — Auto / Dark / Light
 *
 * Three-state toggle: Auto (follows OS) → Dark → Light → Auto
 * Priority: localStorage mode > OS preference > dark fallback
 * Emits 'themechange' event on document for other modules to react
 */
const ThemeSystem = {
  STORAGE_KEY: 'gpu-hot-theme-mode',
  LEGACY_KEY: 'gpu-hot-theme',
  DARK: 'dark',
  LIGHT: 'light',
  AUTO: 'auto',

  init() {
    this._migrate();

    const mode = this.getMode();
    const theme = this.resolveTheme(mode);
    this.applyTheme(theme);
    this._updateToggleButton(mode);
    this._watchOSPreference();
  },

  _migrate() {
    const legacy = localStorage.getItem(this.LEGACY_KEY);
    if (legacy) {
      localStorage.setItem(this.STORAGE_KEY, legacy);
      localStorage.removeItem(this.LEGACY_KEY);
    }
  },

  getMode() {
    return localStorage.getItem(this.STORAGE_KEY) || this.AUTO;
  },

  resolveTheme(mode) {
    if (mode === this.DARK) return this.DARK;
    if (mode === this.LIGHT) return this.LIGHT;
    return this.getOSPreference() || this.DARK;
  },

  getOSPreference() {
    if (!window.matchMedia) return null;
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) return this.DARK;
    if (window.matchMedia('(prefers-color-scheme: light)').matches) return this.LIGHT;
    return null;
  },

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  },

  toggle() {
    const currentMode = this.getMode();
    const modes = [this.AUTO, this.DARK, this.LIGHT];
    const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
    const nextMode = modes[nextIndex];

    localStorage.setItem(this.STORAGE_KEY, nextMode);
    const theme = this.resolveTheme(nextMode);
    this.applyTheme(theme);
    this._updateToggleButton(nextMode);
  },

  resetToAuto() {
    localStorage.removeItem(this.STORAGE_KEY);
    const theme = this.resolveTheme(this.AUTO);
    this.applyTheme(theme);
    this._updateToggleButton(this.AUTO);
  },

  getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || this.DARK;
  },

  _updateToggleButton(mode) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const sunIcon = btn.querySelector('.icon-sun');
    const moonIcon = btn.querySelector('.icon-moon');
    const autoIcon = btn.querySelector('.icon-auto');

    if (sunIcon) sunIcon.style.display = 'none';
    if (moonIcon) moonIcon.style.display = 'none';
    if (autoIcon) autoIcon.style.display = 'none';

    if (mode === this.DARK && moonIcon) {
      moonIcon.style.display = 'block';
    } else if (mode === this.LIGHT && sunIcon) {
      sunIcon.style.display = 'block';
    } else if (mode === this.AUTO && autoIcon) {
      autoIcon.style.display = 'block';
    } else if (mode === this.AUTO && moonIcon) {
      moonIcon.style.display = 'block';
    }

    const labels = {};
    labels[this.AUTO] = 'System theme. Click for dark mode';
    labels[this.DARK] = 'Dark theme. Click for light mode';
    labels[this.LIGHT] = 'Light theme. Click for system theme';

    btn.setAttribute('aria-label', labels[mode] || 'Switch theme');
    btn.setAttribute('title', labels[mode] || 'Switch theme');
    btn.setAttribute('aria-pressed', String(mode !== this.AUTO));
  },

  _watchOSPreference() {
    if (!window.matchMedia) return;
    const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
    darkQuery.addEventListener('change', () => {
      if (this.getMode() === this.AUTO) {
        const theme = this.resolveTheme(this.AUTO);
        this.applyTheme(theme);
      }
    });
  },

  prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeSystem;
}

window.ThemeSystem = ThemeSystem;