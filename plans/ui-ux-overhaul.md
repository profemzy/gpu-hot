# Plan: Professional UI/UX Overhaul — Themes, Polish & Accessibility

> Source PRD: `docs/PRD_UI_UX_OVERHAUL.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Frontend-only** — no backend/Python changes. All work is in `static/`, `templates/`, and SVG assets
- **Theme system**: `[data-theme="light"]` attribute on `<html>`, persisted via `localStorage`. OS preference (`prefers-color-scheme`) is the default fallback
- **Iconography**: Single `static/icons.svg` sprite sheet with `<symbol>` elements, no external icon libraries
- **WebSocket data format**: unchanged — no modifications to the data structure sent from the backend
- **Chart.js**: factory function pattern for configs stays in place; color configs will be resolved via `getComputedStyle()` at runtime
- **Test framework**: Vitest for frontend tests (existing `tests/frontend/` setup)
- **CSS architecture**: all colors flow through CSS custom properties; no hardcoded `rgba()` color values after migration
- **No page reload on theme toggle**: CSS attribute swap + Chart.js `.update()` only

---

## Phase 1: Theme System + Light Mode

**User stories**: #1, #2, #3, #15

### What to build

Build the complete theme infrastructure so that the dashboard works in both dark and light modes. The theme auto-detects from the OS preference, can be manually toggled via a sun/moon button in the sidebar, and persists the choice in `localStorage`. All chart colors adapt by reading CSS custom properties at runtime. Light mode meets WCAG AA contrast ratios.

This is a vertical slice because: the theme toggle is visible and functional, charts re-render in the correct theme, all CSS surfaces adapt, and light mode is a complete, usable theme — not a partial stub.

### Acceptance criteria

- [ ] `static/js/theme.js` — detects `prefers-color-scheme`, applies `[data-theme]` attribute to `<html>`, provides toggle function with `localStorage` persistence
- [ ] Sun/moon icon toggle button visible in sidebar bottom section (next to GitHub link)
- [ ] `[data-theme="light"]` overrides in `static/css/tokens.css` redefine all background, text, border, metric, and sparkline color variables
- [ ] All hardcoded `rgba(255, 255, 255, ...)` values in `layout.css` and `components.css` replaced with CSS custom properties or theme-aware token references
- [ ] Chart.js `SPARK` constants replaced with `getChartColors()` function that reads `getComputedStyle()` — charts re-render correctly on theme toggle
- [ ] `static/js/chart-manager.js` — all active chart instances call `.update()` when theme changes
- [ ] Light mode text/element contrast meets WCAG AA (4.5:1 normal, 3:1 large)
- [ ] No page reload on theme toggle — instantaneous CSS swap
- [ ] Tests: `theme.js` module tests (detection, storage, toggle, OS fallback)

---

## Phase 2: Skeleton Loading States

**User stories**: #10

### What to build

Implement a hybrid loading flow: show the existing pulsing dot during WebSocket connection, then swap to skeleton placeholder cards (with shimmer animation) once connected but before GPU data arrives. Skeletons mimic the final card layout so the page doesn't jump when real data fills in. Works correctly in both dark and light themes.

This is a vertical slice because: the complete loading path is functional — connection → skeleton → real data — with proper theme-aware styling and smooth transitions.

### Acceptance criteria

- [ ] `static/css/skeletons.css` — shimmer animation (`@keyframes shimmer`, 1.5s loop), skeleton bar styles, theme-aware background colors
- [ ] Skeleton card template: GPU name bar, 4 metric number placeholders, sparkline rectangle placeholder, bullet bar placeholders
- [ ] `socket-handlers.js` — manages three states: connecting (pulsing dot), skeleton (placeholder cards), data (real GPU cards)
- [ ] Skeleton cards use theme-appropriate colors (light vs dark shimmer backgrounds)
- [ ] Skeleton state auto-transitions to real data without layout jump
- [ ] Tests: skeleton loading state flow in `tests/frontend/`

---

## Phase 3: Iconography + Card Redesign

**User stories**: #4, #8, #9

### What to build

Create the SVG icon sprite sheet (~15 icons) and redesign the GPU card components. Overview cards become contained cards with rounded corners, temperature-colored left border indicators (green/yellow/red), and inline SVG icons next to metric labels. The aggregate summary row upgrades from a single "Total VRAM" bar to a full header bar showing total GPUs online, aggregate power draw, average temperature, and total VRAM. Detail view gets section dividers with icon labels.

This is a vertical slice because: the full card system (overview + aggregate + detail) is redesigned end-to-end, with icons throughout and theme-compatible styling.

### Acceptance criteria

- [ ] `static/icons.svg` — sprite sheet with ~15 icons: `gpu`, `thermometer`, `bolt`, `memory-chip`, `fan`, `speedometer`, `cpu`, `chip`, `network`, `disk`, `sun`, `moon`, `chevron-down`, `plug`, `activity`
- [ ] Icon sprite linked in `templates/index.html` (hidden `<svg>` or `<link>`)
- [ ] Overview cards: contained card design with 8px rounded corners, 1px border, 3px left temperature-colored border strip (green <65°C, yellow 65-80°C, red >80°C)
- [ ] Overview cards: sparkline moves to top edge as full-width 32px band
- [ ] Overview cards: metric labels accompanied by inline SVG icons
- [ ] Card hover effect: subtle lift + shadow (theme-appropriate shadow colors)
- [ ] Aggregate summary: header bar with total VRAM, GPU count, aggregate power, avg temp, max temp — icon + value pairs
- [ ] Detail view: section dividers with icon labels ("Performance", "Clocks & Connectivity", "Media & Health")
- [ ] `gpu-cards.js` — updated `createOverviewCard()` and `createGPUCard()` functions with new structure
- [ ] Both themes render cards correctly with appropriate colors
- [ ] Tests: card HTML structure tests, icon presence tests

---

## Phase 4: Animated Numbers + Chart Polish

**User stories**: #5, #6, #7

### What to build

Add animated number transitions for hero metrics using a vanilla JS `requestAnimationFrame` utility. Gradient fills appear on all detail-view sparklines (overview sparklines stay minimal). A hover crosshair plugin is added to detail charts for pinpoint value inspection at specific timestamps.

This is a vertical slice because: numbers animate on change, charts have richer visual fills, and the hover crosshair interaction works — completing the visual polish layer.

### Acceptance criteria

- [ ] `static/js/animations.js` — `animateValue(element, start, end, duration, easing)` utility with `easeOutExpo`
- [ ] Hero metrics (utilization, temperature, VRAM, power) animate on value change in both overview and detail views
- [ ] Secondary metrics (clocks, PCIe, encoder/decoder) update instantly — no animation
- [ ] Debouncing: new value arriving mid-animation cancels old animation and starts new one from current interpolated value
- [ ] Detail sparklines: gradient fills using metric identity colors at ~8% opacity
- [ ] Overview sparklines: remain minimal (stroke only, no fill)
- [ ] Hover crosshair plugin: vertical dashed line follows cursor on detail charts, tooltip shows timestamp + all visible dataset values
- [ ] Chart configs reference CSS custom properties — gradient fill colors adapt on theme toggle
- [ ] Tests: `animations.js` unit tests (interpolation math, easing output, cancellation behavior)

---

## Phase 5: Accessibility + Mobile + Polish

**User stories**: #11, #12, #13, #14

### What to build

Complete the accessibility and mobile pass. Add ARIA labels to all interactive elements and metric values. Implement keyboard navigation (Tab order through sidebar, Escape to close drawer, Enter/Space for process toggle). Add visible focus rings. Respect `prefers-reduced-motion` to disable animations for sensitive users. Make GPU cards horizontally scrollable on mobile (swipe to browse). Ensure all remaining hardcoded colors are replaced with tokens.

This is a vertical slice because: the dashboard is fully navigable via keyboard, readable by screen readers, comfortable on mobile, and respectful of motion preferences — completing the professional UI/UX overhaul.

### Acceptance criteria

- [ ] ARIA labels on sidebar buttons, theme toggle, process header, drawer close, GPU cards, chart containers
- [ ] GPU card metric values: `aria-label="GPU X <metric>: <value>"` pattern
- [ ] Chart canvases: `role="img"` with descriptive `aria-label`
- [ ] Keyboard navigation: Tab order flows sidebar → main → processes → theme toggle
- [ ] Escape key closes chart drawer
- [ ] Enter/Space toggles process section
- [ ] Visible focus rings: 2px outline with `var(--accent)`, 2px offset, visible in both themes
- [ ] `@media (prefers-reduced-motion: reduce)` disables: number animations, card hover transforms, skeleton shimmer, bullet bar transitions, drawer slide animation
- [ ] Mobile (≤768px): overview grid becomes horizontal scroll with `scroll-snap-type: x mandatory`, cards are `min-width: 85vw`
- [ ] Mobile: sidebar buttons increase to 48×48 touch targets
- [ ] All remaining hardcoded `rgba()` color values replaced with CSS custom properties
- [ ] Tests: keyboard shortcut tests, ARIA label presence checks, mobile scroll behavior verification
