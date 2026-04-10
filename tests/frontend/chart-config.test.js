/**
 * Tests for static/js/chart-config.js
 */

import { describe, it, expect } from 'vitest';

// Globals loaded by setup.js: SPARK, SPARK_THRESHOLDS, chartConfigs, getBaseChartOptions,
// createLineChartConfig, createMultiLineChartConfig

describe('SPARK constants', () => {
    it('defines stroke color', () => {
        expect(SPARK.stroke).toBeDefined();
        expect(typeof SPARK.stroke).toBe('string');
    });

    it('defines warning color', () => {
        expect(SPARK.warning).toBe('#f5a623');
    });

    it('defines tooltip background', () => {
        expect(SPARK.tooltipBg).toBe('#171b22');
    });
});

describe('SPARK_THRESHOLDS', () => {
    it('defines utilization threshold', () => {
        expect(SPARK_THRESHOLDS.utilization).toBe(80);
    });

    it('defines temperature threshold', () => {
        expect(SPARK_THRESHOLDS.temperature).toBe(75);
    });

    it('defines memory threshold', () => {
        expect(SPARK_THRESHOLDS.memory).toBe(85);
    });
});

describe('getBaseChartOptions', () => {
    it('returns responsive options', () => {
        const opts = getBaseChartOptions();
        expect(opts.responsive).toBe(true);
        expect(opts.animation).toBe(false);
    });

    it('disables x-axis display', () => {
        const opts = getBaseChartOptions();
        expect(opts.scales.x.display).toBe(false);
    });

    it('sets point radius to zero', () => {
        const opts = getBaseChartOptions();
        expect(opts.elements.point.radius).toBe(0);
    });
});

describe('chartConfigs', () => {
    const expectedTypes = [
        'utilization', 'temperature', 'memory', 'power',
        'fanSpeed', 'clocks', 'efficiency', 'pcie',
        'appclocks', 'encoderDecoder',
        'systemCpu', 'systemMemory', 'systemSwap',
        'systemNetIo', 'systemDiskIo', 'systemLoadAvg'
    ];

    for (const type of expectedTypes) {
        it(`defines config for ${type}`, () => {
            expect(chartConfigs[type]).toBeDefined();
            expect(chartConfigs[type].type).toBe('line');
            expect(chartConfigs[type].data).toBeDefined();
            expect(chartConfigs[type].data.datasets.length).toBeGreaterThan(0);
        });
    }

    it('utilization has yMax of 100', () => {
        const yScale = chartConfigs.utilization.options.scales.y;
        expect(yScale.max).toBe(100);
    });
});
