/**
 * Chart configuration factory — GPU Studio
 * Theme-aware sparklines with gradient fills
 */

/**
 * Get chart colors from CSS custom properties
 * Reads current theme colors from the DOM
 * @returns {Object} Color palette for charts
 */
function getChartColors() {
    const style = getComputedStyle(document.documentElement);
    
    return {
        stroke: style.getPropertyValue('--spark-stroke').trim() || 'rgba(238, 240, 244, 0.6)',
        strokeLight: style.getPropertyValue('--spark-stroke-secondary').trim() || 'rgba(238, 240, 244, 0.35)',
        strokeDim: style.getPropertyValue('--spark-stroke-secondary').trim() || 'rgba(238, 240, 244, 0.2)',
        grid: style.getPropertyValue('--bar-track').trim() || 'rgba(255, 255, 255, 0.04)',
        tick: style.getPropertyValue('--text-tertiary').trim() || 'rgba(238, 240, 244, 0.4)',
        tooltipBg: style.getPropertyValue('--bg-surface').trim() || '#171b22',
        tooltipTitle: style.getPropertyValue('--text-primary').trim() || '#eef0f4',
        tooltipBody: style.getPropertyValue('--text-secondary').trim() || 'rgba(238, 240, 244, 0.7)',
        warning: style.getPropertyValue('--warning').trim() || '#f5a623',
        legendColor: style.getPropertyValue('--text-tertiary').trim() || 'rgba(255, 255, 255, 0.5)',
        crosshair: style.getPropertyValue('--chart-crosshair').trim() || 'rgba(130, 177, 255, 0.25)',
        sidebarStroke: style.getPropertyValue('--sidebar-chart-stroke').trim() || 'rgba(255, 255, 255, 0.5)',
    };
}

/**
 * Get metric identity RGB values from CSS custom properties
 * @returns {Object} RGB tuples for each metric type
 */
function getMetricColors() {
    const style = getComputedStyle(document.documentElement);

    return {
        utilization: style.getPropertyValue('--metric-util').trim() || '130, 177, 255',
        temperature: style.getPropertyValue('--metric-temp').trim() || '255, 183, 77',
        memory: style.getPropertyValue('--metric-mem').trim() || '100, 210, 255',
        power: style.getPropertyValue('--metric-power').trim() || '134, 239, 172',
        fanSpeed: style.getPropertyValue('--metric-fan').trim() || '186, 147, 216',
        clocks: style.getPropertyValue('--metric-clocks').trim() || '255, 213, 130',
        efficiency: style.getPropertyValue('--metric-efficiency').trim() || '168, 216, 185',
        pcie: style.getPropertyValue('--metric-pcie').trim() || '176, 190, 210',
        appclocks: style.getPropertyValue('--metric-clocks').trim() || '255, 213, 130',
        encoderDecoder: '0, 210, 190',
        systemCpu: style.getPropertyValue('--metric-util').trim() || '130, 177, 255',
        systemMemory: style.getPropertyValue('--metric-mem').trim() || '100, 210, 255',
        systemSwap: style.getPropertyValue('--metric-mem').trim() || '100, 210, 255',
        systemNetIo: style.getPropertyValue('--metric-pcie').trim() || '176, 190, 210',
        systemDiskIo: style.getPropertyValue('--metric-pcie').trim() || '176, 190, 210',
        systemLoadAvg: style.getPropertyValue('--metric-util').trim() || '130, 177, 255',
    };
}

/**
 * Create a gradient fill for chart datasets
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} height - Chart height for gradient calculation
 * @param {string} metricType - Type of metric (utilization, temperature, etc.)
 * @param {number} opacityTop - Opacity at top (default 0.15)
 * @param {number} opacityBottom - Opacity at bottom (default 0.0)
 * @returns {CanvasGradient} Gradient to use as backgroundColor
 */
function createMetricGradient(ctx, height, metricType, opacityTop = 0.15, opacityBottom = 0.0) {
    const colors = getMetricColors();
    const rgb = colors[metricType] || colors.utilization;

    const gradient = ctx.createLinearGradient(0, 0, 0, height || 100);
    gradient.addColorStop(0, `rgba(${rgb}, ${opacityTop})`);
    gradient.addColorStop(1, `rgba(${rgb}, ${opacityBottom})`);

    return gradient;
}

/**
 * Create a hover crosshair line for Chart.js charts
 * Custom plugin that draws a vertical line at the hovered point
 */
const crosshairPlugin = {
    id: 'crosshair',
    afterDraw: (chart) => {
        if (!chart.options.crosshair?.enabled) return;

        const { ctx, chartArea, scales } = chart;
        const active = chart.getActiveElements();

        if (!active.length) return;

        const point = active[0];
        const x = point.element.x;

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
        ctx.lineWidth = chart.options.crosshair.lineWidth || 1;
        ctx.strokeStyle = chart.options.crosshair.color || 'rgba(130, 177, 255, 0.3)';
        ctx.stroke();
        ctx.restore();
    }
};

