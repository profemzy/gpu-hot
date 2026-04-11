# PRD: Professional UI/UX Overhaul — Themes, Polish & Accessibility

## Problem Statement

The GPU Hot dashboard UI feels bare and one-dimensional. It only supports dark mode, uses no iconography, has static number transitions, minimal chart styling, and no accessibility considerations. For a monitoring tool that users may keep open for hours, the interface needs to feel polished, professional, and accessible — supporting both dark and light themes with visual depth, micro-interactions, and proper keyboard/screen-reader support.

## Solution

A comprehensive frontend redesign that introduces:
- Automatic dark/light theme detection with manual override toggle
- Inline SVG iconography for instant metric recognition
- Animated number transitions on hero metrics
- Gradient-filled sparkline charts with hover crosshairs
- Redesigned GPU cards with status-border indicators and wider sparkline bands
- Skeleton loading screens instead of plain "waiting" messages
- WCAG AA accessibility compliance (contrast, ARIA, keyboard nav, reduced motion)
- Improved mobile experience with horizontal-scrolling GPU cards and larger touch targets

## User Stories

1. As a user whose OS is set to light mode, I want the dashboard to automatically match my system theme, so that I'm not blinded by a dark screen in a bright environment
2. As a user, I want a visible theme toggle in the sidebar, so that I can manually switch between dark and light mode regardless of my OS setting
3. As a user, I want my theme preference to persist across sessions, so that I don't have to re-select it every time I open the dashboard
4. As a user, I want to see icons next to metric labels (temperature, power, memory, fan, etc.), so that I can identify metrics at a glance without reading text
5. As a user, I want GPU utilization numbers to smoothly animate when they change, so that I can perceive the rate and direction of change without chart analysis
6. As a user analyzing a single GPU, I want sparkline charts to have subtle gradient fills under the line, so that trends are more visually prominent
7. As a user hovering over a detail-view chart, I want a vertical crosshair line to appear, so that I can pinpoint the exact value at a specific timestamp
8. As a user viewing multiple GPUs, I want each GPU to appear as a contained card with a colored left-border status indicator (green/yellow/red by temperature), so that I can spot thermal issues across the cluster instantly
9. As a user viewing the aggregate summary, I want a header bar showing total GPUs online, aggregate power draw, average temperature, and total VRAM usage, so that I get cluster-level context before drilling into individual GPUs
10. As a user waiting for the dashboard to load, I want to see skeleton placeholder cards that mimic the final layout, so that the interface feels responsive and I know what's coming
11. As a mobile user, I want to swipe horizontally between GPU cards instead of scrolling through a long vertical stack, so that browsing GPUs feels natural on a phone
12. As a keyboard user, I want to Tab through sidebar navigation buttons and press Escape to close the chart drawer, so that I can navigate without a mouse
13. As a screen-reader user, I want ARIA labels on all interactive elements and metric values, so that I can understand the dashboard through audio feedback
14. As a user with vestibular sensitivity, I want the dashboard to respect my OS's "reduce motion" setting and disable animated transitions, so that the interface doesn't cause discomfort
15. As a user in light mode, I want all text and UI elements to meet WCAG AA contrast ratios, so that content is readable without eye strain

## Implementation Decisions

### Theme System
- **Approach**: Auto-detect via `prefers-color-scheme` CSS media query + manual toggle stored in `localStorage`
- **Override logic**: `localStorage` theme > OS preference > default to dark
- **Implementation**: Extend `tokens.css` with `[data-theme="light"]` selectors that redefine all CSS custom properties (backgrounds, text, borders, metric colors, sparkline strokes)
- **Toggle UI**: Small sun/moon icon button added to `.sidebar-bottom`, next to the GitHub link
- **New file**: `static/js/theme.js` — handles detection, toggle, localStorage persistence, and initial DOM attribute application
- **Chart adaptation**: Chart.js configs in `chart-config.js` will reference CSS custom properties via `getComputedStyle()` so charts automatically re-render with theme-appropriate colors

### Iconography
- **Format**: Single `static/icons.svg` sprite file with `<symbol>` elements, referenced via `<use href="/static/icons.svg#icon-name">`
- **Style**: Minimal 24×24 line icons (1.5px stroke, rounded caps/joins) — consistent across the UI
- **Icons needed** (~15): `gpu`, `thermometer`, `bolt` (power), `memory-chip`, `fan`, `speedometer`, `cpu`, `chip`, `network` (PCIe), `disk`, `sun`, `moon`, `chevron-down`, `plug` (processes), `activity` (utilization)
- **Placement**: Inline `<svg>` elements in GPU cards (next to metric labels), sidebar buttons (GPU number + icon), system metrics (CPU/RAM icons), theme toggle
- **No external dependency** — sprite is hand-authored SVG, ~3-4KB total

### Animated Number Transitions
- **New file**: `static/js/animations.js` — single utility function:
  ```js
  function animateValue(element, start, end, duration = 300, easing = easeOutExpo)
  ```
