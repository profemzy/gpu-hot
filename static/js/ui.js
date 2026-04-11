/**
 * UI Interactions and navigation — GPU Studio
 * Sidebar-based navigation
 */

// Global state
let currentTab = 'overview';
let registeredGPUs = new Set();
let hasAutoSwitched = false;

// Toggle processes section
function toggleProcesses() {
    const content = document.getElementById('processes-content');
    const header = document.querySelector('.processes-header');
    const icon = document.querySelector('.toggle-icon');

    content.classList.toggle('expanded');
    if (header) header.classList.toggle('expanded');
    if (icon) icon.classList.toggle('expanded');
}

// Tab switching
function switchToView(viewName) {
    if (!viewName) return;

    currentTab = viewName;

    // Update sidebar button states
    document.querySelectorAll('.sidebar-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.view === viewName) {
            btn.classList.add('active');
        }
    });

    // Switch tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    const targetContent = document.getElementById(`tab-${viewName}`);
    if (!targetContent) return;

    targetContent.classList.add('active');

    // Chart resize for visible tab
    if (viewName.startsWith('gpu-')) {
        const gpuId = viewName.replace('gpu-', '');

        if (charts && charts[gpuId]) {
            Object.values(charts[gpuId]).forEach(chart => {
                if (!chart || !chart.options) return;
                try {
                    const orig = chart.options.animation;
                    chart.options.animation = false;
                    if (typeof chart.resize === 'function') chart.resize();
                    if (typeof chart.update === 'function') chart.update('none');
                    chart.options.animation = orig;
                } catch (error) {
                    console.error(`Chart resize error GPU ${gpuId}:`, error);
                }
            });
        }
    }
}

// Create or update GPU tab
function ensureGPUTab(gpuId, gpuInfo, shouldUpdateDOM = true) {
    if (!registeredGPUs.has(gpuId)) {
        // Add sidebar button
        const viewSelector = document.getElementById('view-selector');
        const btn = document.createElement('button');
        btn.className = 'sidebar-btn';
        btn.dataset.view = `gpu-${gpuId}`;
        // For cluster IDs like "gpu-server-2-0", show only the last segment
        const parts = String(gpuId).split('-');
        btn.textContent = parts.length > 1 ? parts[parts.length - 1] : gpuId;
        btn.title = `GPU ${gpuId}`;
        btn.onclick = () => switchToView(`gpu-${gpuId}`);
        viewSelector.appendChild(btn);

        // Create tab content
        const tabContent = document.createElement('div');
        tabContent.id = `tab-gpu-${gpuId}`;
        tabContent.className = 'tab-content';
        tabContent.innerHTML = `<div class="detailed-view"></div>`;
        document.getElementById('tab-overview').after(tabContent);

        registeredGPUs.add(gpuId);
    }

    // Update or create detailed GPU card
    const detailedContainer = document.querySelector(`#tab-gpu-${gpuId} .detailed-view`);
    const existingCard = document.getElementById(`gpu-${gpuId}`);

    if (!existingCard && detailedContainer) {
        detailedContainer.innerHTML = createGPUCard(gpuId, gpuInfo);
        if (!chartData[gpuId]) initGPUData(gpuId);
        initGPUCharts(gpuId);
    } else if (existingCard) {
        updateGPUDisplay(gpuId, gpuInfo, shouldUpdateDOM);
    }
}

// Remove GPU tab
function removeGPUTab(gpuId) {
    if (!registeredGPUs.has(gpuId)) return;

    if (currentTab === `gpu-${gpuId}`) {
        switchToView('overview');
    }

    const btn = document.querySelector(`.sidebar-btn[data-view="gpu-${gpuId}"]`);
    if (btn) btn.remove();

    const tabContent = document.getElementById(`tab-gpu-${gpuId}`);
    if (tabContent) tabContent.remove();

    if (charts[gpuId]) {
        Object.values(charts[gpuId]).forEach(chart => {
            if (chart && chart.destroy) chart.destroy();
        });
        delete charts[gpuId];
    }

    registeredGPUs.delete(gpuId);
}

// Auto-switch to single GPU view
function autoSwitchSingleGPU(gpuCount, gpuIds) {
    if (gpuCount === 1 && !hasAutoSwitched) {
        const singleGpuId = gpuIds[0];
        setTimeout(() => {
            switchToView(`gpu-${singleGpuId}`);
        }, 300);
        hasAutoSwitched = true;
    }
}

// ============================================
// Animated Number Transitions
// ============================================

// Check if reduced motion is preferred
function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Animation frame tracking for cleanup
const activeAnimations = new Map();

/**
 * Animate a number value smoothly from current to target
 * @param {HTMLElement} element - The element to update
 * @param {number} targetValue - The target numeric value
 * @param {number} duration - Animation duration in ms (default 300)
 * @param {string} suffix - Optional suffix to append (e.g., '%', '°', 'W')
 * @param {function} formatter - Optional formatter function
 */
function animateValue(element, targetValue, duration = 300, suffix = '', formatter = null) {
    if (!element) return;

    // Skip animation if reduced motion preferred
    if (prefersReducedMotion()) {
        const formatted = formatter ? formatter(targetValue) : targetValue;
        element.textContent = formatted + suffix;
        return;
    }

    // Cancel any existing animation on this element
    const animId = element.dataset.animId;
    if (animId && activeAnimations.has(animId)) {
        cancelAnimationFrame(activeAnimations.get(animId));
        activeAnimations.delete(animId);
    }

    // Parse current value
    const currentText = element.textContent.replace(/[^\d.-]/g, '');
    const currentValue = parseFloat(currentText) || 0;

    // Skip if values are essentially the same
    if (Math.abs(currentValue - targetValue) < 0.5) {
        const formatted = formatter ? formatter(targetValue) : targetValue;
        element.textContent = formatted + suffix;
        return;
    }

    const startTime = performance.now();
    const newAnimId = `anim-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    element.dataset.animId = newAnimId;

    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease-out cubic for smooth deceleration
        const eased = 1 - Math.pow(1 - progress, 3);

        // Calculate interpolated value
        const value = currentValue + (targetValue - currentValue) * eased;

        // Apply formatting
        const displayValue = formatter ? formatter(value) :
            (Number.isInteger(targetValue) ? Math.round(value) : value.toFixed(1));

        element.textContent = displayValue + suffix;

        if (progress < 1) {
            activeAnimations.set(newAnimId, requestAnimationFrame(tick));
        } else {
            activeAnimations.delete(newAnimId);
            delete element.dataset.animId;
        }
    }

    activeAnimations.set(newAnimId, requestAnimationFrame(tick));
}

/**
 * Animate multiple metrics at once
 * @param {Object} updates - Map of element IDs to {value, suffix, formatter}
 * @param {number} duration - Animation duration in ms
 */
function animateMetrics(updates, duration = 300) {
    Object.entries(updates).forEach(([id, config]) => {
        const element = document.getElementById(id);
        if (element) {
            animateValue(element, config.value, duration, config.suffix || '', config.formatter || null);
        }
    });
}

// Expose to global scope
window.switchToView = switchToView;
