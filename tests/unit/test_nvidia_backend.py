"""Tests for core/backends/nvidia.py"""

import pytest
from unittest.mock import patch, MagicMock
import pynvml
import psutil


class TestNvidiaBackendInit:
    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.129.03')
    @patch('pynvml.nvmlDeviceGetCount', return_value=2)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_init_success(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'RTX 3090', 'utilization': 75}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        assert backend.available is True
        assert backend.vendor == "nvidia"
        assert backend._device_count == 2
        mock_init.assert_called_once()

    @patch('core.backends.nvidia.HAS_PYNVML', False)
    def test_init_no_pynvml(self):
        from core.backends.nvidia import NvidiaBackend
        backend = NvidiaBackend()
        assert backend.available is False

    @patch('pynvml.nvmlInit', side_effect=Exception("No NVIDIA driver"))
    def test_init_nvml_failure(self, mock_init):
        from core.backends.nvidia import NvidiaBackend
        backend = NvidiaBackend()
        assert backend.available is False


class TestDetectSmiGpus:
    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=2)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_all_nvml(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'RTX 3090', 'utilization': 75}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        assert backend.use_smi.get('0') is False
        assert backend.use_smi.get('1') is False
        assert backend.uses_cli_fallback is False

    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=2)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_mixed_gpus(self, mock_handle, mock_count, mock_version, mock_init):
        def collect_side_effect(handle, gpu_id):
            if gpu_id == '0':
                return {'name': 'RTX 3090', 'utilization': 75}
            else:
                return {'name': 'GTX 750', 'utilization': None}

        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   side_effect=collect_side_effect):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        assert backend.use_smi.get('0') is False
        assert backend.use_smi.get('1') is True
        assert backend.uses_cli_fallback is True

    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=1)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    @patch('core.backends.nvidia.NVIDIA_SMI', True)
    def test_forced_smi(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'RTX 3090', 'utilization': 75}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        assert backend.use_smi.get('0') is True


class TestDetectGpus:
    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=3)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_returns_device_list(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'RTX 3090', 'utilization': 75}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        gpus = backend.detect_gpus()
        assert gpus == ['0', '1', '2']


class TestCollectGpu:
    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=1)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_nvml_path(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'RTX 3090', 'utilization': 75}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

            data = backend.collect_gpu('0', '0')
            assert data['vendor'] == 'nvidia'
            assert data['index'] == '0'
            assert data['utilization'] == 75

    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=1)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_smi_path(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'GTX 750'}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        assert backend.use_smi.get('0') is True

        smi_result = {'0': {'name': 'GTX 750', 'utilization': 60}}
        with patch('core.backends.nvidia.parse_nvidia_smi', return_value=smi_result):
            data = backend.collect_gpu('0', '0')

        assert data['name'] == 'GTX 750'
        assert data['vendor'] == 'nvidia'


class TestGetProcesses:
    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=1)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_returns_process_list(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'RTX 3090', 'utilization': 75}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        proc = MagicMock()
        proc.pid = 1234
        proc.usedGpuMemory = 4 * 1024**3

        with patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock()), \
             patch('pynvml.nvmlDeviceGetUUID', return_value=b'GPU-abc'), \
             patch('pynvml.nvmlDeviceGetComputeRunningProcesses', return_value=[proc]), \
             patch('psutil.Process') as mock_ps:
            mock_ps.return_value.name.return_value = 'train.py'

            procs = backend.get_processes({'0': {}})

        assert len(procs) == 1
        assert procs[0]['pid'] == '1234'


class TestShutdown:
    @patch('pynvml.nvmlInit')
    @patch('pynvml.nvmlSystemGetDriverVersion', return_value=b'535.0')
    @patch('pynvml.nvmlDeviceGetCount', return_value=1)
    @patch('pynvml.nvmlDeviceGetHandleByIndex', return_value=MagicMock())
    def test_shutdown(self, mock_handle, mock_count, mock_version, mock_init):
        with patch('core.metrics.collector.MetricsCollector.collect_all',
                   return_value={'name': 'RTX 3090', 'utilization': 75}):
            from core.backends.nvidia import NvidiaBackend
            backend = NvidiaBackend()

        assert backend.available is True

        with patch('pynvml.nvmlShutdown') as mock_shutdown:
            backend.shutdown()
            mock_shutdown.assert_called_once()


class TestGetProcessName:
    @patch('psutil.Process')
    def test_normal_process(self, mock_process_cls):
        from core.backends.nvidia import _get_process_name
        proc = MagicMock()
        proc.name.return_value = 'blender'
        mock_process_cls.return_value = proc
        assert _get_process_name(1234) == 'blender'

    @patch('psutil.Process')
    def test_python_process_with_script(self, mock_process_cls):
        from core.backends.nvidia import _get_process_name
        proc = MagicMock()
        proc.name.return_value = 'python3'
        proc.cmdline.return_value = ['python3', '/home/user/train.py', '--epochs', '100']
        mock_process_cls.return_value = proc
        assert _get_process_name(1234) == 'train.py'

    @patch('psutil.Process', side_effect=psutil.NoSuchProcess(pid=9999))
    def test_no_such_process(self, mock_process_cls):
        from core.backends.nvidia import _get_process_name
        assert _get_process_name(9999) == 'PID:9999'
