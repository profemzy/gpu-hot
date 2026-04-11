"""GPU metrics collector using AMD SMI (amdsmi)"""

import time
import logging
from datetime import datetime
from .utils import safe_get, decode_bytes, to_mib

logger = logging.getLogger(__name__)

try:
    import amdsmi
    HAS_AMDSMI = True
except Exception:
    HAS_AMDSMI = False


class AmdMetricsCollector:
    """Collect all available GPU metrics via amdsmi.

    Mirrors MetricsCollector's output shape so the frontend
    receives the same JSON keys regardless of GPU vendor.
    """

    def __init__(self):
        self.previous_samples = {}
        self.last_sample_time = {}

    def collect_all(self, handle, gpu_id):
        """Collect all available metrics for an AMD GPU"""
        data = {
            'index': gpu_id,
            'timestamp': datetime.now().isoformat()
        }
        current_time = time.time()

        self._add_basic_info(handle, data)
        self._add_performance(handle, data)
        self._add_memory(handle, data, gpu_id, current_time)
        self._add_power_thermal(handle, data)
        self._add_clocks(handle, data)
        self._add_connectivity(handle, data)
        self._add_media_engines(handle, data)
        self._add_health_status(handle, data)
        self._add_advanced(handle, data)

        self.previous_samples[gpu_id] = data.copy()
        self.last_sample_time[gpu_id] = current_time

        return data

    # ------------------------------------------------------------------
    # Basic info
    # ------------------------------------------------------------------

    def _add_basic_info(self, handle, data):
        """Basic GPU information"""
        if market_name := safe_get(amdsmi.amdsmi_get_gpu_vendor_name, handle):
            data['name'] = decode_bytes(market_name)

        # Board info: product name + serial
        try:
            board_info = amdsmi.amdsmi_get_gpu_board_info(handle)
            if board_info:
                if hasattr(board_info, 'product_name'):
                    product = board_info.product_name
                    if isinstance(product, bytes):
                        product = product.decode('utf-8')
                    if product and product.strip():
                        data['name'] = product.strip()
                if hasattr(board_info, 'product_serial'):
                    serial = board_info.product_serial
                    if isinstance(serial, bytes):
                        serial = serial.decode('utf-8')
                    if serial and serial.strip():
                        data['serial'] = serial.strip()
        except Exception:
            pass

        # ASIC info for additional details
        try:
            asic_info = amdsmi.amdsmi_get_gpu_asic_info(handle)
            if asic_info:
                if hasattr(asic_info, 'market_name') and asic_info.market_name:
                    name = asic_info.market_name
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    if name.strip():
                        data['name'] = name.strip()
                if hasattr(asic_info, 'vendor_id'):
                    data['vendor_id'] = str(asic_info.vendor_id)
                if hasattr(asic_info, 'device_id'):
                    data['device_id'] = str(asic_info.device_id)
        except Exception:
            pass

        if 'name' not in data:
            data['name'] = 'AMD GPU'

        # VBIOS version
        try:
            vbios = amdsmi.amdsmi_get_gpu_vbios_info(handle)
            if vbios:
                if hasattr(vbios, 'version'):
                    ver = vbios.version
                    if isinstance(ver, bytes):
                        ver = ver.decode('utf-8')
                    data['vbios_version'] = ver
        except Exception:
            pass

        # Driver version
        try:
            driver_info = amdsmi.amdsmi_get_gpu_driver_info(handle)
            if driver_info and hasattr(driver_info, 'driver_version'):
                ver = driver_info.driver_version
                if isinstance(ver, bytes):
                    ver = ver.decode('utf-8')
                data['driver_version'] = ver
        except Exception:
            pass

        # UUID
        if uuid := safe_get(amdsmi.amdsmi_get_gpu_device_uuid, handle):
            data['uuid'] = decode_bytes(uuid)

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    def _add_performance(self, handle, data):
        """Performance metrics"""
        try:
            activity = amdsmi.amdsmi_get_gpu_activity(handle)
            if activity:
                if hasattr(activity, 'gfx_activity'):
                    data['utilization'] = float(activity.gfx_activity)
                if hasattr(activity, 'umc_activity'):
                    data['memory_utilization'] = float(activity.umc_activity)
                # Media engine activity (encoder/decoder equivalent)
                if hasattr(activity, 'mm_activity'):
                    mm = activity.mm_activity
                    if mm is not None and mm > 0:
                        data['encoder_utilization'] = float(mm)
        except Exception:
            pass

        # Performance level (AMD equivalent of P-state)
        try:
            perf_level = amdsmi.amdsmi_get_gpu_perf_level(handle)
            if perf_level is not None:
                # amdsmi returns an enum; convert to a readable string
                level_str = str(perf_level)
                # Strip enum prefix if present (e.g. "AmdSmiDevPerfLevel.AUTO" -> "AUTO")
                if '.' in level_str:
                    level_str = level_str.split('.')[-1]
                data['performance_state'] = level_str
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def _add_memory(self, handle, data, gpu_id, current_time):
        """Memory metrics"""
        try:
            vram_used = amdsmi.amdsmi_get_gpu_memory_usage(
                handle, amdsmi.AmdSmiMemoryType.VRAM
            )
            vram_total = amdsmi.amdsmi_get_gpu_memory_total(
                handle, amdsmi.AmdSmiMemoryType.VRAM
            )
            if vram_used is not None and vram_total is not None:
                data['memory_used'] = to_mib(vram_used)
                data['memory_total'] = to_mib(vram_total)
                data['memory_free'] = to_mib(vram_total - vram_used)

                # Calculate change rate
                if gpu_id in self.previous_samples:
                    prev = self.previous_samples[gpu_id]
                    if 'memory_used' in prev:
                        dt = current_time - self.last_sample_time.get(gpu_id, current_time)
                        if dt > 0:
                            delta = data['memory_used'] - prev['memory_used']
                            data['memory_change_rate'] = float(delta / dt)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Power & thermal
    # ------------------------------------------------------------------

    def _add_power_thermal(self, handle, data):
        """Power and thermal metrics"""
        self._add_temperature(handle, data)
        self._add_power(handle, data)
        self._add_fan_speeds(handle, data)
        self._add_throttling(handle, data)

    def _add_temperature(self, handle, data):
        # Edge temperature (GPU core equivalent)
        try:
            temp = amdsmi.amdsmi_get_temp_metric(
                handle, amdsmi.AmdSmiTemperatureType.EDGE,
                amdsmi.AmdSmiTemperatureMetric.CURRENT
            )
            if temp is not None:
                data['temperature'] = float(temp)
        except Exception:
            pass

        # Junction/hotspot temperature
        try:
            temp_hot = amdsmi.amdsmi_get_temp_metric(
                handle, amdsmi.AmdSmiTemperatureType.HOTSPOT,
                amdsmi.AmdSmiTemperatureMetric.CURRENT
            )
            if temp_hot is not None and temp_hot > 0:
                data['temperature_hotspot'] = float(temp_hot)
        except Exception:
            pass

        # VRAM temperature
        try:
            temp_mem = amdsmi.amdsmi_get_temp_metric(
                handle, amdsmi.AmdSmiTemperatureType.VRAM,
                amdsmi.AmdSmiTemperatureMetric.CURRENT
            )
            if temp_mem is not None and temp_mem > 0:
                data['temperature_memory'] = float(temp_mem)
        except Exception:
            pass

    def _add_power(self, handle, data):
        # Current power draw
        try:
            power_info = amdsmi.amdsmi_get_power_info(handle)
            if power_info:
                if hasattr(power_info, 'current_socket_power'):
                    data['power_draw'] = float(power_info.current_socket_power)
                elif hasattr(power_info, 'average_socket_power'):
                    data['power_draw'] = float(power_info.average_socket_power)
                if hasattr(power_info, 'power_limit'):
                    data['power_limit'] = float(power_info.power_limit)
        except Exception:
            pass

        # Power cap (also used as fallback for power_limit)
        try:
            cap = amdsmi.amdsmi_get_power_cap_info(handle)
            if cap:
                if 'power_limit' not in data and hasattr(cap, 'power_cap'):
                    data['power_limit'] = float(cap.power_cap)
                if hasattr(cap, 'min_power_cap'):
                    data['power_limit_min'] = float(cap.min_power_cap)
                if hasattr(cap, 'max_power_cap'):
                    data['power_limit_max'] = float(cap.max_power_cap)
        except Exception:
            pass

        # Energy consumption (cumulative)
        try:
            energy = amdsmi.amdsmi_get_energy_count(handle)
            if energy is not None:
                if hasattr(energy, 'energy_accumulator') and hasattr(energy, 'counter_resolution'):
                    # Convert to kJ and Wh to match NVIDIA field names
                    micro_joules = float(energy.energy_accumulator) * float(energy.counter_resolution)
                    data['energy_consumption'] = micro_joules / 1e9  # kJ
                    data['energy_consumption_wh'] = micro_joules / 3.6e9  # Wh
                elif isinstance(energy, (int, float)):
                    # Some versions return micro-joules directly
                    data['energy_consumption'] = float(energy) / 1e9
                    data['energy_consumption_wh'] = float(energy) / 3.6e9
        except Exception:
            pass

    def _add_fan_speeds(self, handle, data):
        # Try to get fan speed as percentage
        try:
            fan_speed = amdsmi.amdsmi_get_gpu_fan_speed(handle, 0)
            fan_max = amdsmi.amdsmi_get_gpu_fan_rpms(handle, 0)
            if fan_speed is not None and fan_max is not None and fan_max > 0:
                data['fan_speed'] = float(fan_speed / fan_max * 100)
            elif fan_speed is not None:
                data['fan_speed'] = float(fan_speed)
        except Exception:
            pass

        # Multiple fans
        if hasattr(amdsmi, 'amdsmi_get_gpu_fan_speed'):
            fans = []
            for fan_idx in range(4):  # Check up to 4 fans
                try:
                    speed = amdsmi.amdsmi_get_gpu_fan_speed(handle, fan_idx)
                    max_speed = amdsmi.amdsmi_get_gpu_fan_rpms(handle, fan_idx)
                    if speed is not None and max_speed is not None and max_speed > 0:
                        fans.append(float(speed / max_speed * 100))
                    elif speed is not None:
                        fans.append(float(speed))
                    else:
                        break
                except Exception:
                    break
            if fans:
                data['fan_speeds'] = fans
                if 'fan_speed' not in data:
                    data['fan_speed'] = fans[0]

    def _add_throttling(self, handle, data):
        """Throttle/violation status"""
        try:
            if not hasattr(amdsmi, 'amdsmi_get_violation_status'):
                return
            violation = amdsmi.amdsmi_get_violation_status(handle)
            if violation is None:
                return

            reasons = []
            violation_map = [
                ('prochot', 'PROCHOT'),
                ('ppt', 'PPT Limit'),
                ('socket_thermal', 'Socket Thermal'),
                ('vr_thermal', 'VR Thermal'),
                ('hbm_thermal', 'HBM Thermal'),
            ]
            for attr, label in violation_map:
                if hasattr(violation, attr):
                    val = getattr(violation, attr)
                    if val and val > 0:
                        reasons.append(label)

            data['throttle_reasons'] = ', '.join(reasons) if reasons else 'None'
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Clocks
    # ------------------------------------------------------------------

    def _add_clocks(self, handle, data):
        """Clock speed metrics"""
        clock_map = [
            ('clock_graphics', amdsmi.AmdSmiClkType.GFX),
            ('clock_memory', amdsmi.AmdSmiClkType.MEM),
        ]

        # SOC clock (AMD equivalent of SM clock)
        if hasattr(amdsmi, 'AmdSmiClkType') and hasattr(amdsmi.AmdSmiClkType, 'SOC'):
            clock_map.append(('clock_sm', amdsmi.AmdSmiClkType.SOC))

        # Video clocks (encode/decode engines)
        if hasattr(amdsmi.AmdSmiClkType, 'VCLK0'):
            clock_map.append(('clock_video', amdsmi.AmdSmiClkType.VCLK0))

        for key, clk_type in clock_map:
            try:
                clk_info = amdsmi.amdsmi_get_clock_info(handle, clk_type)
                if clk_info:
                    if hasattr(clk_info, 'clk'):
                        data[key] = float(clk_info.clk)
                    elif hasattr(clk_info, 'cur_clk'):
                        data[key] = float(clk_info.cur_clk)
                    if hasattr(clk_info, 'max_clk'):
                        data[f'{key}_max'] = float(clk_info.max_clk)
                    if hasattr(clk_info, 'min_clk'):
                        data[f'{key}_min'] = float(clk_info.min_clk)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    def _add_connectivity(self, handle, data):
        """PCIe and interconnect metrics"""
        try:
            pci_info = amdsmi.amdsmi_get_gpu_pci_info(handle)
            if pci_info and hasattr(pci_info, 'pci_bus'):
                data['pci_bus_id'] = str(pci_info.pci_bus)
        except Exception:
            pass

        # PCIe link info
        try:
            link_info = amdsmi.amdsmi_get_pcie_info(handle)
            if link_info:
                if hasattr(link_info, 'pcie_metric'):
                    metric = link_info.pcie_metric
                    if hasattr(metric, 'pcie_speed'):
                        data['pcie_gen'] = str(metric.pcie_speed)
                    if hasattr(metric, 'pcie_width'):
                        data['pcie_width'] = str(metric.pcie_width)
                if hasattr(link_info, 'pcie_static'):
                    static = link_info.pcie_static
                    if hasattr(static, 'max_pcie_speed'):
                        data['pcie_gen_max'] = str(static.max_pcie_speed)
                    if hasattr(static, 'max_pcie_width'):
                        data['pcie_width_max'] = str(static.max_pcie_width)
        except Exception:
            pass

        # PCIe throughput
        try:
            if hasattr(amdsmi, 'amdsmi_get_gpu_pci_throughput'):
                throughput = amdsmi.amdsmi_get_gpu_pci_throughput(handle)
                if throughput:
                    if hasattr(throughput, 'sent'):
                        data['pcie_tx_throughput'] = float(throughput.sent)
                    if hasattr(throughput, 'received'):
                        data['pcie_rx_throughput'] = float(throughput.received)
        except Exception:
            pass

        # XGMI/Infinity Fabric links (AMD equivalent of NVLink)
        self._add_xgmi(handle, data)

    def _add_xgmi(self, handle, data):
        """XGMI/Infinity Fabric link info"""
        if not hasattr(amdsmi, 'amdsmi_get_xgmi_info'):
            return
        try:
            xgmi_info = amdsmi.amdsmi_get_xgmi_info(handle)
            if xgmi_info is None:
                return
            # Map to the same structure as NVLink for frontend compatibility
            links = []
            active_count = 0
            if hasattr(xgmi_info, 'xgmi_lanes'):
                links.append({
                    'id': 0,
                    'active': True,
                    'lanes': int(xgmi_info.xgmi_lanes) if xgmi_info.xgmi_lanes else 0,
                })
                active_count = 1
            if links:
                data['nvlink_links'] = links
                data['nvlink_active_count'] = active_count
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Media engines
    # ------------------------------------------------------------------

    def _add_media_engines(self, handle, data):
        """Encoder/decoder utilization via VCN activity and VCLK/DCLK"""
        # mm_activity from _add_performance already populates encoder_utilization
        # Here we add decoder utilization if available from separate clock activity

        # Try to get VCN/decoder utilization from utilization counters
        try:
            if hasattr(amdsmi, 'amdsmi_get_utilization_count'):
                util_counters = amdsmi.amdsmi_get_utilization_count(handle)
                if util_counters:
                    for counter in util_counters:
                        ctype = getattr(counter, 'type', None)
                        val = getattr(counter, 'value', None)
                        if val is None:
                            continue
                        ctype_str = str(ctype) if ctype else ''
                        if 'DECODER' in ctype_str.upper():
                            data['decoder_utilization'] = float(val)
                        elif 'GFX' in ctype_str.upper() and 'utilization' not in data:
                            data['utilization'] = float(val)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Health status
    # ------------------------------------------------------------------

    def _add_health_status(self, handle, data):
        """ECC and health metrics"""
        # ECC status
        try:
            if hasattr(amdsmi, 'amdsmi_get_gpu_ecc_enabled'):
                ecc_enabled = amdsmi.amdsmi_get_gpu_ecc_enabled(handle)
                if ecc_enabled:
                    data['ecc_enabled'] = True
        except Exception:
            pass

        # ECC error counts
        try:
            if hasattr(amdsmi, 'amdsmi_get_gpu_total_ecc_count'):
                ecc = amdsmi.amdsmi_get_gpu_total_ecc_count(handle)
                if ecc is not None:
                    if hasattr(ecc, 'correctable_count'):
                        data['ecc_errors_corrected'] = int(ecc.correctable_count)
                    if hasattr(ecc, 'uncorrectable_count'):
                        data['ecc_errors_uncorrected'] = int(ecc.uncorrectable_count)
        except Exception:
            pass

        # Retired/bad pages
        try:
            if hasattr(amdsmi, 'amdsmi_get_gpu_bad_page_info'):
                bad_pages = amdsmi.amdsmi_get_gpu_bad_page_info(handle)
                if bad_pages is not None:
                    if isinstance(bad_pages, (list, tuple)):
                        data['retired_pages'] = len(bad_pages)
                    elif isinstance(bad_pages, int):
                        data['retired_pages'] = bad_pages
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Advanced
    # ------------------------------------------------------------------

    def _add_advanced(self, handle, data):
        """Additional metrics: RAS, voltage, overdrive"""
        # RAS feature info
        try:
            if hasattr(amdsmi, 'amdsmi_get_gpu_ras_feature_info'):
                ras = amdsmi.amdsmi_get_gpu_ras_feature_info(handle)
                if ras and hasattr(ras, 'ras_eeprom_version'):
                    data['ras_version'] = str(ras.ras_eeprom_version)
        except Exception:
            pass

        # Overdrive level
        try:
            if hasattr(amdsmi, 'amdsmi_get_gpu_overdrive_level'):
                od = amdsmi.amdsmi_get_gpu_overdrive_level(handle)
                if od is not None:
                    data['overdrive_level'] = int(od)
        except Exception:
            pass

        try:
            if hasattr(amdsmi, 'amdsmi_get_gpu_mem_overdrive_level'):
                mod = amdsmi.amdsmi_get_gpu_mem_overdrive_level(handle)
                if mod is not None:
                    data['mem_overdrive_level'] = int(mod)
        except Exception:
            pass
