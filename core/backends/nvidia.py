"""NVIDIA GPU backend using NVML (pynvml) with nvidia-smi fallback"""

import logging
import psutil

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False

from .base import GPUBackend
from ..metrics import MetricsCollector
from ..nvidia_smi_fallback import parse_nvidia_smi
from ..config import NVIDIA_SMI

logger = logging.getLogger(__name__)


class NvidiaBackend(GPUBackend):
    """Monitor NVIDIA GPUs using NVML with nvidia-smi fallback"""

    vendor = "nvidia"

    def __init__(self):
        self.available = False
        self.collector = MetricsCollector()
        self.use_smi = {}  # Track which GPUs use nvidia-smi (decided at boot)
        self._device_count = 0

        if not HAS_PYNVML:
            logger.debug("pynvml not installed - NVIDIA backend unavailable")
            return

        try:
            pynvml.nvmlInit()
            version = pynvml.nvmlSystemGetDriverVersion()
            if isinstance(version, bytes):
                version = version.decode('utf-8')
            logger.info(f"NVML initialized - Driver: {version}")

            self._device_count = pynvml.nvmlDeviceGetCount()
            logger.info(f"Detected {self._device_count} NVIDIA GPU(s)")

            self._detect_smi_gpus()
            self.available = self._device_count > 0

        except Exception as e:
            logger.error(f"Failed to initialize NVML: {e}")

    def _detect_smi_gpus(self):
        """Detect which GPUs need nvidia-smi fallback (called once at boot)"""
        if NVIDIA_SMI:
            logger.warning("NVIDIA_SMI=True - Forcing nvidia-smi for all GPUs")
            for i in range(self._device_count):
                self.use_smi[str(i)] = True
            return

        for i in range(self._device_count):
            gpu_id = str(i)
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                data = self.collector.collect_all(handle, gpu_id)
                gpu_name = data.get('name', 'Unknown')

                if 'utilization' not in data or data.get('utilization') is None:
                    self.use_smi[gpu_id] = True
                    logger.warning(f"GPU {i} ({gpu_name}): Utilization not available via NVML, switching to nvidia-smi")
                else:
                    self.use_smi[gpu_id] = False
                    logger.info(f"GPU {i} ({gpu_name}): Using NVML (utilization: {data.get('utilization')}%)")

            except Exception as e:
                self.use_smi[gpu_id] = True
                logger.error(f"GPU {i}: NVML detection failed - {e}, falling back to nvidia-smi")

        nvml_count = sum(1 for v in self.use_smi.values() if not v)
        smi_count = sum(1 for v in self.use_smi.values() if v)
        if smi_count > 0:
            logger.info(f"NVIDIA boot detection: {nvml_count} GPU(s) NVML, {smi_count} GPU(s) nvidia-smi")
        else:
            logger.info(f"NVIDIA boot detection: All {nvml_count} GPU(s) using NVML")

    def detect_gpus(self) -> list:
        """Return list of device indices as strings"""
        return [str(i) for i in range(self._device_count)]

    def collect_gpu(self, device_id, gpu_id: str) -> dict:
        """Collect metrics for a single NVIDIA GPU"""
        idx = int(device_id)

        if self.use_smi.get(device_id, False):
            smi_data = parse_nvidia_smi()
            data = smi_data.get(device_id, {})
        else:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
                data = self.collector.collect_all(handle, gpu_id)
            except Exception as e:
                logger.error(f"GPU {gpu_id}: NVML error - {e}")
                return {}

        data['index'] = gpu_id
        data['vendor'] = self.vendor
        return data

    def get_processes(self, gpu_data: dict) -> list:
        """Get GPU process information for all NVIDIA GPUs"""
        all_processes = []
        gpu_process_counts = {}

        for i in range(self._device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                uuid = pynvml.nvmlDeviceGetUUID(handle)
                if isinstance(uuid, bytes):
                    uuid = uuid.decode('utf-8')

                gpu_id = str(i)
                gpu_process_counts[gpu_id] = {'compute': 0, 'graphics': 0}

                try:
                    procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                    gpu_process_counts[gpu_id]['compute'] = len(procs)

                    for proc in procs:
                        all_processes.append({
                            'pid': str(proc.pid),
                            'name': _get_process_name(proc.pid),
                            'gpu_uuid': uuid,
                            'gpu_id': gpu_id,
                            'memory': float(proc.usedGpuMemory / (1024 ** 2))
                        })
                except pynvml.NVMLError:
                    pass

            except pynvml.NVMLError:
                continue

        for gpu_id, counts in gpu_process_counts.items():
            if gpu_id in gpu_data:
                gpu_data[gpu_id]['compute_processes_count'] = counts['compute']
                gpu_data[gpu_id]['graphics_processes_count'] = counts['graphics']

        return all_processes

    @property
    def uses_cli_fallback(self) -> bool:
        return any(self.use_smi.values())

    def shutdown(self) -> None:
        if HAS_PYNVML and self.available:
            try:
                pynvml.nvmlShutdown()
                logger.info("NVML shutdown")
            except Exception as e:
                logger.error(f"Error shutting down NVML: {e}")


def _get_process_name(pid):
    """Extract readable process name from PID"""
    try:
        p = psutil.Process(pid)

        try:
            process_name = p.name()
            if process_name and process_name not in ['python', 'python3', 'sh', 'bash']:
                return process_name
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass

        try:
            cmdline = p.cmdline()
            if cmdline:
                for arg in cmdline:
                    if not arg or arg.startswith('-'):
                        continue
                    if arg in ['python', 'python3', 'node', 'java', 'sh', 'bash', 'zsh']:
                        continue
                    filename = arg.split('/')[-1].split('\\')[-1]
                    if filename in ['python', 'python3', 'node', 'java', 'sh', 'bash']:
                        continue
                    if filename:
                        return filename

                if cmdline[0]:
                    return cmdline[0].split('/')[-1].split('\\')[-1]

        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass

        return f'PID:{pid}'

    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return f'PID:{pid}'
    except Exception as e:
        logger.debug(f"Error getting process name for PID {pid}: {e}")
        return f'PID:{pid}'
