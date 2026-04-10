"""Tests for core/metrics/utils.py"""

import pytest
from unittest.mock import MagicMock
import pynvml

from core.metrics.utils import safe_get, decode_bytes, to_mib, to_watts


# ---------------------------------------------------------------------------
# safe_get
# ---------------------------------------------------------------------------

class TestSafeGet:
    def test_success(self):
        func = MagicMock(return_value=42)
        assert safe_get(func) == 42

    def test_with_args(self):
        func = MagicMock(return_value="ok")
        result = safe_get(func, "a", "b")
        func.assert_called_once_with("a", "b")
        assert result == "ok"

    def test_nvml_error_returns_default(self):
        func = MagicMock(side_effect=pynvml.NVMLError(pynvml.NVML_ERROR_NOT_SUPPORTED))
        assert safe_get(func) is None

    def test_generic_exception_returns_default(self):
        func = MagicMock(side_effect=RuntimeError("boom"))
        assert safe_get(func) is None

    def test_none_result_returns_default(self):
        func = MagicMock(return_value=None)
        assert safe_get(func, default="fallback") == "fallback"

    def test_custom_default(self):
        func = MagicMock(side_effect=pynvml.NVMLError(pynvml.NVML_ERROR_NOT_SUPPORTED))
        assert safe_get(func, default=-1) == -1

    def test_zero_is_valid(self):
        func = MagicMock(return_value=0)
        assert safe_get(func) == 0

    def test_empty_string_is_valid(self):
        func = MagicMock(return_value="")
        assert safe_get(func) == ""


# ---------------------------------------------------------------------------
# decode_bytes
# ---------------------------------------------------------------------------

class TestDecodeBytes:
    def test_from_bytes(self):
        assert decode_bytes(b"hello") == "hello"

    def test_from_string(self):
        assert decode_bytes("hello") == "hello"

    def test_empty_bytes(self):
        assert decode_bytes(b"") == ""

    def test_utf8_bytes(self):
        assert decode_bytes("NVIDIA RTX".encode('utf-8')) == "NVIDIA RTX"


# ---------------------------------------------------------------------------
# to_mib
# ---------------------------------------------------------------------------

class TestToMib:
    def test_zero(self):
        assert to_mib(0) == 0.0

    def test_one_mib(self):
        assert to_mib(1024 ** 2) == 1.0

    def test_large_value(self):
        # 24 GiB in bytes -> 24576.0 MiB
        assert to_mib(24 * 1024**3) == 24576.0

    def test_returns_float(self):
        result = to_mib(1024**2)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# to_watts
# ---------------------------------------------------------------------------

class TestToWatts:
    def test_zero(self):
        assert to_watts(0) == 0.0

    def test_250_watts(self):
        assert to_watts(250000) == 250.0

    def test_fractional(self):
        assert to_watts(1500) == 1.5

    def test_returns_float(self):
        result = to_watts(1000)
        assert isinstance(result, float)
