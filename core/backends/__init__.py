"""GPU backend abstraction layer for multi-vendor support"""

from .base import GPUBackend
from .nvidia import NvidiaBackend
from .amd import AmdBackend

__all__ = ['GPUBackend', 'NvidiaBackend', 'AmdBackend']
