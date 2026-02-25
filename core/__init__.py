"""
GPU Hot - Core Package
Real-time NVIDIA GPU monitoring application
"""

from .monitor import GPUMonitor
from . import config

__all__ = ['GPUMonitor', 'config']

