"""Tests for core/metrics/amd_collector.py"""

import pytest
from unittest.mock import patch, MagicMock

from core.metrics.amd_collector import AmdMetricsCollector


def _make_mock_amdsmi():
    """Create a mock amdsmi module with required constants."""
    mock = MagicMock()
    mock.AmdSmiMemoryType.VRAM = 0
    mock.AmdSmiTemperatureType.EDGE = 0
    mock.AmdSmiTemperatureType.HOTSPOT = 1
    mock.AmdSmiTemperatureType.VRAM = 2
    mock.AmdSmiTemperatureMetric.CURRENT = 0
    mock.AmdSmiClkType.GFX = 0
    mock.AmdSmiClkType.MEM = 1
    mock.AmdSmiClkType.SOC = 2
    mock.AmdSmiClkType.VCLK0 = 3
    return mock


@pytest.fixture
def collector():
    return AmdMetricsCollector()


@pytest.fixture
def mock_handle():
    return MagicMock(name="amd_handle")


@pytest.fixture
def mock_amdsmi():
    """Inject a mock amdsmi into the amd_collector module namespace."""
    mock = _make_mock_amdsmi()
    with patch('core.metrics.amd_collector.amdsmi', mock, create=True), \
         patch('core.metrics.amd_collector.HAS_AMDSMI', True):
        yield mock


class TestCollectAll:
    def test_returns_dict_with_required_keys(self, collector, mock_handle, mock_amdsmi):
        # Make all calls raise (simulating unavailable metrics)
        mock_amdsmi.amdsmi_get_gpu_vendor_name.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_board_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_asic_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_vbios_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_driver_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_device_uuid.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_activity.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_memory_usage.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_memory_total.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_temp_metric.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_power_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_power_cap_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_fan_speed.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_fan_rpms.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_clock_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_gpu_pci_info.side_effect = Exception("not available")
        mock_amdsmi.amdsmi_get_pcie_info.side_effect = Exception("not available")

        data = collector.collect_all(mock_handle, '0')

        assert isinstance(data, dict)
        assert data['index'] == '0'
        assert 'timestamp' in data
        assert data['name'] == 'AMD GPU'  # fallback name

    def test_stores_previous_sample(self, collector, mock_handle, mock_amdsmi):
        # Make all calls raise gracefully
        for attr in dir(mock_amdsmi):
            if attr.startswith('amdsmi_get'):
                getattr(mock_amdsmi, attr).side_effect = Exception("not available")

        collector.collect_all(mock_handle, '0')

        assert '0' in collector.previous_samples
        assert '0' in collector.last_sample_time


