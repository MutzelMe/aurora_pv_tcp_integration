"""Support for ABB Aurora Solar Inverters via Waveshare RS485-to-Ethernet adapter."""
import asyncio
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed
import logging
import socket
from aurorapy.client import AuroraTCPClient
import time

from .const import DOMAIN, CONF_SLAVE_ID, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Mapping for human-readable texts
ALARM_MESSAGES = {
    0x0000: "No Alarms",
    0x0001: "Overload",
    0x0002: "Grid Voltage Too High",
    0x0004: "Insulation Fault",
    0x0008: "Temperature Too High",
    0x0010: "Grid Frequency Out of Tolerance",
}

STATUS_MESSAGES = {
    0x00: "Off",
    0x01: "Ready",
    0x02: "On",
    0x03: "Error",
    0x04: "Maintenance",
}

FAULT_MESSAGES = {
    0x0000: "No Fault",
    0x0001: "Short Circuit",
    0x0002: "Communication Error",
}

# --- Module-level sensor configuration (single source of truth) ---
#
# Each row: (sensor_type, unit, factor, precision, is_string, text_mapping,
#            device_class, state_class, read_spec)
#
# read_spec is one of:
#   ("measure", <register>)       → client.measure(register)
#   ("energy",  <period_code>)    → client.cumulated_energy(period_code)
#   ("string",  "<method_name>")  → getattr(client, method_name)()
#   None                          → register unknown / not supported
#
# cumulated_energy period codes: 0=daily, 1=weekly, 3=monthly, 4=yearly, 5=total

_DC = SensorDeviceClass   # short aliases – only used inside this list
_SC = SensorStateClass
_M  = "measure"
_E  = "energy"
_S  = "string"

