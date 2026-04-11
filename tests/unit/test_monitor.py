"""Tests for core/monitor.py (multi-vendor backend orchestration)"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock


def _make_mock_backend(vendor="nvidia", gpu_count=1, available=True, cli_fallback=False):
    """Create a mock GPUBackend instance."""
    backend = MagicMock()
    backend.vendor = vendor
    backend.available = available
    backend.uses_cli_fallback = cli_fallback
    backend.detect_gpus.return_value = [str(i) for i in range(gpu_count)]
    backend.collect_gpu.side_effect = lambda dev_id, gpu_id: {
        'index': gpu_id,
        'name': f'Mock {vendor.upper()} GPU {dev_id}',
        'vendor': vendor,
        'utilization': 75.0,
        'temperature': 65.0,
        'memory_used': 8192.0,
        'memory_total': 24576.0,
    }
    backend.get_processes.return_value = []
    return backend


class TestGPUMonitorInit:
    @patch('core.monitor.AmdBackend')
    @patch('core.monitor.NvidiaBackend')
    def test_init_nvidia_only(self, MockNvidia, MockAmd):
        MockNvidia.return_value = _make_mock_backend("nvidia", gpu_count=2)
        MockAmd.return_value = _make_mock_backend("amd", available=False)

        from core.monitor import GPUMonitor
        monitor = GPUMonitor()

        assert monitor.initialized is True
        assert len(monitor.backends) == 1
        assert len(monitor.gpu_map) == 2

    @patch('core.monitor.AmdBackend')
    @patch('core.monitor.NvidiaBackend')
    def test_init_amd_only(self, MockNvidia, MockAmd):
        MockNvidia.return_value = _make_mock_backend("nvidia", available=False)
        MockAmd.return_value = _make_mock_backend("amd", gpu_count=1)

        from core.monitor import GPUMonitor
        monitor = GPUMonitor()

        assert monitor.initialized is True
        assert len(monitor.backends) == 1
        assert monitor.backends[0].vendor == "amd"

    @patch('core.monitor.AmdBackend')
    @patch('core.monitor.NvidiaBackend')
    def test_init_mixed_vendors(self, MockNvidia, MockAmd):
        MockNvidia.return_value = _make_mock_backend("nvidia", gpu_count=2)
        MockAmd.return_value = _make_mock_backend("amd", gpu_count=1)

        from core.monitor import GPUMonitor
        monitor = GPUMonitor()

        assert monitor.initialized is True
        assert len(monitor.backends) == 2
        # 2 NVIDIA + 1 AMD = 3 total GPUs
        assert len(monitor.gpu_map) == 3
        # NVIDIA GPUs get IDs 0, 1; AMD gets ID 2
        gpu_ids = [gid for _, _, gid in monitor.gpu_map]
        assert gpu_ids == ['0', '1', '2']

    @patch('core.monitor.AmdBackend')
    @patch('core.monitor.NvidiaBackend')
    def test_init_no_gpus(self, MockNvidia, MockAmd):
        MockNvidia.return_value = _make_mock_backend("nvidia", available=False)
        MockAmd.return_value = _make_mock_backend("amd", available=False)

        from core.monitor import GPUMonitor
        monitor = GPUMonitor()

        assert monitor.initialized is False
        assert len(monitor.backends) == 0
        assert len(monitor.gpu_map) == 0

    @patch('core.monitor.AmdBackend')
    @patch('core.monitor.NvidiaBackend')
    def test_backend_init_exception_handled(self, MockNvidia, MockAmd):
        MockNvidia.side_effect = RuntimeError("init crash")
        MockAmd.return_value = _make_mock_backend("amd", gpu_count=1)

        from core.monitor import GPUMonitor
        monitor = GPUMonitor()

        # AMD still works despite NVIDIA crash
        assert monitor.initialized is True
        assert len(monitor.backends) == 1


class TestUsesCliFallback:
    @patch('core.monitor.AmdBackend')
    @patch('core.monitor.NvidiaBackend')
    def test_no_cli_fallback(self, MockNvidia, MockAmd):
        MockNvidia.return_value = _make_mock_backend("nvidia", cli_fallback=False)
        MockAmd.return_value = _make_mock_backend("amd", available=False)

        from core.monitor import GPUMonitor
        monitor = GPUMonitor()
        assert monitor.uses_cli_fallback is False

    @patch('core.monitor.AmdBackend')
    @patch('core.monitor.NvidiaBackend')
    def test_with_cli_fallback(self, MockNvidia, MockAmd):
        MockNvidia.return_value = _make_mock_backend("nvidia", cli_fallback=True)
        MockAmd.return_value = _make_mock_backend("amd", available=False)

        from core.monitor import GPUMonitor
        monitor = GPUMonitor()
        assert monitor.uses_cli_fallback is True


class TestGetGpuData:
    @pytest.mark.asyncio
    async def test_not_initialized(self):
        with patch('core.monitor.NvidiaBackend') as MockNv, \
             patch('core.monitor.AmdBackend') as MockAmd:
            MockNv.return_value = _make_mock_backend("nvidia", available=False)
            MockAmd.return_value = _make_mock_backend("amd", available=False)

            from core.monitor import GPUMonitor
            monitor = GPUMonitor()

        data = await monitor.get_gpu_data()
        assert data == {}

    @pytest.mark.asyncio
    async def test_collects_from_all_backends(self):
        nv_backend = _make_mock_backend("nvidia", gpu_count=1)
        amd_backend = _make_mock_backend("amd", gpu_count=1)

        with patch('core.monitor.NvidiaBackend', return_value=nv_backend), \
             patch('core.monitor.AmdBackend', return_value=amd_backend):
            from core.monitor import GPUMonitor
            monitor = GPUMonitor()

        data = await monitor.get_gpu_data()
        assert '0' in data
        assert '1' in data
        assert data['0']['vendor'] == 'nvidia'
        assert data['1']['vendor'] == 'amd'

    @pytest.mark.asyncio
    async def test_handles_collection_error(self):
        nv_backend = _make_mock_backend("nvidia", gpu_count=2)
        # First GPU succeeds, second raises
        nv_backend.collect_gpu.side_effect = [
            {'index': '0', 'vendor': 'nvidia', 'utilization': 75},
            Exception("GPU error"),
        ]

        with patch('core.monitor.NvidiaBackend', return_value=nv_backend), \
             patch('core.monitor.AmdBackend') as MockAmd:
            MockAmd.return_value = _make_mock_backend("amd", available=False)
            from core.monitor import GPUMonitor
            monitor = GPUMonitor()

        data = await monitor.get_gpu_data()
        assert '0' in data
        assert '1' not in data


class TestGetProcesses:
    @pytest.mark.asyncio
    async def test_merges_processes(self):
        nv_backend = _make_mock_backend("nvidia", gpu_count=1)
        nv_backend.get_processes.return_value = [
            {'pid': '100', 'name': 'train.py', 'gpu_id': '0', 'memory': 4096.0}
        ]
        amd_backend = _make_mock_backend("amd", gpu_count=1)
        amd_backend.get_processes.return_value = [
            {'pid': '200', 'name': 'render', 'gpu_id': '1', 'memory': 2048.0}
        ]

        with patch('core.monitor.NvidiaBackend', return_value=nv_backend), \
             patch('core.monitor.AmdBackend', return_value=amd_backend):
            from core.monitor import GPUMonitor
            monitor = GPUMonitor()

        procs = await monitor.get_processes()
        assert len(procs) == 2
        pids = {p['pid'] for p in procs}
        assert pids == {'100', '200'}

    @pytest.mark.asyncio
    async def test_not_initialized(self):
        with patch('core.monitor.NvidiaBackend') as MockNv, \
             patch('core.monitor.AmdBackend') as MockAmd:
            MockNv.return_value = _make_mock_backend("nvidia", available=False)
            MockAmd.return_value = _make_mock_backend("amd", available=False)
            from core.monitor import GPUMonitor
            monitor = GPUMonitor()

        procs = await monitor.get_processes()
        assert procs == []


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_all_backends(self):
        nv_backend = _make_mock_backend("nvidia")
        amd_backend = _make_mock_backend("amd")

        with patch('core.monitor.NvidiaBackend', return_value=nv_backend), \
             patch('core.monitor.AmdBackend', return_value=amd_backend):
            from core.monitor import GPUMonitor
            monitor = GPUMonitor()

        await monitor.shutdown()
        nv_backend.shutdown.assert_called_once()
        amd_backend.shutdown.assert_called_once()
        assert monitor.initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_not_initialized(self):
        with patch('core.monitor.NvidiaBackend') as MockNv, \
             patch('core.monitor.AmdBackend') as MockAmd:
            MockNv.return_value = _make_mock_backend("nvidia", available=False)
            MockAmd.return_value = _make_mock_backend("amd", available=False)
            from core.monitor import GPUMonitor
            monitor = GPUMonitor()

        await monitor.shutdown()
        assert monitor.initialized is False