- **Easing**: `easeOutExpo` — snappy attack, smooth deceleration
- **Scope**: Only hero metrics (utilization, temperature, VRAM, power) on overview cards and detail views. Secondary metrics (clocks, PCIe, encoder/decoder) update instantly to avoid jitter
- **Respects `prefers-reduced-motion`**: If set, numbers update instantly (no animation)
- **Debouncing**: If a new value arrives while a previous animation is in-flight, cancel the old one and start a new animation from the current interpolated value

### Chart Redesign
- **Gradient fills**: Each metric type uses its identity color at 8% opacity gradient fill (defined in `METRIC_FILL_COLORS` in `chart-config.js`, currently unused). Dark mode: lighter fills. Light mode: slightly darker fills for contrast
- **Overview sparklines**: Stay minimal — single stroke, no fill, threshold coloring (orange above 80% utilization). The overview is for scanning, not analysis
- **Detail sparklines**: Gradient fills + hover crosshair via Chart.js tooltip crosshair plugin (custom plugin, ~30 lines)
- **Crosshair plugin**: Vertical dashed line at mouse X position, tooltip shows timestamp + all visible dataset values
- **Chart resize**: Charts re-render when theme changes (colors pulled from `getComputedStyle`)

### Card Redesign
- **Overview cards**: Redesign from 3-column flat layout to contained cards:
  - Rounded corners (8px), subtle border (`1px solid var(--border-subtle)`)
  - 3px left border colored by temperature status (green <65°C, yellow 65-80°C, red >80°C)
  - Sparkline moves to top edge (full-width, 32px tall band)
  - Metrics below in a cleaner grid with inline SVG icons
  - Hover lifts card with subtle shadow (dark: `rgba(0,0,0,0.3)`, light: `rgba(0,0,0,0.08)`)
- **Aggregate summary**: Upgrade from single "Total VRAM" bar to a header bar:
  - Row 1: Total VRAM (used/total), cluster GPU count, online nodes (hub mode)
  - Row 2: Aggregate power draw (sum), average temperature, max temperature
  - Compact, single-line layout with icon + value pairs
- **Detail view**: Keep three-tier structure (hero numbers → sparklines → secondary metrics)
  - Add section labels with icons ("Performance", "Clocks & Connectivity", "Media & Health")
  - Add subtle horizontal dividers between sections
  - Increase spacing between sparkline rows
  - Sparkline gradient fills (as above)

### Skeleton Loading States
- **New file**: `static/css/skeletons.css` — skeleton animation styles
- **Approach**: Hybrid
  - Phase 1 (WebSocket connecting): Pulsing dot + "Connecting…" (existing)
  - Phase 2 (connected, waiting for data): Skeleton cards with shimmer animation
- **Skeleton card shape**: GPU name bar (wide, short), 4 metric number placeholders (short, wide), sparkline placeholder (flat rectangle), bullet bar placeholders
- **Animation**: Linear gradient sweep across skeleton bars (`@keyframes shimmer` — 1.5s loop)
- **Modified**: `socket-handlers.js` manages skeleton state transitions

### Mobile Improvements
- **Horizontal scroll GPU cards**: On screens ≤768px, overview grid becomes `display: flex; overflow-x: auto; scroll-snap-type: x mandatory`. Each card is `min-width: 85vw; scroll-snap-align: start`. Swipe-to-browse feel
- **Touch targets**: Sidebar buttons increase from 40×40 to 48×48 on mobile
- **Drawer**: Already full-width on mobile — keep as-is
- **Process table**: Already adapts — keep as-is
- **No content hiding**: Sparklines remain visible, metrics stay accessible

### Accessibility
- **ARIA labels**: Added to all interactive elements (sidebar buttons, theme toggle, process header, drawer close, GPU cards, chart containers)
- **Keyboard navigation**:
  - Tab order flows: sidebar buttons → main content → processes → theme toggle
  - `Escape` closes chart drawer
  - `Enter`/`Space` toggles process section
  - Focus rings: 2px outline with `var(--accent)` color, 2px offset, visible on both themes
- **Screen reader**: GPU card metric values get `aria-label="GPU 0 utilization: 85 percent"`, chart canvases get `role="img"` with descriptive labels
- **Reduced motion**: `@media (prefers-reduced-motion: reduce)` disables:
  - Animated number transitions (instant updates)
  - Card hover transforms
  - Skeleton shimmer (replaced with static placeholders)
  - Bullet bar transitions
  - Drawer slide animation (instant show/hide)

### File Changes Summary