class TestPerformanceMetrics:
    def test_utilization(self, collector, mock_handle, mock_amdsmi):
        activity = MagicMock()
        activity.gfx_activity = 85
        activity.umc_activity = 40
        mock_amdsmi.amdsmi_get_gpu_activity.return_value = activity

        data = {}
        collector._add_performance(mock_handle, data)

        assert data['utilization'] == 85.0
        assert data['memory_utilization'] == 40.0

    def test_utilization_not_available(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_activity.side_effect = Exception("not supported")

        data = {}
        collector._add_performance(mock_handle, data)

        assert 'utilization' not in data


class TestMemoryMetrics:
    def test_memory_values(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_memory_usage.return_value = 8 * 1024**3
        mock_amdsmi.amdsmi_get_gpu_memory_total.return_value = 24 * 1024**3

        data = {}
        collector._add_memory(mock_handle, data, '0', 1000.0)

        assert data['memory_used'] == 8192.0
        assert data['memory_total'] == 24576.0
        assert data['memory_free'] == 16384.0

    def test_memory_change_rate(self, collector, mock_handle, mock_amdsmi):
        # First sample
        mock_amdsmi.amdsmi_get_gpu_memory_usage.return_value = 8 * 1024**3
        mock_amdsmi.amdsmi_get_gpu_memory_total.return_value = 24 * 1024**3
        data1 = {}
        collector._add_memory(mock_handle, data1, '0', 1000.0)
        collector.previous_samples['0'] = data1.copy()
        collector.last_sample_time['0'] = 1000.0

        # Second sample - more memory used
        mock_amdsmi.amdsmi_get_gpu_memory_usage.return_value = 10 * 1024**3
        data2 = {}
        collector._add_memory(mock_handle, data2, '0', 1001.0)

        assert 'memory_change_rate' in data2
        assert data2['memory_change_rate'] > 0


class TestPowerThermal:
    def test_temperature(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_temp_metric.return_value = 72

        data = {}
        collector._add_temperature(mock_handle, data)

        assert data['temperature'] == 72.0

    def test_power(self, collector, mock_handle, mock_amdsmi):
        power_info = MagicMock()
        power_info.current_socket_power = 250.0
        power_info.power_limit = 350.0
        mock_amdsmi.amdsmi_get_power_info.return_value = power_info

        data = {}
        collector._add_power(mock_handle, data)

        assert data['power_draw'] == 250.0
        assert data['power_limit'] == 350.0

    def test_fan_speed(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_fan_speed.return_value = 1500
        mock_amdsmi.amdsmi_get_gpu_fan_rpms.return_value = 3000

        data = {}
        collector._add_fan_speeds(mock_handle, data)

        assert data['fan_speed'] == 50.0  # 1500/3000 * 100


class TestClocks:
    def test_clock_values(self, collector, mock_handle, mock_amdsmi):
        gfx_clk = MagicMock()
        gfx_clk.clk = 2400
        gfx_clk.max_clk = 2800

        mem_clk = MagicMock()
        mem_clk.clk = 1250
        mem_clk.max_clk = 1250

        mock_amdsmi.amdsmi_get_clock_info.side_effect = [gfx_clk, mem_clk]

        data = {}
        collector._add_clocks(mock_handle, data)

        assert data['clock_graphics'] == 2400.0
        assert data['clock_graphics_max'] == 2800.0
        assert data['clock_memory'] == 1250.0


class TestConnectivity:
    def test_pcie_info(self, collector, mock_handle, mock_amdsmi):
        pci_info = MagicMock()
        pci_info.pci_bus = '0000:03:00.0'
        mock_amdsmi.amdsmi_get_gpu_pci_info.return_value = pci_info

        link_info = MagicMock()
        link_info.pcie_metric.pcie_speed = 4
        link_info.pcie_metric.pcie_width = 16
        link_info.pcie_static.max_pcie_speed = 4
        link_info.pcie_static.max_pcie_width = 16
        mock_amdsmi.amdsmi_get_pcie_info.return_value = link_info

        data = {}
        collector._add_connectivity(mock_handle, data)

        assert data['pci_bus_id'] == '0000:03:00.0'
        assert data['pcie_gen'] == '4'
        assert data['pcie_width'] == '16'

    def test_pcie_throughput(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_pci_info.side_effect = Exception("n/a")
        mock_amdsmi.amdsmi_get_pcie_info.side_effect = Exception("n/a")

        throughput = MagicMock()
        throughput.sent = 1024.0
        throughput.received = 2048.0
        mock_amdsmi.amdsmi_get_gpu_pci_throughput.return_value = throughput

        data = {}
        collector._add_connectivity(mock_handle, data)

        assert data['pcie_tx_throughput'] == 1024.0
        assert data['pcie_rx_throughput'] == 2048.0

    def test_xgmi_info(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_pci_info.side_effect = Exception("n/a")
        mock_amdsmi.amdsmi_get_pcie_info.side_effect = Exception("n/a")
        mock_amdsmi.amdsmi_get_gpu_pci_throughput.side_effect = Exception("n/a")

        xgmi = MagicMock()
        xgmi.xgmi_lanes = 16
        mock_amdsmi.amdsmi_get_xgmi_info.return_value = xgmi

        data = {}
        collector._add_connectivity(mock_handle, data)

        assert data['nvlink_links'] == [{'id': 0, 'active': True, 'lanes': 16}]
        assert data['nvlink_active_count'] == 1


class TestPerformanceLevel:
    def test_perf_level(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_activity.side_effect = Exception("n/a")
        mock_amdsmi.amdsmi_get_gpu_perf_level.return_value = "AmdSmiDevPerfLevel.AUTO"

        data = {}
        collector._add_performance(mock_handle, data)

        assert data['performance_state'] == 'AUTO'

    def test_mm_activity(self, collector, mock_handle, mock_amdsmi):
        activity = MagicMock()
        activity.gfx_activity = 50
        activity.umc_activity = 30
        activity.mm_activity = 75
        mock_amdsmi.amdsmi_get_gpu_activity.return_value = activity

        data = {}
        collector._add_performance(mock_handle, data)

        assert data['encoder_utilization'] == 75.0


class TestThrottling:
    def test_no_throttling(self, collector, mock_handle, mock_amdsmi):
        violation = MagicMock()
        violation.prochot = 0
        violation.ppt = 0
        violation.socket_thermal = 0
        violation.vr_thermal = 0
        violation.hbm_thermal = 0
        mock_amdsmi.amdsmi_get_violation_status.return_value = violation

        data = {}
        collector._add_throttling(mock_handle, data)

        assert data['throttle_reasons'] == 'None'

    def test_with_throttling(self, collector, mock_handle, mock_amdsmi):
        violation = MagicMock()
        violation.prochot = 1
        violation.ppt = 0
        violation.socket_thermal = 1
        violation.vr_thermal = 0
        violation.hbm_thermal = 0
        mock_amdsmi.amdsmi_get_violation_status.return_value = violation

        data = {}
        collector._add_throttling(mock_handle, data)

        assert 'PROCHOT' in data['throttle_reasons']
        assert 'Socket Thermal' in data['throttle_reasons']

    def test_not_available(self, collector, mock_handle, mock_amdsmi):
        del mock_amdsmi.amdsmi_get_violation_status

        data = {}
        collector._add_throttling(mock_handle, data)

        assert 'throttle_reasons' not in data


class TestMediaEngines:
    def test_decoder_utilization(self, collector, mock_handle, mock_amdsmi):
        counter = MagicMock()
        counter.type = "AMDSMI_UTILIZATION_COUNTER_DECODER"
        counter.value = 42.0
        mock_amdsmi.amdsmi_get_utilization_count.return_value = [counter]

        data = {}
        collector._add_media_engines(mock_handle, data)

        assert data['decoder_utilization'] == 42.0

    def test_not_available(self, collector, mock_handle, mock_amdsmi):
        del mock_amdsmi.amdsmi_get_utilization_count

        data = {}
        collector._add_media_engines(mock_handle, data)

        assert 'decoder_utilization' not in data


class TestHealthStatus:
    def test_ecc_enabled(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_ecc_enabled.return_value = True

        ecc = MagicMock()
        ecc.correctable_count = 5
        ecc.uncorrectable_count = 1
        mock_amdsmi.amdsmi_get_gpu_total_ecc_count.return_value = ecc

        data = {}
        collector._add_health_status(mock_handle, data)

        assert data['ecc_enabled'] is True
        assert data['ecc_errors_corrected'] == 5
        assert data['ecc_errors_uncorrected'] == 1

    def test_ecc_not_available(self, collector, mock_handle, mock_amdsmi):
        del mock_amdsmi.amdsmi_get_gpu_ecc_enabled
        del mock_amdsmi.amdsmi_get_gpu_total_ecc_count
        del mock_amdsmi.amdsmi_get_gpu_bad_page_info

        data = {}
        collector._add_health_status(mock_handle, data)

        assert 'ecc_enabled' not in data

    def test_retired_pages(self, collector, mock_handle, mock_amdsmi):
        del mock_amdsmi.amdsmi_get_gpu_ecc_enabled
        del mock_amdsmi.amdsmi_get_gpu_total_ecc_count
        mock_amdsmi.amdsmi_get_gpu_bad_page_info.return_value = [1, 2, 3]

        data = {}
        collector._add_health_status(mock_handle, data)

        assert data['retired_pages'] == 3


class TestAdvanced:
    def test_overdrive_level(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_gpu_overdrive_level.return_value = 10
        mock_amdsmi.amdsmi_get_gpu_mem_overdrive_level.return_value = 5
        del mock_amdsmi.amdsmi_get_gpu_ras_feature_info

        data = {}
        collector._add_advanced(mock_handle, data)

        assert data['overdrive_level'] == 10
        assert data['mem_overdrive_level'] == 5

    def test_ras_version(self, collector, mock_handle, mock_amdsmi):
        ras = MagicMock()
        ras.ras_eeprom_version = 2
        mock_amdsmi.amdsmi_get_gpu_ras_feature_info.return_value = ras
        del mock_amdsmi.amdsmi_get_gpu_overdrive_level
        del mock_amdsmi.amdsmi_get_gpu_mem_overdrive_level

        data = {}
        collector._add_advanced(mock_handle, data)

        assert data['ras_version'] == '2'

    def test_not_available(self, collector, mock_handle, mock_amdsmi):
        del mock_amdsmi.amdsmi_get_gpu_ras_feature_info
        del mock_amdsmi.amdsmi_get_gpu_overdrive_level
        del mock_amdsmi.amdsmi_get_gpu_mem_overdrive_level

        data = {}
        collector._add_advanced(mock_handle, data)

        assert 'overdrive_level' not in data
        assert 'ras_version' not in data


class TestTemperatureExtended:
    def test_hotspot_temperature(self, collector, mock_handle, mock_amdsmi):
        def temp_side_effect(handle, temp_type, metric):
            if temp_type == mock_amdsmi.AmdSmiTemperatureType.EDGE:
                return 65
            elif temp_type == mock_amdsmi.AmdSmiTemperatureType.HOTSPOT:
                return 78
            elif temp_type == mock_amdsmi.AmdSmiTemperatureType.VRAM:
                return 55
            return None

        mock_amdsmi.amdsmi_get_temp_metric.side_effect = temp_side_effect

        data = {}
        collector._add_temperature(mock_handle, data)

        assert data['temperature'] == 65.0
        assert data['temperature_hotspot'] == 78.0
        assert data['temperature_memory'] == 55.0


class TestEnergy:
    def test_energy_consumption(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_power_info.side_effect = Exception("n/a")
        mock_amdsmi.amdsmi_get_power_cap_info.side_effect = Exception("n/a")

        energy = MagicMock()
        energy.energy_accumulator = 1000000.0
        energy.counter_resolution = 1.0
        mock_amdsmi.amdsmi_get_energy_count.return_value = energy

        data = {}
        collector._add_power(mock_handle, data)

        assert 'energy_consumption' in data
        assert 'energy_consumption_wh' in data


class TestPowerCap:
    def test_power_cap_fallback(self, collector, mock_handle, mock_amdsmi):
        mock_amdsmi.amdsmi_get_power_info.side_effect = Exception("n/a")

        cap = MagicMock()
        cap.power_cap = 300.0
        cap.min_power_cap = 100.0
        cap.max_power_cap = 400.0
        mock_amdsmi.amdsmi_get_power_cap_info.return_value = cap

        data = {}
        collector._add_power(mock_handle, data)

        assert data['power_limit'] == 300.0
        assert data['power_limit_min'] == 100.0
        assert data['power_limit_max'] == 400.0


class TestClocksExtended:
    def test_soc_and_video_clocks(self, collector, mock_handle, mock_amdsmi):
        clocks = {}
        def clock_side_effect(handle, clk_type):
            m = MagicMock()
            if clk_type == mock_amdsmi.AmdSmiClkType.GFX:
                m.clk = 2400; m.max_clk = 2800; m.min_clk = 500
            elif clk_type == mock_amdsmi.AmdSmiClkType.MEM:
                m.clk = 1250; m.max_clk = 1250; m.min_clk = 1250
            elif clk_type == mock_amdsmi.AmdSmiClkType.SOC:
                m.clk = 1100; m.max_clk = 1200; m.min_clk = 400
            elif clk_type == mock_amdsmi.AmdSmiClkType.VCLK0:
                m.clk = 800; m.max_clk = 1000; m.min_clk = 200
            return m

        mock_amdsmi.amdsmi_get_clock_info.side_effect = clock_side_effect

        data = {}
        collector._add_clocks(mock_handle, data)

        assert data['clock_graphics'] == 2400.0
        assert data['clock_memory'] == 1250.0
        assert data['clock_sm'] == 1100.0
        assert data['clock_video'] == 800.0
        assert data['clock_graphics_max'] == 2800.0
