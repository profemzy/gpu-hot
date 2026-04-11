"""Abstract base class for GPU monitoring backends"""

from abc import ABC, abstractmethod


class GPUBackend(ABC):
    """Abstract interface for vendor-specific GPU monitoring"""

    available: bool = False
    vendor: str = "unknown"

    @abstractmethod
    def detect_gpus(self) -> list:
        """Return list of internal device identifiers (vendor-specific)"""
        pass

    @abstractmethod
    def collect_gpu(self, device_id, gpu_id: str) -> dict:
        """Collect metrics for one GPU, returning the standard metric dict.

        Args:
            device_id: Vendor-specific device identifier (e.g. NVML index, amdsmi handle)
            gpu_id: Global GPU ID string assigned by GPUMonitor
        """
        pass

    @abstractmethod
    def get_processes(self, gpu_data: dict) -> list:
        """Return process list in standard format.

        Args:
            gpu_data: Current GPU data dict (for enriching process info)
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up vendor library resources"""
        pass

    @property
    def uses_cli_fallback(self) -> bool:
        """Whether any GPU in this backend uses a CLI tool (slower polling)"""
        return False
