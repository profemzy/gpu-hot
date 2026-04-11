/**
 * Tests for static/js/theme.js
 *
 * Theme system: auto-detect, toggle, localStorage persistence
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
    // Mock localStorage
    const store = {};
    globalThis.localStorage = {
        getItem: (key) => store[key] || null,
        setItem: (key, val) => { store[key] = String(val); },
        removeItem: (key) => { delete store[key]; },
        clear: () => { Object.keys(store).forEach(k => delete store[k]); }
    };

    // Mock matchMedia
    globalThis.matchMedia = vi.fn((query) => ({
        matches: query.includes('dark'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn()
    }));

    // Mock document.documentElement
    const mockElement = {
        _attributes: {},
        setAttribute(name, value) {
            this._attributes[name] = value;
        },
        getAttribute(name) {
            return this._attributes[name] || null;
        }
    };
    
    globalThis.document = {
        documentElement: mockElement,
        dispatchEvent: vi.fn(),
        getElementById: vi.fn()
    };

    // Mock CustomEvent
    globalThis.CustomEvent = class CustomEvent {
        constructor(type, options = {}) {
            this.type = type;
            this.detail = options.detail || null;
        }
    };

    // Load the source and export to globalThis
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
        store = {};
    });

    describe('constants', () => {
        it('defines STORAGE_KEY', () => {
            expect(ThemeSystem.STORAGE_KEY).toBe('gpu-hot-theme');
        });

        it('defines DARK and LIGHT constants', () => {
            expect(ThemeSystem.DARK).toBe('dark');
            expect(ThemeSystem.LIGHT).toBe('light');
        });
    });

    describe('init', () => {
        it('applies stored preference over OS preference', () => {
            store['gpu-hot-theme'] = 'light';
            
            ThemeSystem.init();
            
            expect(document.documentElement.getAttribute('data-theme')).toBe('light');
        });

        it('applies OS preference when no stored preference', () => {
            // matchMedia returns dark by default in our mock
            ThemeSystem.init();
            
            expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        });

        it('defaults to dark when no preference available', () => {
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
        it('switches from dark to light', () => {
            document.documentElement._attributes['data-theme'] = 'dark';
            
            ThemeSystem.toggle();
            
            expect(document.documentElement.getAttribute('data-theme')).toBe('light');
            expect(store['gpu-hot-theme']).toBe('light');
        });

        it('switches from light to dark', () => {
            document.documentElement._attributes['data-theme'] = 'light';
            
            ThemeSystem.toggle();
            
            expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
            expect(store['gpu-hot-theme']).toBe('dark');
        });

        it('stores preference in localStorage', () => {
            document.documentElement._attributes['data-theme'] = 'dark';
            
            ThemeSystem.toggle();
            
            expect(localStorage.getItem('gpu-hot-theme')).toBe('light');
        });
    });

    describe('resetToAuto', () => {
        it('clears stored preference', () => {
            store['gpu-hot-theme'] = 'light';
            
            ThemeSystem.resetToAuto();
            
            expect(localStorage.getItem('gpu-hot-theme')).toBeNull();
        });

        it('applies OS preference after reset', () => {
            store['gpu-hot-theme'] = 'light';
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
        it('updates aria-label based on theme', () => {
            const mockBtn = {
                setAttribute: vi.fn(),
                querySelector: vi.fn((cls) => ({ style: {} }))
            };
            document.getElementById = vi.fn(() => mockBtn);
            
            ThemeSystem.updateToggleButton('dark');
            
            expect(mockBtn.setAttribute).toHaveBeenCalledWith('aria-label', 'Switch to light mode');
        });

        it('handles missing button gracefully', () => {
            document.getElementById = vi.fn(() => null);
            
            ThemeSystem.updateToggleButton('dark');
            
            // Should not throw
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