// Legacy SPARK object for backwards compatibility (computed on first access)
const SPARK = {
    get stroke() { return getChartColors().stroke; },
    get strokeLight() { return getChartColors().strokeLight; },
    get strokeDim() { return getChartColors().strokeDim; },
    get grid() { return getChartColors().grid; },
    get tick() { return getChartColors().tick; },
    get tooltipBg() { return getChartColors().tooltipBg; },
    get warning() { return getChartColors().warning; },
};

// Sparkline warning thresholds — line turns orange above these values
const SPARK_THRESHOLDS = {
    utilization: 80,
    temperature: 75,
    memory: 85,
};

// Base chart options — minimal sparkline
function getBaseChartOptions() {
    const colors = getChartColors();
    
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        elements: {
            point: { radius: 0, hitRadius: 8 },
            line: { borderCapStyle: 'round', borderJoinStyle: 'round' }
        },
        layout: {
            padding: { left: 0, right: 0, top: 2, bottom: 0 }
        },
        scales: {
            x: {
                display: false
            },
            y: {
                min: 0,
                display: true,
                position: 'right',
                grid: {
                    color: colors.grid,
                    drawBorder: false,
                    lineWidth: 1
                },
                ticks: {
                    color: colors.tick,
                    font: { size: 10, family: "'SF Mono', 'Menlo', 'Consolas', monospace" },
                    padding: 8,
                    maxTicksLimit: 3
                },
                border: {
                    display: false
                }
            }
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: colors.tooltipBg,
                titleColor: colors.tooltipTitle,
                bodyColor: colors.tooltipBody,
                borderWidth: 0,
                cornerRadius: 4,
                displayColors: false,
                padding: 8,
                titleFont: { size: 11, weight: '600' },
                bodyFont: { size: 11 }
            }
        }
    };
}

// Metric identity RGB values for gradient fills (computed dynamically)
const METRIC_FILL_COLORS = {
    get utilization() { return getMetricColors().utilization; },
    get temperature() { return getMetricColors().temperature; },
    get memory() { return getMetricColors().memory; },
    get power() { return getMetricColors().power; },
    get fanSpeed() { return getMetricColors().fanSpeed; },
    get clocks() { return getMetricColors().clocks; },
    get efficiency() { return getMetricColors().efficiency; },
    get pcie() { return getMetricColors().pcie; },
    get appclocks() { return getMetricColors().appclocks; },
    get encoderDecoder() { return getMetricColors().encoderDecoder; },
    get systemCpu() { return getMetricColors().systemCpu; },
    get systemMemory() { return getMetricColors().systemMemory; },
    get systemSwap() { return getMetricColors().systemSwap; },
    get systemNetIo() { return getMetricColors().systemNetIo; },
    get systemDiskIo() { return getMetricColors().systemDiskIo; },
    get systemLoadAvg() { return getMetricColors().systemLoadAvg; },
};

// Single-line sparkline config
function createLineChartConfig(options) {
    const {
        label,
        yMax,
        yStepSize,
        yUnit,
        tooltipTitle,
        tooltipLabel,
        decimals = 1
    } = options;

    const config = {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderColor: SPARK.stroke,
                backgroundColor: 'transparent',
                borderWidth: 1.5,
                tension: 0.3,
                fill: true,
                pointRadius: 0,
                pointHitRadius: 8
            }]
        },
        options: getBaseChartOptions()
    };

    if (yMax !== undefined) config.options.scales.y.max = yMax;
    if (options.ySuggestedMax) config.options.scales.y.suggestedMax = options.ySuggestedMax;
    if (yStepSize) config.options.scales.y.ticks.stepSize = yStepSize;
    if (yUnit) {
        config.options.scales.y.ticks.callback = function (value) {
            return value + yUnit;
        };
    }

    config.options.plugins.tooltip.callbacks = {
        title: function () { return tooltipTitle; },
        label: function (context) {
            const displayLabel = tooltipLabel || context.dataset.label || '';
            const value = context.parsed.y;
            return `${displayLabel}: ${value.toFixed(decimals)}${yUnit || ''}`;
        }
    };

    return config;
}

