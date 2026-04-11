/**
 * Theme System — Auto-detect + Manual Toggle
 * 
 * Priority: localStorage override > OS preference > default (dark)
 * Emits 'themechange' event on document for other modules to react
 */

const ThemeSystem = {
  STORAGE_KEY: 'gpu-hot-theme',
  DARK: 'dark',
  LIGHT: 'light',
  
  /**
   * Initialize theme system on page load
   * Applies stored preference or falls back to OS preference
   */
  init() {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    const osPreference = this.getOSPreference();
    
    // Priority: stored > OS > default dark
    const theme = stored || osPreference || this.DARK;
    this.applyTheme(theme);
    
    // Listen for OS preference changes (only if no stored override)
    this.watchOSPreference();
  },
  
  /**
   * Get OS color scheme preference
   * @returns {'dark'|'light'|null}
   */
  getOSPreference() {
    if (!window.matchMedia) return null;
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) return this.DARK;
    if (window.matchMedia('(prefers-color-scheme: light)').matches) return this.LIGHT;
    return null;
  },
  
  /**
   * Watch for OS preference changes
   * Only applies if user hasn't set a manual override
   */
  watchOSPreference() {
    if (!window.matchMedia) return;
    
    const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const lightQuery = window.matchMedia('(prefers-color-scheme: light)');
    
    darkQuery.addEventListener('change', (e) => {
      if (!localStorage.getItem(this.STORAGE_KEY)) {
        this.applyTheme(e.matches ? this.DARK : this.LIGHT);
      }
    });
  },
  
  /**
   * Apply theme to document
   * @param {'dark'|'light'} theme
   */
  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    this.updateToggleButton(theme);
    
    // Emit event for charts and other components
    document.dispatchEvent(new CustomEvent('themechange', { 
      detail: { theme } 
    }));
  },
  
  /**
   * Toggle between dark and light
   * Stores preference in localStorage
   */
  toggle() {
    const current = document.documentElement.getAttribute('data-theme') || this.DARK;
    const next = current === this.DARK ? this.LIGHT : this.DARK;
    
    localStorage.setItem(this.STORAGE_KEY, next);
    this.applyTheme(next);
  },
  
  /**
   * Clear stored preference and fall back to OS preference
   */
  resetToAuto() {
    localStorage.removeItem(this.STORAGE_KEY);
    const osPreference = this.getOSPreference();
    this.applyTheme(osPreference || this.DARK);
  },
  
  /**
   * Get current theme
   * @returns {'dark'|'light'}
   */
  getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || this.DARK;
  },
  
  /**
   * Update toggle button icon (sun/moon)
   * @param {'dark'|'light'} theme
   */
  updateToggleButton(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    
    const sunIcon = btn.querySelector('.icon-sun');
    const moonIcon = btn.querySelector('.icon-moon');
    
    if (sunIcon && moonIcon) {
      sunIcon.style.display = theme === this.DARK ? 'block' : 'none';
      moonIcon.style.display = theme === this.LIGHT ? 'block' : 'none';
    }
    
    btn.setAttribute('aria-label', 
      theme === this.DARK ? 'Switch to light mode' : 'Switch to dark mode'
    );
    btn.setAttribute('aria-pressed', theme === this.LIGHT ? 'true' : 'false');
  },
  
  /**
   * Check if reduced motion is preferred
   * @returns {boolean}
   */
  prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeSystem;
}

// Global assignment for non-module usage
window.ThemeSystem = ThemeSystem;