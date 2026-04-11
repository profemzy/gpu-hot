"""Shared test fixtures for gpu-hot backend tests"""

import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ---------------------------------------------------------------------------
# pynvml mock helpers
# ---------------------------------------------------------------------------

def make_mock_nvml_device():
    """Create a pre-configured mock NVML device handle with realistic GPU data."""
    handle = MagicMock(name="nvml_handle")

    # Utilization rates
    util = MagicMock()
    util.gpu = 75
    util.memory = 45
    handle._util = util

    # Memory info
    mem = MagicMock()
    mem.used = 8 * 1024**3      # 8 GiB
    mem.total = 24 * 1024**3    # 24 GiB
    mem.free = 16 * 1024**3     # 16 GiB
    handle._mem = mem

    # BAR1 memory
    bar1 = MagicMock()
    bar1.bar1Used = 256 * 1024**2
    bar1.bar1Total = 256 * 1024**2
    handle._bar1 = bar1

    # PCI info
    pci = MagicMock()
    pci.busId = b"00000000:01:00.0"
    handle._pci = pci

    return handle


def configure_nvml_patches(mock_nvml_funcs, handle=None):
    """Configure all pynvml function return values for a mock device."""
    if handle is None:
        handle = make_mock_nvml_device()

    mock_nvml_funcs['nvmlDeviceGetName'].return_value = b"NVIDIA GeForce RTX 3090"
    mock_nvml_funcs['nvmlDeviceGetUUID'].return_value = b"GPU-abc-1234-5678"
    mock_nvml_funcs['nvmlSystemGetDriverVersion'].return_value = b"535.129.03"
    mock_nvml_funcs['nvmlDeviceGetVbiosVersion'].return_value = b"94.02.42.00.A1"
    mock_nvml_funcs['nvmlDeviceGetUtilizationRates'].return_value = handle._util
    mock_nvml_funcs['nvmlDeviceGetMemoryInfo'].return_value = handle._mem
    mock_nvml_funcs['nvmlDeviceGetBAR1MemoryInfo'].return_value = handle._bar1
    mock_nvml_funcs['nvmlDeviceGetTemperature'].return_value = 72
    mock_nvml_funcs['nvmlDeviceGetPowerUsage'].return_value = 250000  # milliwatts
    mock_nvml_funcs['nvmlDeviceGetPowerManagementLimit'].return_value = 350000
    mock_nvml_funcs['nvmlDeviceGetFanSpeed'].return_value = 65
    mock_nvml_funcs['nvmlDeviceGetClockInfo'].return_value = 1800
    mock_nvml_funcs['nvmlDeviceGetMaxClockInfo'].return_value = 2100
    mock_nvml_funcs['nvmlDeviceGetPerformanceState'].return_value = 0
    mock_nvml_funcs['nvmlDeviceGetComputeMode'].return_value = 0
    mock_nvml_funcs['nvmlDeviceGetBrand'].return_value = 8
    mock_nvml_funcs['nvmlDeviceGetCudaComputeCapability'].return_value = (8, 6)
    mock_nvml_funcs['nvmlDeviceGetCurrPcieLinkGeneration'].return_value = 4
    mock_nvml_funcs['nvmlDeviceGetMaxPcieLinkGeneration'].return_value = 4
    mock_nvml_funcs['nvmlDeviceGetCurrPcieLinkWidth'].return_value = 16
    mock_nvml_funcs['nvmlDeviceGetMaxPcieLinkWidth'].return_value = 16
    mock_nvml_funcs['nvmlDeviceGetPciInfo'].return_value = handle._pci
    mock_nvml_funcs['nvmlDeviceGetPersistenceMode'].return_value = 1
    mock_nvml_funcs['nvmlDeviceGetDisplayActive'].return_value = 0
    mock_nvml_funcs['nvmlDeviceGetMultiGpuBoard'].return_value = 0
    mock_nvml_funcs['nvmlDeviceGetGraphicsRunningProcesses'].return_value = []

    return handle


@pytest.fixture
def mock_nvml_device():
    """Provide a pre-configured mock NVML device handle."""
    return make_mock_nvml_device()


# ---------------------------------------------------------------------------
# Sample nvidia-smi CSV output
# ---------------------------------------------------------------------------

NVIDIA_SMI_CSV_FULL = (
    "0, NVIDIA GeForce RTX 3090, GPU-abc-1234-5678, 535.129.03, 94.02.42.00.A1, "
    "72, 75, 45, 8192, 24576, 16384, 250.00, 350.00, "
    "65, 1800, 1800, 5001, "
    "2100, 2100, 5505, "
    "4, 4, 16, 16, "
    "0, 0.0, 0.0, "
    "P0, Default, "
    "0, 0"
)

NVIDIA_SMI_CSV_BASIC = (
    "0, NVIDIA GeForce RTX 3090, 72, 75, 45, "
    "8192, 24576, 250.00, 350.00, 65, "
    "1800, 1800, 5001, P0"
)


@pytest.fixture
def mock_subprocess_nvidia_smi():
    """Patch subprocess.run to return fake nvidia-smi CSV output."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = NVIDIA_SMI_CSV_FULL + "\n"
    with patch('subprocess.run', return_value=result) as mock_run:
        yield mock_run


@pytest.fixture
def sample_gpu_info():
    """Sample GPU info dict as returned by the backend."""
    return {
        'index': '0',
        'name': 'NVIDIA GeForce RTX 3090',
        'uuid': 'GPU-abc-1234-5678',
        'driver_version': '535.129.03',
        'utilization': 75.0,
        'memory_utilization': 45.0,
        'temperature': 72.0,
        'memory_used': 8192.0,
        'memory_total': 24576.0,
        'memory_free': 16384.0,
        'power_draw': 250.0,
        'power_limit': 350.0,
        'fan_speed': 65.0,
        'clock_graphics': 1800.0,
        'clock_sm': 1800.0,
        'clock_memory': 5001.0,
        'performance_state': 'P0',
        'pcie_gen': '4',
        'pcie_width': '16',
        'architecture': 'Ampere',
        'brand': 'GeForce RTX',
        'timestamp': '2025-01-01T00:00:00',
    }


@pytest.fixture
def sample_amd_gpu_info():
    """Sample AMD GPU info dict as returned by the backend."""
    return {
        'index': '0',
        'name': 'AMD Radeon RX 7900 XTX',
        'vendor': 'amd',
        'utilization': 80.0,
        'memory_utilization': 40.0,
        'temperature': 65.0,
        'memory_used': 16384.0,
        'memory_total': 24576.0,
        'memory_free': 8192.0,
        'power_draw': 300.0,
        'power_limit': 355.0,
        'fan_speed': 50.0,
        'clock_graphics': 2400.0,
        'clock_memory': 1250.0,
        'pcie_gen': '4',
        'pcie_width': '16',
        'timestamp': '2025-01-01T00:00:00',
    }


@pytest.fixture
def sample_system_info():
    """Sample system info dict as collected by the monitor loop."""
    return {
        'cpu_percent': 25.0,
        'memory_percent': 60.0,
        'memory_total_gb': 64.0,
        'memory_used_gb': 38.0,
        'memory_available_gb': 26.0,
        'cpu_count': 16,
        'swap_percent': 5.0,
        'load_avg_1': 2.5,
        'load_avg_5': 3.0,
        'load_avg_15': 2.8,
        'net_bytes_sent': 1000000,
        'net_bytes_recv': 5000000,
        'disk_read_bytes': 2000000,
        'disk_write_bytes': 3000000,
        'timestamp': '2025-01-01T00:00:00',
    }