// Multi-line sparkline config
function createMultiLineChartConfig(options) {
    const {
        datasets,
        yUnit,
        tooltipTitle,
        showLegend = false,
        ySuggestedMax,
        decimals = 0
    } = options;

    const colors = getChartColors();
    
    // Grayscale tones for multi-line differentiation
    const grayTones = [colors.stroke, colors.strokeLight, colors.strokeDim, colors.strokeDim];

    const config = {
        type: 'line',
        data: {
            labels: [],
            datasets: datasets.map((ds, i) => ({
                label: ds.label,
                data: [],
                borderColor: grayTones[i % grayTones.length],
                backgroundColor: 'transparent',
                borderWidth: ds.width || 1.5,
                tension: 0.3,
                fill: false,
                pointRadius: 0,
                pointHitRadius: 8
            }))
        },
        options: getBaseChartOptions()
    };

    if (ySuggestedMax) config.options.scales.y.suggestedMax = ySuggestedMax;
    if (yUnit) {
        config.options.scales.y.ticks.callback = function (value) {
            return value.toFixed(decimals) + yUnit;
        };
    }

    if (showLegend) {
        config.options.plugins.legend.display = true;
        config.options.plugins.legend.position = 'top';
        config.options.plugins.legend.align = 'end';
        config.options.plugins.legend.labels = {
            color: colors.legendColor,
            font: { size: 10 },
            boxWidth: 8,
            boxHeight: 2,
            padding: 8,
            usePointStyle: false
        };
    }

    config.options.plugins.tooltip.callbacks = {
        title: function () { return tooltipTitle; },
        label: function (context) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${value.toFixed(decimals)}${yUnit || ''}`;
        }
    };

    return config;
}

// ============================================
// Chart Configs — all grayscale sparklines
// ============================================

const chartConfigs = {
    utilization: createLineChartConfig({
        label: 'Utilization',
        yMax: 100,
        yStepSize: 50,
        yUnit: '%',
        tooltipTitle: 'GPU Utilization',
        tooltipLabel: 'Util'
    }),

    temperature: createLineChartConfig({
        label: 'Temperature',
        ySuggestedMax: 90,
        yStepSize: 30,
        yUnit: '°C',
        tooltipTitle: 'Temperature',
        tooltipLabel: 'Temp'
    }),

    memory: createLineChartConfig({
        label: 'Memory',
        yMax: 100,
        yStepSize: 50,
        yUnit: '%',
        tooltipTitle: 'VRAM Usage',
        tooltipLabel: 'Mem'
    }),

    power: createLineChartConfig({
        label: 'Power',
        ySuggestedMax: 200,
        yStepSize: 100,
        yUnit: 'W',
        tooltipTitle: 'Power Draw',
        tooltipLabel: 'Power'
    }),

    fanSpeed: createLineChartConfig({
        label: 'Fan',
        yMax: 100,
        yStepSize: 50,
        yUnit: '%',
        tooltipTitle: 'Fan Speed',
        tooltipLabel: 'Fan'
    }),

    clocks: createMultiLineChartConfig({
        datasets: [
            { label: 'Graphics' },
            { label: 'SM' },
            { label: 'Memory' }
        ],
        yUnit: ' MHz',
        tooltipTitle: 'Clock Speeds',
        showLegend: true,
        decimals: 0
    }),

    efficiency: createLineChartConfig({
        label: 'Efficiency',
        yUnit: ' %/W',
        tooltipTitle: 'Power Efficiency',
        tooltipLabel: 'Eff',
        decimals: 2
    }),

    pcie: createMultiLineChartConfig({
        datasets: [
            { label: 'RX' },
            { label: 'TX' }
        ],
        yUnit: ' KB/s',
        tooltipTitle: 'PCIe Throughput',
        showLegend: true,
        decimals: 0
    }),

    appclocks: createMultiLineChartConfig({
        datasets: [
            { label: 'Graphics' },
            { label: 'Memory' },
            { label: 'SM' },
            { label: 'Video' }
        ],
        yUnit: ' MHz',
        tooltipTitle: 'App Clocks',
        showLegend: true,
        decimals: 0
    }),

    encoderDecoder: createMultiLineChartConfig({
        datasets: [
            { label: 'Encoder' },
            { label: 'Decoder' }
        ],
        yUnit: '%',
        tooltipTitle: 'Encoder / Decoder Utilization',
        showLegend: true,
        ySuggestedMax: 100,
        decimals: 0
    }),

    // ============================================
    // System Charts
    // ============================================

    systemCpu: createLineChartConfig({
        label: 'CPU',
        yMax: 100,
        yStepSize: 50,
        yUnit: '%',
        tooltipTitle: 'CPU Usage',
        tooltipLabel: 'CPU'
    }),

    systemMemory: createLineChartConfig({
        label: 'RAM',
        yMax: 100,
        yStepSize: 50,
        yUnit: '%',
        tooltipTitle: 'RAM Usage',
        tooltipLabel: 'RAM'
    }),

    systemSwap: createLineChartConfig({
        label: 'Swap',
        yMax: 100,
        yStepSize: 50,
        yUnit: '%',
        tooltipTitle: 'Swap Usage',
        tooltipLabel: 'Swap'
    }),

    systemNetIo: createMultiLineChartConfig({
        datasets: [
            { label: 'RX' },
            { label: 'TX' }
        ],
        yUnit: ' KB/s',
        tooltipTitle: 'Network I/O',
        showLegend: true,
        decimals: 1
    }),

    systemDiskIo: createMultiLineChartConfig({
        datasets: [
            { label: 'Read' },
            { label: 'Write' }
        ],
        yUnit: ' KB/s',
        tooltipTitle: 'Disk I/O',
        showLegend: true,
        decimals: 1
    }),

    systemLoadAvg: createMultiLineChartConfig({
        datasets: [
            { label: '1m' },
            { label: '5m' },
            { label: '15m' }
        ],
        yUnit: '',
        tooltipTitle: 'Load Average',
        showLegend: true,
        ySuggestedMax: 4,
        decimals: 2
    })
};
