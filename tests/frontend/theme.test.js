/**
 * Tests for static/js/theme.js
 *
 * Theme system: auto/dark/light three-state toggle, localStorage persistence,
 * OS preference detection, and FOUC prevention compatibility
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import vm from 'vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcPath = join(__dirname, '../../static/js/theme.js');
const sourceCode = readFileSync(srcPath, 'utf-8');

function loadThemeModule() {
    const store = {};
    globalThis.localStorage = {
        getItem: (key) => store[key] || null,
        setItem: (key, val) => { store[key] = String(val); },
        removeItem: (key) => { delete store[key]; },
        clear: () => { Object.keys(store).forEach(k => delete store[k]); }
    };

    globalThis.matchMedia = vi.fn((query) => ({
        matches: query.includes('dark'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn()
    }));

    const mockElement = {
        _attributes: {},
        setAttribute(name, value) { this._attributes[name] = value; },
        getAttribute(name) { return this._attributes[name] || null; }
    };
    
    globalThis.document = {
        documentElement: mockElement,
        dispatchEvent: vi.fn(),
        getElementById: vi.fn()
    };

    globalThis.CustomEvent = class CustomEvent {
        constructor(type, options = {}) {
            this.type = type;
            this.detail = options.detail || null;
        }
    };

    const wrappedCode = `(function() { ${sourceCode}\n
        globalThis.ThemeSystem = ThemeSystem;
    })();`;
    vm.runInThisContext(wrappedCode, { filename: 'theme.js' });

    return store;
}

describe('ThemeSystem', () => {
    let store;

    beforeEach(() => {
        store = loadThemeModule();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe('constants', () => {
        it('defines STORAGE_KEY', () => {
            expect(ThemeSystem.STORAGE_KEY).toBe('gpu-hot-theme-mode');
        });

        it('defines LEGACY_KEY', () => {
            expect(ThemeSystem.LEGACY_KEY).toBe('gpu-hot-theme');
        });

        it('defines DARK and LIGHT and AUTO constants', () => {
            expect(ThemeSystem.DARK).toBe('dark');
            expect(ThemeSystem.LIGHT).toBe('light');
            expect(ThemeSystem.AUTO).toBe('auto');
        });
    });

    describe('init', () => {
        it('applies stored mode preference', () => {
            store['gpu-hot-theme-mode'] = 'light';
            ThemeSystem.init();
            expect(document.documentElement.getAttribute('data-theme')).toBe('light');
        });

        it('follows OS preference when mode is auto', () => {
            ThemeSystem.init();
            expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        });

        it('defaults to dark when no preference and no OS detection', () => {
            globalThis.matchMedia = vi.fn(() => ({
                matches: false,
                media: '',
                addEventListener: vi.fn()
            }));
            ThemeSystem.init();
            expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        });

        it('dispatches themechange event', () => {
            ThemeSystem.init();
            expect(document.dispatchEvent).toHaveBeenCalled();
            const event = document.dispatchEvent.mock.calls[0][0];
            expect(event.type).toBe('themechange');
            expect(event.detail.theme).toBeDefined();
        });

        it('migrates legacy storage key', () => {
            store['gpu-hot-theme'] = 'light';
            ThemeSystem.init();
            expect(store['gpu-hot-theme-mode']).toBe('light');
            expect(store['gpu-hot-theme']).toBeUndefined();
        });
    });

    describe('getMode', () => {
        it('returns stored mode when set', () => {
            store['gpu-hot-theme-mode'] = 'dark';
            expect(ThemeSystem.getMode()).toBe('dark');
        });

        it('returns auto when no mode stored', () => {
            expect(ThemeSystem.getMode()).toBe('auto');
        });
    });

    describe('resolveTheme', () => {
        it('resolves dark to dark', () => {
            expect(ThemeSystem.resolveTheme('dark')).toBe('dark');
        });

        it('resolves light to light', () => {
            expect(ThemeSystem.resolveTheme('light')).toBe('light');
        });

        it('resolves auto to OS preference', () => {
            expect(ThemeSystem.resolveTheme('auto')).toBe('dark');
        });

        it('resolves auto to dark when OS detection unavailable', () => {
            globalThis.matchMedia = undefined;
            expect(ThemeSystem.resolveTheme('auto')).toBe('dark');
        });
    });

    describe('getOSPreference', () => {
        it('returns dark when OS prefers dark', () => {
            globalThis.matchMedia = vi.fn((query) => ({
                matches: query.includes('dark'),
                media: query,
                addEventListener: vi.fn()
            }));
            expect(ThemeSystem.getOSPreference()).toBe('dark');
        });

        it('returns light when OS prefers light', () => {
            globalThis.matchMedia = vi.fn((query) => ({
                matches: query.includes('light'),
                media: query,
                addEventListener: vi.fn()
            }));
            expect(ThemeSystem.getOSPreference()).toBe('light');
        });

        it('returns null when matchMedia not available', () => {
            globalThis.matchMedia = undefined;
            expect(ThemeSystem.getOSPreference()).toBeNull();
        });
    });

    describe('applyTheme', () => {
        it('sets data-theme attribute', () => {
            ThemeSystem.applyTheme('light');
            expect(document.documentElement.getAttribute('data-theme')).toBe('light');
        });

        it('dispatches themechange event with theme detail', () => {
            ThemeSystem.applyTheme('dark');
            expect(document.dispatchEvent).toHaveBeenCalled();
            const event = document.dispatchEvent.mock.calls[document.dispatchEvent.mock.calls.length - 1][0];
            expect(event.type).toBe('themechange');
            expect(event.detail.theme).toBe('dark');
        });
    });

    describe('toggle', () => {
        it('cycles from auto to dark', () => {
            ThemeSystem.toggle();
            expect(store['gpu-hot-theme-mode']).toBe('dark');
        });

        it('cycles from dark to light', () => {
            store['gpu-hot-theme-mode'] = 'dark';
            ThemeSystem.toggle();
            expect(document.documentElement.getAttribute('data-theme')).toBe('light');
            expect(store['gpu-hot-theme-mode']).toBe('light');
        });

        it('cycles from light to auto', () => {
            store['gpu-hot-theme-mode'] = 'light';
            ThemeSystem.toggle();
            expect(store['gpu-hot-theme-mode']).toBe('auto');
        });

        it('stores mode in localStorage', () => {
            ThemeSystem.toggle();
            expect(localStorage.getItem('gpu-hot-theme-mode')).toBe('dark');
        });
    });

    describe('resetToAuto', () => {
        it('clears stored preference', () => {
            store['gpu-hot-theme-mode'] = 'light';
            ThemeSystem.resetToAuto();
            expect(localStorage.getItem('gpu-hot-theme-mode')).toBeNull();
        });

        it('applies OS preference after reset', () => {
            store['gpu-hot-theme-mode'] = 'light';
            globalThis.matchMedia = vi.fn((query) => ({
                matches: query.includes('dark'),
                media: query,
                addEventListener: vi.fn()
            }));
            ThemeSystem.resetToAuto();
            expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        });
    });

    describe('getCurrentTheme', () => {
        it('returns current theme from attribute', () => {
            document.documentElement._attributes['data-theme'] = 'light';
            expect(ThemeSystem.getCurrentTheme()).toBe('light');
        });

        it('returns dark as default when no attribute', () => {
            document.documentElement._attributes = {};
            expect(ThemeSystem.getCurrentTheme()).toBe('dark');
        });
    });

    describe('updateToggleButton', () => {
        it('updates aria-label based on mode', () => {
            const mockBtn = {
                setAttribute: vi.fn(),
                querySelector: vi.fn()
            };
            document.getElementById = vi.fn(() => mockBtn);
            
            ThemeSystem._updateToggleButton('dark');
            expect(mockBtn.setAttribute).toHaveBeenCalledWith('aria-label', 'Dark theme. Click for light mode');
        });

        it('handles missing button gracefully', () => {
            document.getElementById = vi.fn(() => null);
            ThemeSystem._updateToggleButton('dark');
            expect(true).toBe(true);
        });
    });

    describe('prefersReducedMotion', () => {
        it('returns true when reduced motion is preferred', () => {
            globalThis.matchMedia = vi.fn((query) => ({
                matches: query.includes('reduce')
            }));
            expect(ThemeSystem.prefersReducedMotion()).toBe(true);
        });

        it('returns false when reduced motion is not preferred', () => {
            globalThis.matchMedia = vi.fn(() => ({
                matches: false
            }));
            expect(ThemeSystem.prefersReducedMotion()).toBe(false);
        });
    });
});