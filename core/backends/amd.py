"""AMD GPU backend using amdsmi"""

import logging
import psutil

try:
    import amdsmi
    HAS_AMDSMI = True
except Exception:
    HAS_AMDSMI = False

from .base import GPUBackend
from ..metrics.amd_collector import AmdMetricsCollector

logger = logging.getLogger(__name__)


class AmdBackend(GPUBackend):
    """Monitor AMD GPUs using amdsmi"""

    vendor = "amd"

    def __init__(self):
        self.available = False
        self.collector = AmdMetricsCollector()
        self._handles = []

        if not HAS_AMDSMI:
            logger.debug("amdsmi not installed - AMD backend unavailable")
            return

        try:
            amdsmi.amdsmi_init(amdsmi.AmdSmiInitFlags.INIT_AMD_GPUS)
            self._handles = amdsmi.amdsmi_get_processor_handles()

            if self._handles:
                self.available = True
                logger.info(f"AMD SMI initialized - Detected {len(self._handles)} AMD GPU(s)")
                for i, handle in enumerate(self._handles):
                    try:
                        asic = amdsmi.amdsmi_get_gpu_asic_info(handle)
                        name = getattr(asic, 'market_name', 'Unknown')
                        if isinstance(name, bytes):
                            name = name.decode('utf-8')
                        logger.info(f"AMD GPU {i}: {name}")
                    except Exception:
                        logger.info(f"AMD GPU {i}: detected")
            else:
                logger.debug("AMD SMI initialized but no GPU handles found")

        except Exception as e:
            logger.debug(f"AMD SMI initialization failed: {e}")

    def detect_gpus(self) -> list:
        """Return list of device indices as strings"""
        return [str(i) for i in range(len(self._handles))]

    def collect_gpu(self, device_id, gpu_id: str) -> dict:
        """Collect metrics for a single AMD GPU"""
        idx = int(device_id)
        handle = self._handles[idx]

        try:
            data = self.collector.collect_all(handle, gpu_id)
        except Exception as e:
            logger.error(f"AMD GPU {gpu_id}: collection error - {e}")
            return {}

        data['index'] = gpu_id
        data['vendor'] = self.vendor
        return data

    def get_processes(self, gpu_data: dict) -> list:
        """Get GPU process information for all AMD GPUs"""
        all_processes = []

        for i, handle in enumerate(self._handles):
            gpu_id = str(i)
            try:
                proc_list = amdsmi.amdsmi_get_gpu_process_list(handle)
                if not proc_list:
                    continue

                for proc_handle in proc_list:
                    try:
                        proc_info = amdsmi.amdsmi_get_gpu_process_info(handle, proc_handle)
                        if proc_info:
                            pid = getattr(proc_info, 'pid', None)
                            if pid is None:
                                pid = proc_handle  # Some versions use handle as PID

                            mem = getattr(proc_info, 'memory_usage', 0)
                            if hasattr(mem, 'vram_mem'):
                                mem = mem.vram_mem

                            all_processes.append({
                                'pid': str(pid),
                                'name': _get_process_name(pid),
                                'gpu_id': gpu_id,
                                'memory': float(mem / (1024 ** 2)) if mem else 0.0
                            })
                    except Exception:
                        pass

            except Exception:
                pass

        return all_processes

    def shutdown(self) -> None:
        if HAS_AMDSMI and self.available:
            try:
                amdsmi.amdsmi_shut_down()
                logger.info("AMD SMI shutdown")
            except Exception as e:
                logger.error(f"Error shutting down AMD SMI: {e}")


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
    except Exception:
        return f'PID:{pid}'
