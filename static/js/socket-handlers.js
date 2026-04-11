/**
 * WebSocket event handlers
 */

// WebSocket connection with auto-reconnect
let socket = null;
let reconnectInterval = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY = 2000; // Start with 2 seconds

function createWebSocketConnection() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(protocol + '//' + window.location.host + '/socket.io/');
    return ws;
}

function connectWebSocket() {
    if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) {
        return; // Already connected or connecting
    }

    socket = createWebSocketConnection();
    setupWebSocketHandlers();
}

function setupWebSocketHandlers() {
    if (!socket) return;

    socket.onopen = handleSocketOpen;
    socket.onmessage = handleSocketMessage;
    socket.onclose = handleSocketClose;
    socket.onerror = handleSocketError;
}

function handleSocketOpen() {
    console.log('Connected to server');
    reconnectAttempts = 0;
    clearInterval(reconnectInterval);
    reconnectInterval = null;

    const statusEl = document.getElementById('connection-status');
    if (statusEl) {
        statusEl.textContent = 'Connected';
        statusEl.style.color = '';
        const dot = document.getElementById('status-dot');
        if (dot) dot.classList.add('connected');
    }

    // Show skeleton cards after WebSocket connects (before GPU data arrives)
    showSkeletonCards();
}

function handleSocketClose() {
    console.log('Disconnected from server');

    const statusEl = document.getElementById('connection-status');
    if (statusEl) {
        statusEl.textContent = 'Reconnecting...';
        statusEl.style.color = '#f5a623';
        const dot = document.getElementById('status-dot');
        if (dot) dot.classList.remove('connected');
    }

    // Attempt to reconnect
    attemptReconnect();
}

function handleSocketError(error) {
    console.error('WebSocket error:', error);
    const statusEl = document.getElementById('connection-status');
    if (statusEl) {
        statusEl.textContent = 'Error';
        statusEl.style.color = '#f44';
    }
}

