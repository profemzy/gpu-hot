"""Tests for core/backends/amd.py"""

import pytest
from unittest.mock import patch, MagicMock
import psutil


def _make_mock_amdsmi():
    """Create a mock amdsmi module."""
    mock_amdsmi = MagicMock()
    mock_amdsmi.AmdSmiInitFlags.INIT_AMD_GPUS = 0
    mock_amdsmi.AmdSmiMemoryType.VRAM = 0
    mock_amdsmi.AmdSmiTemperatureType.EDGE = 0
    mock_amdsmi.AmdSmiTemperatureType.HOTSPOT = 1
    mock_amdsmi.AmdSmiTemperatureType.VRAM = 2
    mock_amdsmi.AmdSmiTemperatureMetric.CURRENT = 0
    mock_amdsmi.AmdSmiClkType.GFX = 0
    mock_amdsmi.AmdSmiClkType.MEM = 1
    return mock_amdsmi


def _make_amd_backend(mock_amdsmi, handles):
    """Create an AmdBackend with mocked amdsmi and given handles."""
    mock_amdsmi.amdsmi_get_processor_handles.return_value = handles

    asic_info = MagicMock()
    asic_info.market_name = 'Radeon RX 7900 XTX'
    mock_amdsmi.amdsmi_get_gpu_asic_info.return_value = asic_info

    with patch('core.backends.amd.HAS_AMDSMI', True), \
         patch('core.backends.amd.amdsmi', mock_amdsmi, create=True):
        from core.backends.amd import AmdBackend
        backend = AmdBackend()

    return backend


class TestAmdBackendInit:
    def test_init_success(self):
        mock_amdsmi = _make_mock_amdsmi()
        handle1, handle2 = MagicMock(), MagicMock()
        backend = _make_amd_backend(mock_amdsmi, [handle1, handle2])

        assert backend.available is True
        assert backend.vendor == "amd"
        assert len(backend._handles) == 2
        mock_amdsmi.amdsmi_init.assert_called_once()

    @patch('core.backends.amd.HAS_AMDSMI', False)
    def test_init_no_amdsmi(self):
        from core.backends.amd import AmdBackend
        backend = AmdBackend()
        assert backend.available is False

    def test_init_no_gpus(self):
        mock_amdsmi = _make_mock_amdsmi()
        backend = _make_amd_backend(mock_amdsmi, [])
        assert backend.available is False

    def test_init_amdsmi_failure(self):
        mock_amdsmi = _make_mock_amdsmi()
        mock_amdsmi.amdsmi_init.side_effect = Exception("ROCm not found")

        with patch('core.backends.amd.HAS_AMDSMI', True), \
             patch('core.backends.amd.amdsmi', mock_amdsmi, create=True):
            from core.backends.amd import AmdBackend
            backend = AmdBackend()

        assert backend.available is False


class TestDetectGpus:
    def test_returns_device_list(self):
        mock_amdsmi = _make_mock_amdsmi()
        backend = _make_amd_backend(mock_amdsmi, [MagicMock(), MagicMock(), MagicMock()])

        gpus = backend.detect_gpus()
        assert gpus == ['0', '1', '2']


class TestCollectGpu:
    def test_collect_returns_standard_shape(self):
        mock_amdsmi = _make_mock_amdsmi()
        handle = MagicMock()
        backend = _make_amd_backend(mock_amdsmi, [handle])

        # Mock the collector to return known data
        backend.collector = MagicMock()
        backend.collector.collect_all.return_value = {
            'index': '0',
            'name': 'AMD Radeon RX 7900 XTX',
            'utilization': 80.0,
            'temperature': 65.0,
            'memory_used': 16384.0,
            'memory_total': 24576.0,
            'timestamp': '2025-01-01T00:00:00',
        }

        data = backend.collect_gpu('0', '5')

        assert data['index'] == '5'  # global GPU ID, not device index
        assert data['vendor'] == 'amd'
        assert data['utilization'] == 80.0
        assert data['memory_total'] == 24576.0

    def test_collect_handles_error(self):
        mock_amdsmi = _make_mock_amdsmi()
        handle = MagicMock()
        backend = _make_amd_backend(mock_amdsmi, [handle])

        backend.collector = MagicMock()
        backend.collector.collect_all.side_effect = Exception("collection error")

        data = backend.collect_gpu('0', '0')
        assert data == {}


class TestGetProcesses:
    def test_returns_process_list(self):
        mock_amdsmi = _make_mock_amdsmi()
        handle = MagicMock()
        backend = _make_amd_backend(mock_amdsmi, [handle])

        proc_handle = MagicMock()
        mock_amdsmi.amdsmi_get_gpu_process_list.return_value = [proc_handle]
        proc_info = MagicMock()
        proc_info.pid = 5678
        proc_info.memory_usage = MagicMock(vram_mem=2 * 1024**3)
        mock_amdsmi.amdsmi_get_gpu_process_info.return_value = proc_info

        # Patch amdsmi back into the module for get_processes call
        with patch('core.backends.amd.amdsmi', mock_amdsmi, create=True):
            with patch('psutil.Process') as mock_ps:
                mock_ps.return_value.name.return_value = 'rocm_app'
                procs = backend.get_processes({})

        assert len(procs) == 1
        assert procs[0]['pid'] == '5678'
        assert procs[0]['name'] == 'rocm_app'
        assert procs[0]['gpu_id'] == '0'

    def test_no_processes(self):
        mock_amdsmi = _make_mock_amdsmi()
        handle = MagicMock()
        backend = _make_amd_backend(mock_amdsmi, [handle])

        mock_amdsmi.amdsmi_get_gpu_process_list.return_value = None

        with patch('core.backends.amd.amdsmi', mock_amdsmi, create=True):
            procs = backend.get_processes({})
        assert procs == []


class TestShutdown:
    def test_shutdown(self):
        mock_amdsmi = _make_mock_amdsmi()
        backend = _make_amd_backend(mock_amdsmi, [MagicMock()])

        with patch('core.backends.amd.HAS_AMDSMI', True), \
             patch('core.backends.amd.amdsmi', mock_amdsmi, create=True):
            backend.shutdown()

        mock_amdsmi.amdsmi_shut_down.assert_called_once()


class TestGetProcessName:
    @patch('psutil.Process')
    def test_normal_process(self, mock_process_cls):
        from core.backends.amd import _get_process_name
        proc = MagicMock()
        proc.name.return_value = 'rocm_smi'
        mock_process_cls.return_value = proc
        assert _get_process_name(1234) == 'rocm_smi'

    @patch('psutil.Process', side_effect=psutil.NoSuchProcess(pid=9999))
    def test_no_such_process(self, mock_process_cls):
        from core.backends.amd import _get_process_name
        assert _get_process_name(9999) == 'PID:9999'
