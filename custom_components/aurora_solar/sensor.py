"""Support for ABB Aurora Solar Inverters via Waveshare RS485-to-Ethernet adapter."""
import asyncio
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_HOST, CONF_PORT
import logging
from aurorapy.client import AuroraTCPClient, AuroraError
import time

from .const import DOMAIN, CONF_SLAVE_ID, CONF_SCAN_INTERVAL

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

class AuroraConnectionPool:
    """Connection pool for Aurora TCP clients to reduce connection overhead."""
    
    _instances = {}  # {(host, port, slave_id): AuroraConnectionPool}
    
    def __new__(cls, host, port, slave_id, timeout=20):
        """Singleton pattern - one pool per inverter configuration."""
        key = (host, port, slave_id)
        if key not in cls._instances:
            cls._instances[key] = super().__new__(cls)
            cls._instances[key].__init__(host, port, slave_id, timeout)
        return cls._instances[key]
    
    def __init__(self, host, port, slave_id, timeout=20):
        """Initialize connection pool."""
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.timeout = timeout
        self._connection = None
        self._lock = asyncio.Lock()
        self._last_used = 0
    
    async def get_connection(self):
        """Get or create a connection with health check."""
        now = time.time()
        
        # Check if existing connection is still valid
        if self._connection and (now - self._last_used) < 300:  # 5 minute timeout
            try:
                # Simple health check - try to read a known register
                test_value = self._connection.measure(1)  # Grid voltage
                self._last_used = now
                return self._connection
            except Exception:
                await self._close_connection()
        
        # Create new connection
        async with self._lock:
            if self._connection is None:
                self._connection = AuroraTCPClient(
                    ip=self.host,
                    port=self.port,
                    address=self.slave_id,
                    timeout=self.timeout
                )
                self._connection.connect()
                self._last_used = now
        
        return self._connection
    
    async def _close_connection(self):
        """Close current connection safely."""
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
            self._connection = None

def measure_with_retry(client, code, retries=2):
    """Attempts to read a value with retries on timeout."""
    for attempt in range(retries + 1):
        try:
            value = client.measure(code)
            if (abs(value) < 1e-30 and value != 0.0) or abs(value) > 1e10:
                return None
            return value
        except AuroraError as e:
            if "Reading Timeout" in str(e) and attempt < retries:
                time.sleep(0.3)
                continue
            return None
    return None

