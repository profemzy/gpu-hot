"""Async GPU monitoring with multi-vendor support (NVIDIA + AMD)"""

import asyncio
import logging
from .backends import NvidiaBackend, AmdBackend

logger = logging.getLogger(__name__)


class GPUMonitor:
    """Monitor GPUs from multiple vendors using a unified backend abstraction"""

    def __init__(self):
        self.running = False
        self.gpu_data = {}

        # Try each backend — only those that successfully init are kept
        self.backends = []
        for BackendClass in [NvidiaBackend, AmdBackend]:
            try:
                backend = BackendClass()
                if backend.available:
                    self.backends.append(backend)
            except Exception as e:
                name = getattr(BackendClass, '__name__', str(BackendClass))
                logger.error(f"Failed to initialize {name}: {e}")

        self.initialized = len(self.backends) > 0

        # Build unified GPU map: [(backend, device_id, global_gpu_id), ...]
        self.gpu_map = []
        idx = 0
        for backend in self.backends:
            for device_id in backend.detect_gpus():
                self.gpu_map.append((backend, device_id, str(idx)))
                idx += 1

        if self.initialized:
            vendors = [b.vendor for b in self.backends]
            logger.info(f"GPU monitoring initialized: {len(self.gpu_map)} GPU(s) across backends: {', '.join(vendors)}")
        else:
            logger.error("No GPU backends available")

    @property
    def uses_cli_fallback(self):
        """Whether any backend uses a CLI fallback (requires slower polling)"""
        return any(b.uses_cli_fallback for b in self.backends)

    async def get_gpu_data(self):
        """Async collect metrics from all detected GPUs across all backends"""
        if not self.initialized:
            logger.error("Cannot get GPU data - no backends initialized")
            return {}

        try:
            gpu_data = {}

            # Collect data from all GPUs concurrently via thread pool
            tasks = []
            for backend, device_id, gpu_id in self.gpu_map:
                task = asyncio.get_event_loop().run_in_executor(
                    None, backend.collect_gpu, device_id, gpu_id
                )
                tasks.append((gpu_id, task))

            if tasks:
                results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)
                for (gpu_id, _), result in zip(tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"GPU {gpu_id}: Error - {result}")
                    elif result:
                        gpu_data[gpu_id] = result

            if not gpu_data:
                logger.error("No GPU data collected from any backend")

            self.gpu_data = gpu_data
            return gpu_data

        except Exception as e:
            logger.error(f"Failed to get GPU data: {e}")
            return {}

    async def get_processes(self):
        """Async get GPU process information from all backends"""
        if not self.initialized:
            return []

        try:
            all_processes = []

            # Collect processes from each backend in thread pool
            tasks = []
            for backend in self.backends:
                task = asyncio.get_event_loop().run_in_executor(
                    None, backend.get_processes, self.gpu_data
                )
                tasks.append(task)

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error getting processes: {result}")
                    elif result:
                        all_processes.extend(result)

            return all_processes

        except Exception as e:
            logger.error(f"Error getting processes: {e}")
            return []

    async def shutdown(self):
        """Async shutdown all backends"""
        for backend in self.backends:
            try:
                backend.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {backend.vendor} backend: {e}")
        self.initialized = False
        logger.info("All GPU backends shut down")