SENSOR_DEFINITIONS: list = [
    # sensor_type                       unit       fac  prec  str    text_map          device_class        state_class           read_spec                   icon
    # ── Power ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_GRID_POWER",                 "W",        1,   2,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M,  3 ),  "mdi:solar-power"             ),
    ("DSP_DC_POWER",                   "W",        1,   0,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M, 12 ),  "mdi:solar-power"             ),
    ("DSP_MPPT_POWER",                 "W",        1,   0,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M, 16 ),  "mdi:solar-power"             ),
    ("DSP_PIN1",                       "W",        1,   1,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M,  8 ),  "mdi:solar-power"             ),
    ("DSP_PIN2",                       "W",        1,   1,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M,  9 ),  "mdi:solar-power"             ),
    ("DSP_POWER_PEAK",                 "W",        1,   0,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M, 34 ),  "mdi:solar-power"             ),
    ("DSP_POWER_PEAK_TODAY",           "W",        1,   0,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M, 35 ),  "mdi:solar-power"             ),
    ("DSP_POWER_SATURATION_LIMIT",     "W",        1,   0,  False, None,            _DC.POWER,          _SC.MEASUREMENT,      (_M, 58 ),  "mdi:solar-power"             ),
    # ── Energy ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_DAILY_ENERGY",               "Wh",       1,   0,  False, None,            _DC.ENERGY,         _SC.TOTAL,            (_E,  0 ),  "mdi:solar-power-variant"     ),
    ("DSP_WEEKLY_ENERGY",              "Wh",       1,   0,  False, None,            _DC.ENERGY,         _SC.TOTAL,            (_E,  1 ),  "mdi:solar-power-variant"     ),
    ("DSP_MONTHLY_ENERGY",             "Wh",       1,   0,  False, None,            _DC.ENERGY,         _SC.TOTAL,            (_E,  3 ),  "mdi:solar-power-variant"     ),
    ("DSP_YEARLY_ENERGY",              "Wh",       1,   0,  False, None,            _DC.ENERGY,         _SC.TOTAL,            (_E,  4 ),  "mdi:solar-power-variant"     ),
    ("DSP_TOTAL_ENERGY",               "kWh",      0.1, 2,  False, None,            _DC.ENERGY,         _SC.TOTAL_INCREASING, (_E,  5 ),  "mdi:counter"                 ),
    # ── Grid AC ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_GRID_VOLTAGE",               "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M,  1 ),  "mdi:flash"                   ),
    ("DSP_GRID_CURRENT",               "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M,  2 ),  "mdi:current-ac"              ),
    ("DSP_GRID_FREQUENCY",             "Hz",       1,   1,  False, None,            _DC.FREQUENCY,      _SC.MEASUREMENT,      (_M,  4 ),  "mdi:sine-wave"               ),
    ("DSP_PF",                         "",         1,   2,  False, None,            _DC.POWER_FACTOR,   _SC.MEASUREMENT,      None,       "mdi:angle-acute"             ),  # add (_M, <reg>) once register is verified
    ("DSP_AVERAGE_GRID_VOLTAGE",       "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 32 ),  "mdi:flash"                   ),
    ("DSP_GRID_VOLTAGE_NEUTRAL",       "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 36 ),  "mdi:flash"                   ),
    ("DSP_GRID_VOLTAGE_NEUTRAL_PHASE", "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 38 ),  "mdi:flash"                   ),
    # ── Three-phase ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_GRID_VOLTAGE_PHASE_R",       "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 61 ),  "mdi:flash"                   ),
    ("DSP_GRID_VOLTAGE_PHASE_S",       "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 62 ),  "mdi:flash"                   ),
    ("DSP_GRID_VOLTAGE_PHASE_T",       "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 63 ),  "mdi:flash"                   ),
    ("DSP_GRID_CURRENT_PHASE_R",       "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M, 39 ),  "mdi:current-ac"              ),
    ("DSP_GRID_CURRENT_PHASE_S",       "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M, 40 ),  "mdi:current-ac"              ),
    ("DSP_GRID_CURRENT_PHASE_T",       "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M, 41 ),  "mdi:current-ac"              ),
    ("DSP_FREQUENCY_PHASE_R",          "Hz",       1,   1,  False, None,            _DC.FREQUENCY,      _SC.MEASUREMENT,      (_M, 42 ),  "mdi:sine-wave"               ),
    ("DSP_FREQUENCY_PHASE_S",          "Hz",       1,   1,  False, None,            _DC.FREQUENCY,      _SC.MEASUREMENT,      (_M, 43 ),  "mdi:sine-wave"               ),
    ("DSP_FREQUENCY_PHASE_T",          "Hz",       1,   1,  False, None,            _DC.FREQUENCY,      _SC.MEASUREMENT,      (_M, 44 ),  "mdi:sine-wave"               ),
    # ── DC / Bulk voltages ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_DC_VOLTAGE",                 "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 23 ),  "mdi:flash-outline"           ),
    ("DSP_DC_CURRENT",                 "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M, 25 ),  "mdi:current-dc"              ),
    ("DSP_INPUT_2_VOLTAGE",            "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 26 ),  "mdi:flash-outline"           ),
    ("DSP_INPUT_2_CURRENT",            "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M, 27 ),  "mdi:current-dc"              ),
    ("DSP_VBULK",                      "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M,  5 ),  "mdi:flash-outline"           ),
    ("DSP_VBULK_PLUS",                 "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 45 ),  "mdi:flash-outline"           ),
    ("DSP_VBULK_MINUS",                "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 46 ),  "mdi:flash-outline"           ),
    ("DSP_VBULK_MID",                  "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 33 ),  "mdi:flash-outline"           ),
    ("DSP_VBULK_DC_DC",                "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 31 ),  "mdi:flash-outline"           ),
    ("DSP_VPANEL_MICRO",               "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 60 ),  "mdi:flash-outline"           ),
    ("DSP_GRID_VOLTAGE_DC_DC",         "V",        1,   1,  False, None,            _DC.VOLTAGE,        _SC.MEASUREMENT,      (_M, 28 ),  "mdi:flash"                   ),
    ("DSP_GRID_FREQUENCY_DC_DC",       "Hz",       1,   1,  False, None,            _DC.FREQUENCY,      _SC.MEASUREMENT,      (_M, 29 ),  "mdi:sine-wave"               ),
    ("DSP_WIND_GENERATOR_FREQUENCY",   "Hz",       1,   1,  False, None,            _DC.FREQUENCY,      _SC.MEASUREMENT,      (_M, 37 ),  "mdi:wind-turbine"            ),
    ("DSP_ILEAK_DC_DC",                "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M,  6 ),  "mdi:alert-circle"            ),
    ("DSP_ILEAK_INVERTER",             "A",        1,   1,  False, None,            _DC.CURRENT,        _SC.MEASUREMENT,      (_M,  7 ),  "mdi:alert-circle"            ),
    # ── Temperature ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_TEMPERATURE",                "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 21 ),  "mdi:thermometer"             ),
    ("DSP_RADIATOR_TEMP",              "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 22 ),  "mdi:thermometer"             ),
    ("DSP_AMBIENT_TEMP",               "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 15 ),  "mdi:thermometer"             ),
    ("DSP_SUPERVISOR_TEMPERATURE",     "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 47 ),  "mdi:thermometer"             ),
    ("DSP_ALIM_TEMPERATURE",           "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 48 ),  "mdi:thermometer"             ),
    ("DSP_HEAT_SINK_TEMPERATURE",      "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 49 ),  "mdi:thermometer"             ),
    ("DSP_TEMPERATURE_1",              "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 50 ),  "mdi:thermometer"             ),
    ("DSP_TEMPERATURE_2",              "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 51 ),  "mdi:thermometer"             ),
    ("DSP_TEMPERATURE_3",              "\u00b0C",  1,   1,  False, None,            _DC.TEMPERATURE,    _SC.MEASUREMENT,      (_M, 52 ),  "mdi:thermometer"             ),
    # ── Fan speeds ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_FAN_1_SPEED",                "rpm",      1,   0,  False, None,            None,               _SC.MEASUREMENT,      (_M, 53 ),  "mdi:fan"                     ),
    ("DSP_FAN_2_SPEED",                "rpm",      1,   0,  False, None,            None,               _SC.MEASUREMENT,      (_M, 54 ),  "mdi:fan"                     ),
    ("DSP_FAN_3_SPEED",                "rpm",      1,   0,  False, None,            None,               _SC.MEASUREMENT,      (_M, 55 ),  "mdi:fan"                     ),
    ("DSP_FAN_4_SPEED",                "rpm",      1,   0,  False, None,            None,               _SC.MEASUREMENT,      (_M, 56 ),  "mdi:fan"                     ),
    ("DSP_FAN_5_SPEED",                "rpm",      1,   0,  False, None,            None,               _SC.MEASUREMENT,      (_M, 57 ),  "mdi:fan"                     ),
    # ── Diagnostics ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_ISOLATION",                  "k\u03a9", 1,   0,  False, None,            None,               _SC.MEASUREMENT,      (_M, 30 ),  "mdi:resistor"                ),
    ("DSP_OPERATING_HOURS",            "h",        1,   0,  False, None,            _DC.DURATION,       _SC.TOTAL_INCREASING, (_M, 18 ),  "mdi:clock"                   ),
    ("DSP_RIFERIMENTO_ANELLO_BULK",    "",         1,   1,  False, None,            None,               _SC.MEASUREMENT,      (_M, 59 ),  "mdi:gauge"                   ),
    ("DSP_ALARMS",                     "",         1,   2,  False, ALARM_MESSAGES,  None,               None,                 (_M, 10 ),  "mdi:alert"                   ),
    ("DSP_FAULT_CODE",                 "",         1,   2,  False, FAULT_MESSAGES,  None,               None,                 (_M, 11 ),  "mdi:alert-circle"            ),
    ("DSP_STATUS",                     "",         1,   2,  False, STATUS_MESSAGES, None,               None,                 (_M, 14 ),  "mdi:information"             ),
    ("DSP_EVENTS",                     "",         1,   2,  False, None,            None,               None,                 (_M, 13 ),  "mdi:calendar-alert"          ),
    ("DSP_LAST_ERROR",                 "",         1,   2,  False, None,            None,               None,                 (_M, 20 ),  "mdi:alert-circle-outline"    ),
    # ── Device info (strings) ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    ("DSP_SERIAL_NUMBER",              "",         1,   2,  True,  None,            None,               None,                 (_S, "serial_number"),  "mdi:identifier"          ),
    ("DSP_MODEL",                      "",         1,   2,  True,  None,            None,               None,                 (_S, "version"       ),  "mdi:tag"                 ),
    ("DSP_VERSION",                    "",         1,   2,  True,  None,            None,               None,                 (_S, "version"       ),  "mdi:information-outline" ),
]
del _DC, _SC, _M, _E, _S  # clean up module-level aliases

class AuroraConnectionPool:
    """Connection pool for Aurora TCP clients to reduce connection overhead."""
    
    _instances = {}  # {(host, port, slave_id): AuroraConnectionPool}
    
    def __new__(cls, host, port, slave_id, timeout=20):
        """Singleton pattern - one pool per inverter configuration."""
        key = (host, port, slave_id)
        if key not in cls._instances:
            cls._instances[key] = super().__new__(cls)
        return cls._instances[key]

    def __init__(self, host, port, slave_id, timeout=20):
        """Initialize connection pool. Guard prevents reset on singleton reuse."""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.timeout = timeout
        self._connection = None
        self._lock = asyncio.Lock()
        self._last_used = 0
    
    async def get_connection(self):
        """Get or create a connection with health check and proper timeout handling."""
        now = time.time()
        
        # Check if existing connection is still valid
        if self._connection and (now - self._last_used) < 300:  # 5 minute timeout
            try:
                # Health check: wrap blocking TCP call in executor to prevent HA event-loop freeze
                loop = asyncio.get_running_loop()
                async with asyncio.timeout(3.0):
                    await loop.run_in_executor(None, lambda: self._connection.measure(1))
                self._last_used = now
                return self._connection
            except asyncio.TimeoutError:
                _LOGGER.warning(
                    "Health check timeout for %s:%s - stale connection, reconnecting",
                    self.host, self.port
                )
                await self._close_connection()
            except (socket.error, ConnectionResetError) as e:
                _LOGGER.warning(f"Socket error detected in health check: {e}")
                await self._close_connection()
            except Exception as e:
                _LOGGER.debug(f"Health check failed: {e}")
                await self._close_connection()
        
        # Create new connection with proper lock handling and timeout
        try:
            # Use asyncio.wait_for with the lock context manager
            async with asyncio.timeout(5.0):
                async with self._lock:
                    if self._connection is None:
                        try:
                            # Create connection with timeout
                            self._connection = AuroraTCPClient(
                                ip=self.host,
                                port=self.port,
                                address=self.slave_id,
                                timeout=min(self.timeout, 5)  # MAX 5 seconds timeout
                            )
                            # Connect with timeout - use executor for blocking call
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(
                                None,
                                lambda: self._connection.connect()
                            )
                            self._last_used = now
                            _LOGGER.debug(f"New connection established to {self.host}:{self.port}")
                        except (socket.error, ConnectionResetError) as e:
                            _LOGGER.error(f"Socket connection failed for {self.host}:{self.port} (slave {self.slave_id}): {e}")
                            await self._close_connection()
                            raise
                        except Exception as e:
                            _LOGGER.error(f"Connection failed for {self.host}:{self.port} (slave {self.slave_id}): {e}")
                            await self._close_connection()
                            raise
        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout acquiring connection for {self.host}:{self.port} (slave {self.slave_id})")
            raise
        
        return self._connection
    
    async def _close_connection(self):
        """Close current connection safely."""
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
            self._connection = None

def _fetch_all_sync(client):
    """Read all sensor values synchronously in a single TCP session (runs in executor)."""
    data = {}
    for sensor_type, _u, _f, _p, _s, _m, _dc, _sc, read_spec, _icon in SENSOR_DEFINITIONS:
        try:
            if read_spec is None:
                data[sensor_type] = None
            elif read_spec[0] == "measure":
                data[sensor_type] = client.measure(read_spec[1])
            elif read_spec[0] == "energy":
                data[sensor_type] = client.cumulated_energy(read_spec[1])
            elif read_spec[0] == "string":
                data[sensor_type] = getattr(client, read_spec[1])()
        except Exception as exc:
            _LOGGER.debug("Could not read %s: %s", sensor_type, exc)
            data[sensor_type] = None
    return data


class AuroraDataUpdateCoordinator(DataUpdateCoordinator):
    """Reads all sensor registers in one TCP session per poll cycle."""

    def __init__(self, hass, host, port, slave_id, scan_interval):
        super().__init__(
            hass,
            _LOGGER,
            name=f"Aurora {host}:{port} slave {slave_id}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self.slave_id = slave_id

    async def _async_update_data(self):
        """Fetch all sensor values in one executor call (single TCP session)."""
        pool = AuroraConnectionPool(self.host, self.port, self.slave_id)
        try:
            async with asyncio.timeout(15.0):
                client = await pool.get_connection()
        except asyncio.TimeoutError as exc:
            raise UpdateFailed(
                f"Connection timeout for {self.host}:{self.port}"
            ) from exc
        except Exception as exc:
            raise UpdateFailed(
                f"Cannot connect to {self.host}:{self.port}: {exc}"
            ) from exc

        loop = asyncio.get_running_loop()
        try:
            # All reads in one executor block – single TCP session, no event-loop blocking
            async with asyncio.timeout(30.0):
                data = await loop.run_in_executor(None, _fetch_all_sync, client)
        except asyncio.TimeoutError as exc:
            await pool._close_connection()
            raise UpdateFailed(
                f"Timed out reading all sensors from {self.host}:{self.port}"
            ) from exc
        except Exception as exc:
            await pool._close_connection()
            raise UpdateFailed(f"Error reading sensor data: {exc}") from exc

        return data

    async def async_close(self) -> None:
        """Close the TCP connection pool (called on integration unload)."""
        pool = AuroraConnectionPool(self.host, self.port, self.slave_id)
        await pool._close_connection()
        AuroraConnectionPool._instances.pop((self.host, self.port, self.slave_id), None)


class AuroraSensorBase(CoordinatorEntity, SensorEntity):
    """A single ABB Aurora sensor entity backed by the shared coordinator."""

    def __init__(self, coordinator, inverter_name, sensor_type, unit, factor=1, precision=2,
                 is_string=False, text_mapping=None, device_class=None, state_class=None,
                 icon="mdi:help"):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._factor = factor
        self._precision = precision
        self._is_string = is_string
        self._text_mapping = text_mapping
        self._inverter_name = inverter_name
        sensor_type_clean = sensor_type[4:].replace('_', ' ').title()
        self._attr_name = f"{inverter_name} {sensor_type_clean}"
        sensor_key = sensor_type.lower().replace("dsp_", "")
        self._attr_unique_id = f"aurora_{coordinator.slave_id}_{sensor_key}"
        self._attr_native_unit_of_measurement = unit if not is_string else None
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon

    @property
    def device_info(self):
        """Group all sensors under one HA device per inverter."""
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.host}_{self.coordinator.slave_id}")},
            "name": self._inverter_name,
            "manufacturer": "ABB / Power-One",
            "model": "Aurora PVI Inverter",
        }

    @property
    def native_value(self):
        """Return current sensor value from coordinator data."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._sensor_type)
        if raw is None:
            return None
        if self._text_mapping:
            return self._text_mapping.get(int(raw), str(int(raw)))
        if self._is_string:
            return raw
        return round(raw * self._factor, self._precision)


def _create_sensors(coordinator, name):
    """Create all sensor entities for one inverter from SENSOR_DEFINITIONS."""
    return [
        AuroraSensorBase(
            coordinator, name,
            sensor_type, unit, factor, precision, is_string, text_mapping,
            device_class, state_class, icon,
        )
        for sensor_type, unit, factor, precision, is_string, text_mapping,
            device_class, state_class, _read_spec, icon
        in SENSOR_DEFINITIONS
    ]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Aurora Solar sensors from a config entry."""
    data = config_entry.data
    opts = config_entry.options
    # options override data so changes via Options-Flow take effect after reload
    slave_id = opts.get(CONF_SLAVE_ID, data[CONF_SLAVE_ID])
    scan_interval = opts.get(CONF_SCAN_INTERVAL, data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    name = data.get("name", f"Inverter {slave_id}")
    coordinator = AuroraDataUpdateCoordinator(
        hass,
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        slave_id=slave_id,
        scan_interval=scan_interval,
    )
    # Initial refresh – sensors show unavailable if inverter is offline at startup
    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator
    async_add_entities(_create_sensors(coordinator, name))
    config_entry.async_on_unload(
        config_entry.add_update_listener(
            lambda hass, entry: hass.config_entries.async_reload(entry.entry_id)
        )
    )