class AuroraSensorBase(SensorEntity):
    """Base class for all ABB Aurora sensors."""

    def __init__(self, host, port, slave_id, name, sensor_type, unit, factor=1, precision=2, is_string=False, text_mapping=None, scan_interval=60):
        """Initialize the sensor."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._scan_interval = scan_interval
        """self._name = f"{name} {sensor_type.split('_')[-1].title()}"""
        # Use the provided name (short name from config flow) + clean sensor type name
        # Extract the meaningful part of the sensor type and clean it up
        sensor_type_clean = sensor_type.split('_')[-1].replace('_', ' ').title()
        # Remove redundant parts like "Dsp" and create clean names
        sensor_type_clean = sensor_type_clean.replace("Dsp", "").strip()
        
        # Create clean friendly name: "<Short Name> <Sensor Type>"
        self._name = f"{name} {sensor_type_clean}"
        self._attr_friendly_name = f"{name} {sensor_type_clean}"
        self._sensor_type = sensor_type
        self._unit = unit
        self._factor = factor
        self._precision = precision
        self._is_string = is_string
        self._text_mapping = text_mapping
        self._state = None
        self._attr_native_unit_of_measurement = unit if not is_string else None
        # Create unique_id - keep original format for backward compatibility
        # but ensure it's lowercase and consistent
        sensor_key = sensor_type.lower().replace("dsp_", "")
        self._attr_unique_id = f"aurora_{slave_id}_{sensor_key}"
        self._attr_icon = self._get_icon_for_sensor_type(sensor_type)

    def _get_icon_for_sensor_type(self, sensor_type):
        """Returns the appropriate icon for the sensor type."""
        icon_mapping = {
            "DSP_GRID_POWER": "mdi:solar-power",
            "DSP_DC_POWER": "mdi:solar-power",
            "DSP_MPPT_POWER": "mdi:solar-power",
            "DSP_POWER_PEAK": "mdi:solar-power",
            "DSP_PIN1": "mdi:solar-power",
            "DSP_PIN2": "mdi:solar-power",
            "DSP_POWER_PEAK_TODAY": "mdi:solar-power",   
            "DSP_DAILY_ENERGY": "mdi:solar-power-variant",
            "DSP_WEEKLY_ENERGY": "mdi:solar-power-variant",
            "DSP_MONTHLY_ENERGY": "mdi:solar-power-variant",
            "DSP_YEARLY_ENERGY": "mdi:solar-power-variant",
            "DSP_TOTAL_ENERGY": "mdi:counter",
            "DSP_GRID_VOLTAGE": "mdi:flash",
            "DSP_AVERAGE_GRID_VOLTAGE": "mdi:flash",
            "DSP_GRID_CURRENT": "mdi:current-ac",
            "DSP_DC_VOLTAGE": "mdi:flash-outline",
            "DSP_DC_CURRENT": "mdi:current-dc",
            "DSP_TEMPERATURE": "mdi:thermometer",
            "DSP_RADIATOR_TEMP": "mdi:thermometer",
            "DSP_AMBIENT_TEMP": "mdi:thermometer",
            "DSP_GRID_FREQUENCY": "mdi:sine-wave",
            "DSP_PF": "mdi:angle-acute",
            "DSP_ALARMS": "mdi:alert",
            "DSP_STATUS": "mdi:information",
            "DSP_FAULT_CODE": "mdi:alert-circle",
            "DSP_EVENTS": "mdi:calendar-alert",
            "DSP_LAST_ERROR": "mdi:alert-circle-outline",
            "DSP_SERIAL_NUMBER": "mdi:identifier",
            "DSP_MODEL": "mdi:tag",
            "DSP_VERSION": "mdi:information-outline",
            "DSP_ISOLATION": "mdi:resistor",
            "DSP_OPERATING_HOURS": "mdi:clock",
            "DSP_INPUT_2_VOLTAGE": "mdi:flash-outline",
            "DSP_INPUT_2_CURRENT": "mdi:current-dc",
            "DSP_INPUT_1_VOLTAGE": "mdi:flash-outline",
            "DSP_INPUT_1_CURRENT": "mdi:current-dc",
            "DSP_ILEAK_INVERTER": "mdi:alert-circle",
            "DSP_GRID_VOLTAGE_DC_DC": "mdi:flash",
            "DSP_GRID_FREQUENCY_DC_DC": "mdi:sine-wave",
            "DSP_VBULK_MID": "mdi:flash-outline",
            "DSP_GRID_VOLTAGE_NEUTRAL": "mdi:flash",
            "DSP_GRID_VOLTAGE_NEUTRAL_PHASE": "mdi:flash",
            "DSP_WIND_GENERATOR_FREQUENCY": "mdi:wind-turbine",
        }
        return icon_mapping.get(sensor_type, "mdi:help")


    @property
    def state(self):
        """Current state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {"scan_interval": self._scan_interval}

    def update(self):
        """Synchronous update method for backward compatibility."""
        # Run async_update synchronously for compatibility
        try:
            asyncio.run(self.async_update())
        except RuntimeError:
            # Handle case where asyncio.run() can't be called (e.g., already in event loop)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task if we're already in an event loop
                loop.create_task(self.async_update())
            else:
                asyncio.run(self.async_update())

    async def async_update(self):
        """Update the sensor data using connection pooling."""
        try:
            # Use connection pool instead of creating new client each time
            pool = AuroraConnectionPool(self._host, self._port, self._slave_id)
            client = await pool.get_connection()

            if self._sensor_type == "DSP_GRID_POWER":
                value = measure_with_retry(client, 3)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_DAILY_ENERGY":
                self._state = round(client.cumulated_energy(0), self._precision)
            elif self._sensor_type == "DSP_WEEKLY_ENERGY":
                self._state = round(client.cumulated_energy(1), self._precision)
            elif self._sensor_type == "DSP_MONTHLY_ENERGY":
                self._state = round(client.cumulated_energy(3), self._precision)
            elif self._sensor_type == "DSP_YEARLY_ENERGY":
                self._state = round(client.cumulated_energy(4), self._precision)
            elif self._sensor_type == "DSP_TOTAL_ENERGY":
                self._state = round(client.cumulated_energy(5), self._precision)
            elif self._sensor_type == "DSP_GRID_VOLTAGE":
                value = measure_with_retry(client, 1)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_CURRENT":
                value = measure_with_retry(client, 2)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_FREQUENCY":
                value = measure_with_retry(client, 4)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_PF":
                value = measure_with_retry(client, 9)
                self._state = round(value * 0.01, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_DC_VOLTAGE":
                value = measure_with_retry(client, 23)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_DC_CURRENT":
                value = measure_with_retry(client, 25)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_DC_POWER":
                value = measure_with_retry(client, 12)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_TEMPERATURE":
                value = measure_with_retry(client, 21)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_RADIATOR_TEMP":
                value = measure_with_retry(client, 22)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_AMBIENT_TEMP":
                value = measure_with_retry(client, 15)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_MPPT_POWER":
                value = measure_with_retry(client, 16)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_ISOLATION":
                value = measure_with_retry(client, 30)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_OPERATING_HOURS":
                value = measure_with_retry(client, 18)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_SERIAL_NUMBER":
                self._state = client.serial_number()
            elif self._sensor_type == "DSP_VERSION":
                self._state = client.version()
            elif self._sensor_type == "DSP_MODEL":
                self._state = client.version()
            elif self._sensor_type == "DSP_EVENTS":
                events = measure_with_retry(client, 21)
                self._state = events
            elif self._sensor_type == "DSP_LAST_ERROR":
                last_error = measure_with_retry(client, 22)
                self._state = last_error
            elif self._sensor_type == "DSP_ALARMS":
                alarms = measure_with_retry(client, 19)
                self._state = self._text_mapping.get(int(alarms), "Unbekannt") if alarms is not None else "Unbekannt"
            elif self._sensor_type == "DSP_FAULT_CODE":
                fault = measure_with_retry(client, 20)
                self._state = self._text_mapping.get(int(fault), "Unbekannt") if fault is not None else "Unbekannt"
            elif self._sensor_type == "DSP_STATUS":
                status = measure_with_retry(client, 23)
                self._state = self._text_mapping.get(int(status), "Unbekannt") if status is not None else "Unbekannt"
            elif self._sensor_type == "DSP_INPUT_2_VOLTAGE":
                value = measure_with_retry(client, 26)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_INPUT_2_CURRENT":
                value = measure_with_retry(client, 27)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_VBULK":
                value = measure_with_retry(client, 5)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_ILEAK_DC_DC":
                value = measure_with_retry(client, 6)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_ILEAK_INVERTER":
                value = measure_with_retry(client, 7)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_PIN1":
                value = measure_with_retry(client, 8)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_PIN2":
                value = measure_with_retry(client, 9)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_VOLTAGE_DC_DC":
                value = measure_with_retry(client, 28)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_FREQUENCY_DC_DC":
                value = measure_with_retry(client, 29)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_VBULK_DC_DC":
                value = measure_with_retry(client, 31)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_AVERAGE_GRID_VOLTAGE":
                value = measure_with_retry(client, 32)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_VBULK_MID":
                value = measure_with_retry(client, 33)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_POWER_PEAK":
                value = measure_with_retry(client, 34)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_POWER_PEAK_TODAY":
                value = measure_with_retry(client, 35)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_VOLTAGE_NEUTRAL":
                value = measure_with_retry(client, 36)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_WIND_GENERATOR_FREQUENCY":
                value = measure_with_retry(client, 37)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_VOLTAGE_NEUTRAL_PHASE":
                value = measure_with_retry(client, 38)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_CURRENT_PHASE_R":
                value = measure_with_retry(client, 39)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_CURRENT_PHASE_S":
                value = measure_with_retry(client, 40)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_CURRENT_PHASE_T":
                value = measure_with_retry(client, 41)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FREQUENCY_PHASE_R":
                value = measure_with_retry(client, 42)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FREQUENCY_PHASE_S":
                value = measure_with_retry(client, 43)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FREQUENCY_PHASE_T":
                value = measure_with_retry(client, 44)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_VBULK_PLUS":
                value = measure_with_retry(client, 45)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_VBULK_MINUS":
                value = measure_with_retry(client, 46)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_SUPERVISOR_TEMPERATURE":
                value = measure_with_retry(client, 47)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_ALIM_TEMPERATURE":
                value = measure_with_retry(client, 48)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_HEAT_SINK_TEMPERATURE":
                value = measure_with_retry(client, 49)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_TEMPERATURE_1":
                value = measure_with_retry(client, 50)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_TEMPERATURE_2":
                value = measure_with_retry(client, 51)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_TEMPERATURE_3":
                value = measure_with_retry(client, 52)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FAN_1_SPEED":
                value = measure_with_retry(client, 53)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FAN_2_SPEED":
                value = measure_with_retry(client, 54)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FAN_3_SPEED":
                value = measure_with_retry(client, 55)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FAN_4_SPEED":
                value = measure_with_retry(client, 56)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_FAN_5_SPEED":
                value = measure_with_retry(client, 57)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_POWER_SATURATION_LIMIT":
                value = measure_with_retry(client, 58)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_RIFERIMENTO_ANELLO_BULK":
                value = measure_with_retry(client, 59)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_VPANEL_MICRO":
                value = measure_with_retry(client, 60)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_VOLTAGE_PHASE_R":
                value = measure_with_retry(client, 61)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_VOLTAGE_PHASE_S":
                value = measure_with_retry(client, 62)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_GRID_VOLTAGE_PHASE_T":
                value = measure_with_retry(client, 63)
                self._state = round(value * self._factor, self._precision) if value is not None else None

            # Note: We don't close the connection here since it's managed by the pool
            # The pool will handle connection cleanup based on timeout and health checks
        except AuroraError as e:
            self._state = None
            _LOGGER.error("Fehler bei %s: %s", self._name, e)
        except Exception as e:
            self._state = None
            _LOGGER.error("Allgemeiner Fehler bei %s: %s", self._name, e)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up ALL ABB Aurora sensors (legacy setup)."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    slave_id = config.get(CONF_SLAVE_ID, 2)
    name = config.get("name", f"Aurora WR {slave_id}")
    # Default scan interval for legacy setup
    scan_interval = 60

    # Create all sensors for this inverter
    sensors = [
        # Power and Energy
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_POWER", "W", factor=1, precision=2, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DAILY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_WEEKLY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MONTHLY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_YEARLY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TOTAL_ENERGY", "kWh", factor=0.1, precision=2, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PF", "", factor=1, precision=2, scan_interval=scan_interval),

        # DC Circuit
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_CURRENT", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_POWER", "W", factor=1, precision=0, scan_interval=scan_interval),

        # Temperature and Environment
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_RADIATOR_TEMP", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_AMBIENT_TEMP", "°C", factor=1, precision=1, scan_interval=scan_interval),

        # Diagnostics (important!)
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALARMS", "", text_mapping=ALARM_MESSAGES, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAULT_CODE", "", text_mapping=FAULT_MESSAGES, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_STATUS", "", text_mapping=STATUS_MESSAGES, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_EVENTS", "", scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_LAST_ERROR", "", scan_interval=scan_interval),

        # Serial Numbers and Model (as String)
        AuroraSensorBase(host, port, slave_id, name, "DSP_SERIAL_NUMBER", "", is_string=True, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MODEL", "", is_string=True, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VERSION", "", is_string=True, scan_interval=scan_interval),

        # Advanced Diagnostics
        AuroraSensorBase(host, port, slave_id, name, "DSP_ISOLATION", "kΩ", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_OPERATING_HOURS", "h", factor=1, precision=0, scan_interval=scan_interval),

        # Input 2
        AuroraSensorBase(host, port, slave_id, name, "DSP_INPUT_2_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_INPUT_2_CURRENT", "A", factor=1, precision=1, scan_interval=scan_interval),

        # Vbulk
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Leakage Currents
        AuroraSensorBase(host, port, slave_id, name, "DSP_ILEAK_DC_DC", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_ILEAK_INVERTER", "A", factor=1, precision=1, scan_interval=scan_interval),

        # Pins
        AuroraSensorBase(host, port, slave_id, name, "DSP_PIN1", "W", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PIN2", "W", factor=1, precision=1, scan_interval=scan_interval),

        # DC/DC
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_DC_DC", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY_DC_DC", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_DC_DC", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Average Grid Voltage
        AuroraSensorBase(host, port, slave_id, name, "DSP_AVERAGE_GRID_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Vbulk Mid
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_MID", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Power Peaks
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_PEAK", "W", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_PEAK_TODAY", "W", factor=1, precision=0, scan_interval=scan_interval),

        # Neutral Conductor
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_NEUTRAL", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_NEUTRAL_PHASE", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Wind Generator
        AuroraSensorBase(host, port, slave_id, name, "DSP_WIND_GENERATOR_FREQUENCY", "Hz", factor=1, precision=1, scan_interval=scan_interval),

        # Phase Currents
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_R", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_S", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_T", "A", factor=1, precision=1, scan_interval=scan_interval),

        # Phase Frequencies
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_R", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_S", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_T", "Hz", factor=1, precision=1, scan_interval=scan_interval),

        # Vbulk Plus/Minus
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_PLUS", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_MINUS", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Temperaturen
        AuroraSensorBase(host, port, slave_id, name, "DSP_SUPERVISOR_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALIM_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_HEAT_SINK_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_1", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_2", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_3", "°C", factor=1, precision=1, scan_interval=scan_interval),

        # Fan Speeds
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_1_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_2_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_3_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_4_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_5_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),

        # Power Saturation Limit
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_SATURATION_LIMIT", "W", factor=1, precision=0, scan_interval=scan_interval),

        # Bulk Ring Reference
        AuroraSensorBase(host, port, slave_id, name, "DSP_RIFERIMENTO_ANELLO_BULK", "", factor=1, precision=1, scan_interval=scan_interval),

        # Micro Panel Voltage
        AuroraSensorBase(host, port, slave_id, name, "DSP_VPANEL_MICRO", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Phase Voltages
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_R", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_S", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_T", "V", factor=1, precision=1, scan_interval=scan_interval),
    ]
    add_entities(sensors, True)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up ABB Aurora sensors from a config entry."""
    from homeassistant.const import CONF_HOST, CONF_PORT
    from .const import CONF_SLAVE_ID, CONF_SCAN_INTERVAL
    
    # Get configuration from the config entry
    host = config_entry.data[CONF_HOST]
    port = config_entry.data[CONF_PORT]
    slave_id = config_entry.data.get(CONF_SLAVE_ID, 2)
    # Get scan interval from config entry data or options, default to 60 seconds
    scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, config_entry.data.get(CONF_SCAN_INTERVAL, 60))
    # Use the entry title as the name (this is what the user provided in config flow)
    name = config_entry.title

    # Create all sensors for this inverter
    sensors = [
        # Power and Energy
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_POWER", "W", factor=1, precision=2, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DAILY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_WEEKLY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MONTHLY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_YEARLY_ENERGY", "Wh", precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TOTAL_ENERGY", "kWh", factor=0.1, precision=2, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PF", "", factor=1, precision=2, scan_interval=scan_interval),

        # DC Circuit
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_CURRENT", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_POWER", "W", factor=1, precision=0, scan_interval=scan_interval),

        # Temperature and Environment
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_RADIATOR_TEMP", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_AMBIENT_TEMP", "°C", factor=1, precision=1, scan_interval=scan_interval),

        # Diagnostics (important!)
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALARMS", "", text_mapping=ALARM_MESSAGES, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAULT_CODE", "", text_mapping=FAULT_MESSAGES, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_STATUS", "", text_mapping=STATUS_MESSAGES, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_EVENTS", "", scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_LAST_ERROR", "", scan_interval=scan_interval),

        # Serial Numbers and Model (as String)
        AuroraSensorBase(host, port, slave_id, name, "DSP_SERIAL_NUMBER", "", is_string=True, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MODEL", "", is_string=True, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VERSION", "", is_string=True, scan_interval=scan_interval),

        # Advanced Diagnostics
        AuroraSensorBase(host, port, slave_id, name, "DSP_ISOLATION", "kΩ", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_OPERATING_HOURS", "h", factor=1, precision=0, scan_interval=scan_interval),

        # Input 2
        AuroraSensorBase(host, port, slave_id, name, "DSP_INPUT_2_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_INPUT_2_CURRENT", "A", factor=1, precision=1, scan_interval=scan_interval),

        # Vbulk
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Leakage Currents
        AuroraSensorBase(host, port, slave_id, name, "DSP_ILEAK_DC_DC", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_ILEAK_INVERTER", "A", factor=1, precision=1, scan_interval=scan_interval),

        # Pins
        AuroraSensorBase(host, port, slave_id, name, "DSP_PIN1", "W", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PIN2", "W", factor=1, precision=1, scan_interval=scan_interval),

        # DC/DC
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_DC_DC", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY_DC_DC", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_DC_DC", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Average Grid Voltage
        AuroraSensorBase(host, port, slave_id, name, "DSP_AVERAGE_GRID_VOLTAGE", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Vbulk Mid
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_MID", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Power Peaks
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_PEAK", "W", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_PEAK_TODAY", "W", factor=1, precision=0, scan_interval=scan_interval),

        # Neutral Conductor
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_NEUTRAL", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_NEUTRAL_PHASE", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Wind Generator
        AuroraSensorBase(host, port, slave_id, name, "DSP_WIND_GENERATOR_FREQUENCY", "Hz", factor=1, precision=1, scan_interval=scan_interval),

        # Phase Currents
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_R", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_S", "A", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_T", "A", factor=1, precision=1, scan_interval=scan_interval),

        # Phase Frequencies
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_R", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_S", "Hz", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_T", "Hz", factor=1, precision=1, scan_interval=scan_interval),

        # Vbulk Plus/Minus
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_PLUS", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_MINUS", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Temperaturen
        AuroraSensorBase(host, port, slave_id, name, "DSP_SUPERVISOR_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALIM_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_HEAT_SINK_TEMPERATURE", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_1", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_2", "°C", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_3", "°C", factor=1, precision=1, scan_interval=scan_interval),

        # Fan Speeds
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_1_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_2_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_3_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_4_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_5_SPEED", "rpm", factor=1, precision=0, scan_interval=scan_interval),

        # Power Saturation Limit
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_SATURATION_LIMIT", "W", factor=1, precision=0, scan_interval=scan_interval),

        # Bulk Ring Reference
        AuroraSensorBase(host, port, slave_id, name, "DSP_RIFERIMENTO_ANELLO_BULK", "", factor=1, precision=1, scan_interval=scan_interval),

        # Micro Panel Voltage
        AuroraSensorBase(host, port, slave_id, name, "DSP_VPANEL_MICRO", "V", factor=1, precision=1, scan_interval=scan_interval),

        # Phase Voltages
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_R", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_S", "V", factor=1, precision=1, scan_interval=scan_interval),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_T", "V", factor=1, precision=1, scan_interval=scan_interval),
    ]
    async_add_entities(sensors, True)