function attemptReconnect() {
    if (reconnectInterval) return; // Already trying to reconnect

    reconnectInterval = setInterval(() => {
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.textContent = 'Disconnected';
                statusEl.style.color = '#f44';
                statusEl.style.cursor = 'pointer';
                statusEl.onclick = () => location.reload();
            }
            return;
        }

        reconnectAttempts++;
        console.log(`Reconnection attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);
        connectWebSocket();
    }, RECONNECT_DELAY);
}

// Initialize connection
connectWebSocket();

// ============================================
// Skeleton Loading State Management
// ============================================

/**
 * Show skeleton cards after WebSocket connection
 * Replaces "Waiting for GPU data…" with skeleton placeholders
 */
function showSkeletonCards() {
    const overviewContainer = document.getElementById('overview-container');
    const processesContainer = document.getElementById('processes-container');

    // Skip if containers don't exist (test environment)
    if (!overviewContainer) return;

    // Only show skeletons if still in loading state
    if (!overviewContainer.querySelector('.loading')) return;

    // Replace overview loading with skeleton cards
    overviewContainer.innerHTML = createSkeletonOverview();

    // Replace processes loading with skeleton rows
    if (processesContainer) {
        processesContainer.innerHTML = createSkeletonProcesses();
    }
}

/**
 * Create skeleton overview cards (2 placeholder GPUs)
 * @returns {string} HTML string with skeleton cards
 */
function createSkeletonOverview() {
    return `
        <div class="skeleton-aggregate">
            <div class="skeleton-aggregate-row">
                <div class="skeleton skeleton-aggregate-value"></div>
                <div class="skeleton skeleton-aggregate-bar"></div>
            </div>
        </div>
        <div class="skeleton-overview-card">
            <div class="skeleton-gpu-name">
                <div class="skeleton skeleton-gpu-name-title"></div>
                <div class="skeleton skeleton-gpu-name-subtitle"></div>
            </div>
            <div class="skeleton-metrics">
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
            </div>
            <div class="skeleton skeleton-sparkline"></div>
        </div>
        <div class="skeleton-overview-card">
            <div class="skeleton-gpu-name">
                <div class="skeleton skeleton-gpu-name-title"></div>
                <div class="skeleton skeleton-gpu-name-subtitle"></div>
            </div>
            <div class="skeleton-metrics">
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
                <div class="skeleton-metric">
                    <div class="skeleton skeleton-metric-value"></div>
                    <div class="skeleton skeleton-metric-label"></div>
                </div>
            </div>
            <div class="skeleton skeleton-sparkline"></div>
        </div>
    `;
}

/**
 * Create skeleton process rows
 * @returns {string} HTML string with skeleton process table
 */
function createSkeletonProcesses() {
    const rows = [];
    for (let i = 0; i < 4; i++) {
        rows.push(`
            <div class="skeleton-process-row">
                <div class="skeleton skeleton-process-name"></div>
                <div class="skeleton skeleton-process-pid"></div>
                <div class="skeleton skeleton-process-memory"></div>
            </div>
        `);
    }
    return `
        <div class="skeleton-processes">
            <div class="skeleton-process-header">
                <div class="skeleton skeleton-process-name"></div>
                <div class="skeleton skeleton-process-pid"></div>
                <div class="skeleton skeleton-process-memory"></div>
            </div>
            ${rows.join('')}
        </div>
    `;
}

/**
 * Hide skeleton cards when real data arrives
 * Called from handleSocketMessage when first GPU data is received
 */
function hideSkeletonCards() {
    const overviewContainer = document.getElementById('overview-container');
    const skeletonCards = overviewContainer.querySelectorAll('.skeleton-overview-card, .skeleton-aggregate');
    skeletonCards.forEach(card => card.remove());
}

// Performance: Scroll detection to pause DOM updates during scroll
let isScrolling = false;
let scrollTimeout;
const SCROLL_PAUSE_DURATION = 100; // ms to wait after scroll stops before resuming updates

/**
 * Setup scroll event listeners to detect when user is scrolling
 * Uses passive listeners for better performance
 */
function setupScrollDetection() {
    const handleScroll = () => {
        isScrolling = true;
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            isScrolling = false;
        }, SCROLL_PAUSE_DURATION);
    };

    // Wait for DOM to be ready
    setTimeout(() => {
        // Listen to window scroll (primary scroll container)
        window.addEventListener('scroll', handleScroll, { passive: true });

        // Also listen to .main as fallback
        const main = document.querySelector('.main');
        if (main) {
            main.addEventListener('scroll', handleScroll, { passive: true });
        }
    }, 500);
}

// Initialize scroll detection
setupScrollDetection();

// Track whether the aggregate summary card has been injected
let aggregateCardInjected = false;

// Performance: Batched rendering system using requestAnimationFrame
// Batches all DOM updates into a single frame to minimize reflows/repaints
let pendingUpdates = new Map(); // Queue of pending GPU/system updates
let rafScheduled = false; // Flag to prevent duplicate RAF scheduling

// Performance: Throttle text updates (less critical than charts)
const lastDOMUpdate = {}; // Track last update time per GPU
const DOM_UPDATE_INTERVAL = 1000; // Text/card updates every 1s, charts update every frame

// Handle incoming GPU data
function handleSocketMessage(event) {
    const data = JSON.parse(event.data);
    // Hub mode: different data structure with nodes
    if (data.mode === 'hub') {
        handleClusterData(data);
        return;
    }

    const overviewContainer = document.getElementById('overview-container');

    // Clear loading state (both pulsing dot and skeleton cards)
    if (overviewContainer.querySelector('.loading') || overviewContainer.querySelector('.skeleton-overview-card')) {
        hideSkeletonCards();
        overviewContainer.innerHTML = '';
        aggregateCardInjected = false;
    }

    const gpuCount = Object.keys(data.gpus).length;
    const now = Date.now();

    // Performance: Skip ALL DOM updates during active scrolling
    if (isScrolling) {
        // Still update chart data arrays (lightweight) to maintain continuity
        // This ensures no data gaps when scroll ends
        Object.keys(data.gpus).forEach(gpuId => {
            const gpuInfo = data.gpus[gpuId];
            if (!chartData[gpuId]) {
                initGPUData(gpuId, {
                    utilization: gpuInfo.utilization,
                    temperature: gpuInfo.temperature,
                    memory: (gpuInfo.memory_used / gpuInfo.memory_total) * 100,
                    power: gpuInfo.power_draw,
                    fanSpeed: gpuInfo.fan_speed,
                    clockGraphics: gpuInfo.clock_graphics,
                    clockSm: gpuInfo.clock_sm,
                    clockMemory: gpuInfo.clock_memory,
                    powerLimit: gpuInfo.power_limit
                });
            }
            updateAllChartDataOnly(gpuId, gpuInfo);
            // Also update system chart data during scroll
            if (data.system) {
                updateGPUSystemCharts(gpuId, data.system, '_local', false);
            }
        });
        return; // Exit early - zero DOM work during scroll = smooth 60 FPS
    }

    // Process each GPU - queue updates for batched rendering
    Object.keys(data.gpus).forEach(gpuId => {
        const gpuInfo = data.gpus[gpuId];

        // Initialize chart data structures if first time seeing this GPU
        if (!chartData[gpuId]) {
            initGPUData(gpuId, {
                utilization: gpuInfo.utilization,
                temperature: gpuInfo.temperature,
                memory: (gpuInfo.memory_used / gpuInfo.memory_total) * 100,
                power: gpuInfo.power_draw,
                fanSpeed: gpuInfo.fan_speed,
                clockGraphics: gpuInfo.clock_graphics,
                clockSm: gpuInfo.clock_sm,
                clockMemory: gpuInfo.clock_memory,
                powerLimit: gpuInfo.power_limit
            });
        }

        // Determine if text/card DOM should update (throttled) or just charts (every frame)
        const shouldUpdateDOM = !lastDOMUpdate[gpuId] || (now - lastDOMUpdate[gpuId]) >= DOM_UPDATE_INTERVAL;

        // Queue this GPU's update instead of executing immediately
        pendingUpdates.set(gpuId, {
            gpuInfo,
            systemInfo: data.system,
            sourceKey: '_local',
            shouldUpdateDOM,
            now
        });

        // Handle initial card creation (can't be batched since we need the DOM element)
        const existingOverview = overviewContainer.querySelector(`[data-gpu-id="${gpuId}"]`);
        if (!existingOverview) {
            if (gpuCount >= 2) {
                // Compact layout for multi-GPU servers
                let nodeGrid = overviewContainer.querySelector('.node-grid');
                if (!nodeGrid) {
                    const hostname = data.node_name || 'GPU Server';
                    overviewContainer.insertAdjacentHTML('beforeend', `
                        <div class="node-group" data-node="_local">
                            <div class="node-label">${hostname}</div>
                            <div class="node-grid"></div>
                        </div>
                    `);
                    nodeGrid = overviewContainer.querySelector('.node-grid');
                }
                nodeGrid.insertAdjacentHTML('beforeend', createCompactOverviewCard(gpuId, gpuInfo));
            } else {
                overviewContainer.insertAdjacentHTML('beforeend', createEnhancedOverviewCard(gpuId, gpuInfo));
                // Auto-expand processes for single GPU
                setTimeout(() => {
                    const content = document.getElementById('processes-content');
                    const header = document.querySelector('.processes-header');
                    const icon = document.querySelector('.toggle-icon');
                    if (content && !content.classList.contains('expanded')) {
                        content.classList.add('expanded');
                        if (header) header.classList.add('expanded');
                        if (icon) icon.classList.add('expanded');
                    }
                }, 100);
            }
            initOverviewMiniChart(gpuId, gpuInfo.utilization);
            lastDOMUpdate[gpuId] = now;
        }
    });

    // Aggregate summary card (2+ GPUs)
    if (gpuCount >= 2) {
        if (!aggregateCardInjected) {
            overviewContainer.insertAdjacentHTML('afterbegin', createAggregateCard());
            aggregateCardInjected = true;
            initAggregateChart();
        }
        pendingUpdates.set('_aggregate', { gpus: data.gpus });
    } else if (aggregateCardInjected) {
        const aggCard = document.getElementById('aggregate-card');
        if (aggCard) aggCard.remove();
        destroyAggregateChart();
        aggregateCardInjected = false;
    }

    // Queue system updates (processes/CPU/RAM) for batching
    if (!lastDOMUpdate.system || (now - lastDOMUpdate.system) >= DOM_UPDATE_INTERVAL) {
        pendingUpdates.set('_system', {
            processes: data.processes,
            system: data.system,
            now
        });
    }

    // Schedule single batched render (if not already scheduled)
    // This ensures all updates happen in ONE animation frame
    if (!rafScheduled && pendingUpdates.size > 0) {
        rafScheduled = true;
        requestAnimationFrame(processBatchedUpdates);
    }

    // Auto-switch to single GPU view if only 1 GPU detected (first time only)
    autoSwitchSingleGPU(gpuCount, Object.keys(data.gpus));
}

/**
 * Process all batched updates in a single animation frame
 * Called by requestAnimationFrame at optimal timing (~60 FPS)
 * 
 * Performance benefit: All DOM updates execute in ONE layout/paint cycle
 * instead of multiple cycles, eliminating layout thrashing
 */
function processBatchedUpdates() {
    rafScheduled = false;

    // Execute all queued updates in a single batch
    pendingUpdates.forEach((update, gpuId) => {
        if (gpuId === '_aggregate') {
            updateAggregateStats(update.gpus);
            return;
        } else if (gpuId === '_system') {
            // System updates (CPU, RAM, processes)
            updateProcesses(update.processes);
            updateSystemInfo(update.system);
            lastDOMUpdate.system = update.now;
        } else {
            // GPU updates
            const { gpuInfo, systemInfo, sourceKey, shouldUpdateDOM, now } = update;

            // Update overview card (always for charts, conditionally for text)
            updateOverviewCard(gpuId, gpuInfo, shouldUpdateDOM);
            if (shouldUpdateDOM) {
                lastDOMUpdate[gpuId] = now;
            }

            // Performance: Only update detail view if tab is visible
            // Invisible tabs = zero wasted processing
            const isDetailTabVisible = currentTab === `gpu-${gpuId}`;
            if (isDetailTabVisible || !registeredGPUs.has(gpuId)) {
                ensureGPUTab(gpuId, gpuInfo, shouldUpdateDOM && isDetailTabVisible);
            }

            // Update per-GPU system charts
            if (systemInfo) {
                updateGPUSystemCharts(gpuId, systemInfo, sourceKey || '_local', shouldUpdateDOM && isDetailTabVisible);
            }
        }
    });

    // Clear queue for next batch
    pendingUpdates.clear();
}

/**
 * Update chart data arrays without triggering any rendering (used during scroll)
 * 
 * This maintains data continuity during scroll by collecting metrics
 * but skips expensive DOM/canvas updates for smooth 60 FPS scrolling
 * 
 * @param {string} gpuId - GPU identifier
 * @param {object} gpuInfo - GPU metrics data
 */
function updateAllChartDataOnly(gpuId, gpuInfo) {
    if (!chartData[gpuId]) return;

    const timestamp = new Date().toLocaleTimeString();
    const memory_used = gpuInfo.memory_used || 0;
    const memory_total = gpuInfo.memory_total || 1;
    const memPercent = (memory_used / memory_total) * 100;
    const power_draw = gpuInfo.power_draw || 0;

    // Prepare all metric updates
    const metrics = {
        utilization: gpuInfo.utilization || 0,
        temperature: gpuInfo.temperature || 0,
        memory: memPercent,
        power: power_draw,
        fanSpeed: gpuInfo.fan_speed || 0,
        efficiency: power_draw > 0 ? (gpuInfo.utilization || 0) / power_draw : 0
    };

    // Update single-line charts
    Object.entries(metrics).forEach(([chartType, value]) => {
        const data = chartData[gpuId][chartType];
        if (!data?.labels || !data?.data) return;

        data.labels.push(timestamp);
        data.data.push(Number(value) || 0);

        // Add threshold lines for specific charts
        if (chartType === 'utilization' && data.thresholdData) {
            data.thresholdData.push(80);
        } else if (chartType === 'temperature') {
            if (data.warningData) data.warningData.push(75);
            if (data.dangerData) data.dangerData.push(85);
        } else if (chartType === 'memory' && data.thresholdData) {
            data.thresholdData.push(90);
        }

        // Maintain rolling window (120 points = 60s at 0.5s interval)
        if (data.labels.length > 120) {
            data.labels.shift();
            data.data.shift();
            if (data.thresholdData) data.thresholdData.shift();
            if (data.warningData) data.warningData.shift();
            if (data.dangerData) data.dangerData.shift();
        }
    });

    // Update multi-line charts (clocks)
    const clocksData = chartData[gpuId].clocks;
    if (clocksData?.labels) {
        clocksData.labels.push(timestamp);
        clocksData.graphicsData.push(gpuInfo.clock_graphics || 0);
        clocksData.smData.push(gpuInfo.clock_sm || 0);
        clocksData.memoryData.push(gpuInfo.clock_memory || 0);

        if (clocksData.labels.length > 120) {
            clocksData.labels.shift();
            clocksData.graphicsData.shift();
            clocksData.smData.shift();
            clocksData.memoryData.shift();
        }
    }
}

// Handle page visibility changes (phone lock/unlock, tab switch)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Page became visible (phone unlocked or tab switched back)
        console.log('Page visible - checking connection');
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            // Connection is closed, reconnect immediately
            reconnectAttempts = 0;
            clearInterval(reconnectInterval);
            reconnectInterval = null;
            connectWebSocket();
        }
    }
});

// Also handle page focus (additional safety)
window.addEventListener('focus', () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.log('Window focused - checking connection');
        reconnectAttempts = 0;
        clearInterval(reconnectInterval);
        reconnectInterval = null;
        connectWebSocket();
    }
});

/**
 * Handle cluster/hub mode data
 * Data structure: { mode: 'hub', nodes: {...}, cluster_stats: {...} }
 */
function handleClusterData(data) {
    const overviewContainer = document.getElementById('overview-container');
    const now = Date.now();

    // Clear loading state (both pulsing dot and skeleton cards)
    if (overviewContainer.querySelector('.loading') || overviewContainer.querySelector('.skeleton-overview-card')) {
        hideSkeletonCards();
        overviewContainer.innerHTML = '';
        aggregateCardInjected = false;
    }

    // Skip DOM updates during scrolling
    if (isScrolling) {
        // Still update chart data for continuity
        Object.entries(data.nodes).forEach(([nodeName, nodeData]) => {
            if (nodeData.status === 'online') {
                Object.entries(nodeData.gpus).forEach(([gpuId, gpuInfo]) => {
                    const fullGpuId = `${nodeName}-${gpuId}`;
                    if (!chartData[fullGpuId]) {
                        initGPUData(fullGpuId, {
                            utilization: gpuInfo.utilization,
                            temperature: gpuInfo.temperature,
                            memory: (gpuInfo.memory_used / gpuInfo.memory_total) * 100,
                            power: gpuInfo.power_draw,
                            fanSpeed: gpuInfo.fan_speed,
                            clockGraphics: gpuInfo.clock_graphics,
                            clockSm: gpuInfo.clock_sm,
                            clockMemory: gpuInfo.clock_memory,
                            powerLimit: gpuInfo.power_limit
                        });
                    }
                    updateAllChartDataOnly(fullGpuId, gpuInfo);
                    if (nodeData.system) {
                        updateGPUSystemCharts(fullGpuId, nodeData.system, nodeName, false);
                    }
                });
            }
        });
        return;
    }

    // Render GPUs grouped by node (minimal grouping)
    Object.entries(data.nodes).forEach(([nodeName, nodeData]) => {
        // Get or create node group container
        let nodeGroup = overviewContainer.querySelector(`[data-node="${nodeName}"]`);
        if (!nodeGroup) {
            overviewContainer.insertAdjacentHTML('beforeend', `
                <div class="node-group" data-node="${nodeName}">
                    <div class="node-label">${nodeName}</div>
                    <div class="node-grid"></div>
                </div>
            `);
            nodeGroup = overviewContainer.querySelector(`[data-node="${nodeName}"]`);
        }

        const nodeGrid = nodeGroup.querySelector('.node-grid');

        if (nodeData.status === 'online') {
            // Node is online - process its GPUs normally
            Object.entries(nodeData.gpus).forEach(([gpuId, gpuInfo]) => {
                const fullGpuId = `${nodeName}-${gpuId}`;

                // Initialize chart data with current values
                if (!chartData[fullGpuId]) {
                    initGPUData(fullGpuId, {
                        utilization: gpuInfo.utilization,
                        temperature: gpuInfo.temperature,
                        memory: (gpuInfo.memory_used / gpuInfo.memory_total) * 100,
                        power: gpuInfo.power_draw,
                        fanSpeed: gpuInfo.fan_speed,
                        clockGraphics: gpuInfo.clock_graphics,
                        clockSm: gpuInfo.clock_sm,
                        clockMemory: gpuInfo.clock_memory,
                        powerLimit: gpuInfo.power_limit
                    });
                }

                // Queue update
                const shouldUpdateDOM = !lastDOMUpdate[fullGpuId] || (now - lastDOMUpdate[fullGpuId]) >= DOM_UPDATE_INTERVAL;
                pendingUpdates.set(fullGpuId, {
                    gpuInfo,
                    systemInfo: nodeData.system || {},
                    sourceKey: nodeName,
                    shouldUpdateDOM,
                    now,
                    nodeName
                });

                // Create card if doesn't exist
                const existingCard = nodeGrid.querySelector(`[data-gpu-id="${fullGpuId}"]`);
                if (!existingCard) {
                    nodeGrid.insertAdjacentHTML('beforeend', createClusterGPUCard(nodeName, gpuId, gpuInfo));
                    initOverviewMiniChart(fullGpuId, gpuInfo.utilization);
                    lastDOMUpdate[fullGpuId] = now;
                }
            });
        } else {
            // Node is offline - remove entire node group
            const existingCards = nodeGrid.querySelectorAll('[data-gpu-id]');
            existingCards.forEach(card => {
                const gpuId = card.getAttribute('data-gpu-id');
                // Clean up chart data
                if (chartData[gpuId]) {
                    delete chartData[gpuId];
                }
                if (lastDOMUpdate[gpuId]) {
                    delete lastDOMUpdate[gpuId];
                }
                // Remove the GPU tab
                removeGPUTab(gpuId);
            });

            // Remove the entire node group from the UI
            nodeGroup.remove();
        }
    });

    // Aggregate summary card (2+ GPUs across cluster)
    const clusterGpusFlat = {};
    Object.entries(data.nodes).forEach(([nodeName, nodeData]) => {
        if (nodeData.status === 'online') {
            Object.entries(nodeData.gpus).forEach(([gpuId, gpuInfo]) => {
                clusterGpusFlat[`${nodeName}-${gpuId}`] = gpuInfo;
            });
        }
    });
    const clusterGpuCount = Object.keys(clusterGpusFlat).length;
    if (clusterGpuCount >= 2) {
        if (!aggregateCardInjected) {
            overviewContainer.insertAdjacentHTML('afterbegin', createAggregateCard());
            aggregateCardInjected = true;
            initAggregateChart();
        }
        pendingUpdates.set('_aggregate', { gpus: clusterGpusFlat });
    } else if (aggregateCardInjected) {
        const aggCard = document.getElementById('aggregate-card');
        if (aggCard) aggCard.remove();
        destroyAggregateChart();
        aggregateCardInjected = false;
    }

    // Update processes and system info (use first online node)
    const firstOnlineNode = Object.values(data.nodes).find(n => n.status === 'online');
    if (firstOnlineNode) {
        if (!lastDOMUpdate.system || (now - lastDOMUpdate.system) >= DOM_UPDATE_INTERVAL) {
            pendingUpdates.set('_system', {
                processes: firstOnlineNode.processes || [],
                system: firstOnlineNode.system || {},
                now
            });
        }
    }

    // Schedule batched render
    if (!rafScheduled && pendingUpdates.size > 0) {
        rafScheduled = true;
        requestAnimationFrame(processBatchedUpdates);
    }
}

/**
 * Create GPU card for cluster view (includes node name)
 */
function createClusterGPUCard(nodeName, gpuId, gpuInfo) {
    const fullGpuId = `${nodeName}-${gpuId}`;
    const memory_used = getMetricValue(gpuInfo, 'memory_used', 0);
    const memory_total = getMetricValue(gpuInfo, 'memory_total', 1);
    const memPercent = (memory_used / memory_total) * 100;
    const temperature = getMetricValue(gpuInfo, 'temperature', 0);
    const tempStatus = getTempStatus(temperature);
    const gpuName = getMetricValue(gpuInfo, 'name', 'Unknown GPU');

    return `
        <div class="overview-gpu-card" data-gpu-id="${fullGpuId}" data-temp-status="${tempStatus}"
            tabindex="0" role="button" aria-label="View details for GPU ${gpuId} on ${nodeName}: ${gpuName}"
            onclick="switchToView('gpu-${fullGpuId}')"
            onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();switchToView('gpu-${fullGpuId}')}">
            <div class="overview-sparkline-band">
                <canvas id="overview-chart-${fullGpuId}" aria-hidden="true"></canvas>
            </div>
            <div class="overview-gpu-content">
                <div class="overview-gpu-name">
                    <h2>GPU ${gpuId}</h2>
                    <p>${gpuName}</p>
                </div>
                <div class="overview-metrics">
                    <div class="overview-metric">
                        <div class="overview-metric-value" id="overview-util-${fullGpuId}">${getMetricValue(gpuInfo, 'utilization', 0)}%</div>
                        <div class="overview-metric-label">
                            <svg class="metric-icon" aria-hidden="true"><use href="#icon-speedometer"/></svg>
                            UTIL
                        </div>
                    </div>
                    <div class="overview-metric">
                        <div class="overview-metric-value" id="overview-temp-${fullGpuId}">${temperature}°</div>
                        <div class="overview-metric-label">
                            <svg class="metric-icon" aria-hidden="true"><use href="#icon-thermometer"/></svg>
                            TEMP
                        </div>
                    </div>
                    <div class="overview-metric">
                        <div class="overview-metric-value" id="overview-mem-${fullGpuId}">${Math.round(memPercent)}%</div>
                        <div class="overview-metric-label">
                            <svg class="metric-icon" aria-hidden="true"><use href="#icon-memory"/></svg>
                            MEM
                        </div>
                    </div>
                    <div class="overview-metric">
                        <div class="overview-metric-value" id="overview-power-${fullGpuId}">${getMetricValue(gpuInfo, 'power_draw', 0).toFixed(0)}W</div>
                        <div class="overview-metric-label">
                            <svg class="metric-icon" aria-hidden="true"><use href="#icon-bolt"/></svg>
                            POWER
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