| File | Change |
|------|--------|
| `static/css/tokens.css` | Add `[data-theme="light"]` variable overrides, add `--focus-ring` token |
| `static/css/layout.css` | Mobile improvements, focus ring styles |
| `static/css/components.css` | Card redesign, skeleton styles, improved spacing/dividers |
| `static/css/skeletons.css` | **NEW** — Shimmer animation, skeleton card templates |
| `static/js/theme.js` | **NEW** — Theme detection, toggle, persistence |
| `static/js/animations.js` | **NEW** — `animateValue()` utility |
| `static/js/chart-config.js` | Gradient fill configs, hover crosshair plugin |
| `static/js/chart-manager.js` | Apply gradient fills, theme-aware chart re-rendering |
| `static/js/gpu-cards.js` | Card redesign with icons, status borders, skeleton injection |
| `static/js/ui.js` | Keyboard navigation, focus management, theme toggle handler |
| `static/js/socket-handlers.js` | Skeleton state management during loading |
| `static/js/app.js` | Initialize theme system, register animations |
| `static/icons.svg` | **NEW** — SVG icon sprite sheet |
| `templates/index.html` | Add theme toggle SVG, skeleton markup, ARIA attributes, SVG sprite `<link>` |

### CSS Architecture Decision
All theme-related variables flow through `tokens.css`. Light mode is implemented as `[data-theme="light"]` overrides on `:root`, so no CSS logic changes are needed — just redefine the custom property values. Hardcoded `rgba(255, 255, 255, ...)` values in `layout.css` and `components.css` will be replaced with token variables (e.g., `--rgba-hover-bg`, `--bg-subtle-card`, `--border-color`) or moved into the token system so they invert automatically with the theme.

### Chart.js Theme Integration
Chart configs currently use hardcoded color constants (`SPARK` object). These will be replaced with a `getChartColors()` function that reads computed CSS custom properties, so charts automatically adapt when the theme toggles. The function will be called on initial load AND on theme change (with `.update()` calls on all active chart instances).

## Testing Decisions

### What Makes a Good Test
Only test external behavior, not implementation details. A good test for this PRD verifies:
- Theme toggle changes `[data-theme]` attribute and `localStorage` value
- OS preference is respected when no `localStorage` override exists
- Skeleton cards appear during loading and disappear when data arrives
- Animated number utility correctly interpolates values (test the math, not the DOM)
- ARIA labels are present on key interactive elements
- Keyboard shortcuts work (Escape closes drawer)

### Modules to Test
- **`theme.js`**: Theme detection logic, localStorage read/write, toggle behavior, OS preference fallback
- **`animations.js`**: Value interpolation math, easing function output, cancellation behavior
- **`gpu-cards.js`**: Card HTML generation (verify structure contains expected elements, classes, ARIA labels)
- **Frontend integration**: Skeleton loading state flow (connect → skeleton → real data)

### Prior Art
The project already has a test setup:
- `tests/unit/` — Python unit tests (pytest) for backend
- `tests/frontend/` — Frontend tests (Vitest, per `vitest.config.js`)
- `tests/docker-compose.unittest.yml` — Docker-based test execution
- `run_tests.sh` — Test runner script

New frontend tests should be added to `tests/frontend/` using Vitest, testing the new JS modules (`theme.js`, `animations.js`) and DOM behavior.

## Out of Scope

- **Backend changes** — No modifications to `core/` Python code, FastAPI routes, or WebSocket handlers
- **Chart data format** — The data structure sent over WebSocket remains unchanged; this is purely a frontend rendering upgrade
- **New metrics** — No new GPU or system metrics are being collected; we're only improving how existing metrics are displayed
- **Multi-language/i18n** — No translation support added; all text remains in English
- **Custom themes** — Beyond dark/light, no additional color themes (e.g., "midnight blue", "solarized") are in scope
- **Chart type changes** — No new chart types (bar, pie, radar) are being added; all existing charts remain line/sparkline
- **Data persistence** — No server-side storage of user preferences; theme preference is client-side only via `localStorage`
- **Performance profiling** — No changes to the monitoring polling interval, data collection, or WebSocket frequency
- **Favicon redesign** — The existing `static/favicon.svg` remains as-is

## Further Notes

### Migration Path
This is a drop-in replacement for the existing frontend. Users don't need to change anything about their deployment — the HTML template, CSS, and JS files are all updated in place. The Docker image builds identically.

### Performance Considerations
- Skeleton shimmer animation uses `will-change: transform` for GPU compositing
- Animated number transitions use `requestAnimationFrame` (no layout thrashing)
- Gradient fills add ~1KB per chart in Chart.js internal state — negligible for 120 data points
- SVG icon sprite is ~4KB, cached by browser on first load
- Theme toggle does NOT trigger page reload — CSS attribute swap + chart re-render only

### Design Consistency Rules
- All colors flow through CSS custom properties — zero hardcoded color values in CSS after migration
- All icons use the sprite system — no inline `<path>` elements except the existing GitHub octicon
- All animations respect `prefers-reduced-motion` — check every `transition` and `animation` declaration
- All interactive elements have `:focus-visible` styles — check every `:hover` has a matching `:focus-visible`
- Chart configs are generated by factory functions — no raw config objects scattered across files

### Future Opportunities (Not In Scope)
- Custom alert/notification system (e.g., "GPU 2 temperature exceeded 90°C")
- Historical data persistence (store metrics across restarts)
- Export charts as PNG/CSV
- Custom dashboard layouts (drag-and-drop cards)
- Per-GPU custom names/labels
- WebSocket compression for high-GPU-count clusters
