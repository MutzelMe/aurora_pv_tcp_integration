"""Support for ABB Aurora Solar Inverters via Waveshare RS485-to-Ethernet adapter."""
from __future__ import annotations
import logging
import time
from datetime import timedelta
from aurorapy.client import AuroraTCPClient, AuroraError
from aurorapy.mapping import Mapping

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN, CONF_SLAVE_ID

_LOGGER = logging.getLogger(__name__)

# Use aurorapy mappings:
ALARM_MESSAGES = Mapping.GLOBAL_STATES
STATUS_MESSAGES = Mapping.GLOBAL_STATES

# Icon mapping for sensors
ICON_MAPPING = {
    # Power & Energy
    "DSP_GRID_POWER": "mdi:solar-power",
    "DSP_DC_POWER": "mdi:solar-power",
    "DSP_MPPT_POWER": "mdi:solar-power",
    "DSP_POWER_PEAK": "mdi:solar-power",
    "DSP_POWER_PEAK_TODAY": "mdi:solar-power",
    "DSP_PIN1": "mdi:solar-power",
    "DSP_PIN2": "mdi:solar-power",
    "DSP_PV1_POWER": "mdi:solar-power",
    "DSP_PV2_POWER": "mdi:solar-power",
    "DSP_DAILY_ENERGY": "mdi:solar-power-variant",
    "DSP_TOTAL_ENERGY": "mdi:counter",
    "DSP_EFFICIENCY": "mdi:percent",
    # Voltage
    "DSP_GRID_VOLTAGE": "mdi:flash",
    "DSP_AVERAGE_GRID_VOLTAGE": "mdi:flash",
    "DSP_AC_VOLTAGE_PHASE": "mdi:flash",
    "DSP_DC_VOLTAGE": "mdi:flash-outline",
    "DSP_DC_VOLTAGE2": "mdi:flash-outline",
    "DSP_PV1_VOLTAGE": "mdi:solar-panel",
    "DSP_PV2_VOLTAGE": "mdi:solar-panel",
    # Current
    "DSP_GRID_CURRENT": "mdi:current-ac",
    "DSP_DC_CURRENT": "mdi:current-dc",
    "DSP_DC_CURRENT2": "mdi:current-dc",
    "DSP_PV1_CURRENT": "mdi:solar-panel",
    "DSP_PV2_CURRENT": "mdi:solar-panel",
    # Frequency & Grid
    "DSP_GRID_FREQUENCY": "mdi:sine-wave",
    "DSP_PF": "mdi:angle-acute",
    # Temperature
    "DSP_TEMPERATURE": "mdi:thermometer",
    "DSP_RADIATOR_TEMP": "mdi:thermometer",
    "DSP_BOOSTER_TEMP": "mdi:thermometer",
    "DSP_IPM_TEMP": "mdi:thermometer",
    "DSP_DSP_TEMP": "mdi:thermometer",
    # Operation & Counters
    "DSP_OPERATION_TIME": "mdi:clock-outline",
    "DSP_GRID_RELAY_COUNTER": "mdi:counter",
    "DSP_DC_DISCONNECT_COUNTER": "mdi:counter",
    # Diagnostics
    "DSP_ALARMS": "mdi:alert",
    "DSP_LAST_ALARM": "mdi:alert-circle-outline",
    "DSP_FAULT_CODE": "mdi:alert-circle",
    "DSP_LAST_FAULT": "mdi:alert-circle-outline",
    "DSP_STATUS": "mdi:information",
    "DSP_EVENTS": "mdi:calendar-clock",
    # STATES
    "DSP_GLOBAL_STATE": "mdi:state-machine",
    "DSP_INVERTER_STATE": "mdi:state-machine",
    "DSP_DCDC_CH1_STATE": "mdi:state-machine",
    "DSP_DCDC_CH2_STATE": "mdi:state-machine",
    "DSP_ALARM_STATE": "mdi:alert",
    # Device Data
    "DSP_MODEL": "mdi:information-outline",
    #"DSP_SERIAL": "mdi:barcode",
    "DSP_SERIAL_NUMBER": "mdi:barcode",
    "DSP_FW_VERSION": "mdi:chip",
    "DSP_DSP_VERSION": "mdi:chip",
}

FAULT_MESSAGES = {
    0x0000: "No Fault",
    0x0001: "Short Circuit",
    0x0002: "Communication Error",
}

# --- SCALE FACTORS AND UNITS ---
UNITS = {
    "DSP_GRID_POWER": "W",
    "DSP_DAILY_ENERGY": "Wh",
    "DSP_TOTAL_ENERGY": "kWh",
    "DSP_GRID_VOLTAGE": "V",
    "DSP_GRID_CURRENT": "A",
    "DSP_GRID_FREQUENCY": "Hz",
    "DSP_TEMPERATURE": "°C",
    "DSP_DC_VOLTAGE": "V",
    "DSP_DC_CURRENT": "A",
    "DSP_DC_POWER": "W",
    "DSP_EFFICIENCY": "%",
    "DSP_PF": "",
    "DSP_AC_VOLTAGE_PHASE": "V",
    "DSP_DC_VOLTAGE2": "V",
    "DSP_DC_CURRENT2": "A",
    "DSP_RADIATOR_TEMP": "°C",
    "DSP_BOOSTER_TEMP": "°C",
    "DSP_IPM_TEMP": "°C",
    "DSP_DSP_TEMP": "°C",
    "DSP_ALARMS": "",
    "DSP_STATUS": "",
    "DSP_EVENTS": "",
    "DSP_FAULT_CODE": "",
    "DSP_MODEL": "",
    "DSP_SERIAL_NUMBER": "",
    "DSP_FW_VERSION": "",
    "DSP_DSP_VERSION": "",
    "DSP_LAST_ALARM": "date",
    "DSP_LAST_FAULT": "date",
    "DSP_OPERATION_TIME": "h",
    "DSP_GRID_RELAY_COUNTER": "",
    "DSP_DC_DISCONNECT_COUNTER": "",
    "DSP_PV1_VOLTAGE": "V",
    "DSP_PV1_CURRENT": "A",
    "DSP_PV2_VOLTAGE": "V",
    "DSP_PV2_CURRENT": "A",
    "DSP_PV1_POWER": "W",
    "DSP_PV2_POWER": "W",
    "DSP_GLOBAL_STATE": "",
    "DSP_INVERTER_STATE": "",
    "DSP_DCDC_CH1_STATE": "",
    "DSP_DCDC_CH2_STATE": "",
    "DSP_ALARM_STATE": "",
}

FACTORS = {
    "DSP_GRID_POWER": 1,
    "DSP_DAILY_ENERGY": 1,
    "DSP_TOTAL_ENERGY": 0.1,
    "DSP_GRID_VOLTAGE": 0.1,
    "DSP_GRID_CURRENT": 0.1,
    "DSP_GRID_FREQUENCY": 0.01,
    "DSP_TEMPERATURE": 0.1,
    "DSP_DC_VOLTAGE": 0.1,
    "DSP_DC_CURRENT": 0.1,
    "DSP_DC_POWER": 1,
    "DSP_EFFICIENCY": 0.1,
    "DSP_PF": 0.001,
    "DSP_AC_VOLTAGE_PHASE": 0.1,
    "DSP_DC_VOLTAGE2": 0.1,
    "DSP_DC_CURRENT2": 0.1,
    "DSP_RADIATOR_TEMP": 0.1,
    "DSP_BOOSTER_TEMP": 0.1,
    "DSP_IPM_TEMP": 0.1,
    "DSP_DSP_TEMP": 0.1,
    "DSP_ALARMS": 1,
    "DSP_STATUS": 1,
    "DSP_EVENTS": 1,
    "DSP_FAULT_CODE": 1,
    "DSP_MODEL": 1,
    "DSP_SERIAL_NUMBER": 1,
    "DSP_FW_VERSION": 1,
    "DSP_DSP_VERSION": 1,
    "DSP_LAST_ALARM": 1,
    "DSP_LAST_FAULT": 1,
    "DSP_OPERATION_TIME": 0.1,
    "DSP_GRID_RELAY_COUNTER": 1,
    "DSP_DC_DISCONNECT_COUNTER": 1,
    "DSP_PV1_VOLTAGE": 0.1,
    "DSP_PV1_CURRENT": 0.1,
    "DSP_PV2_VOLTAGE": 0.1,
    "DSP_PV2_CURRENT": 0.1,
    "DSP_PV1_POWER": 1,
    "DSP_PV2_POWER": 1,
    "DSP_GLOBAL_STATE": 1,
    "DSP_INVERTER_STATE": 1,
    "DSP_DCDC_CH1_STATE": 1,
    "DSP_DCDC_CH2_STATE": 1,
    "DSP_ALARM_STATE": 1,
}

# --- HUMAN READABLE SENSOR NAMES ---
SENSOR_NAMES = {
    "DSP_GRID_POWER": "Grid Power",
    "DSP_DAILY_ENERGY": "Daily Energy",
    "DSP_TOTAL_ENERGY": "Total Energy",
    "DSP_GRID_VOLTAGE": "Grid Voltage",
    "DSP_GRID_CURRENT": "Grid Current",
    "DSP_GRID_FREQUENCY": "Grid Frequency",
    "DSP_TEMPERATURE": "Temperature",
    "DSP_DC_VOLTAGE": "DC Voltage",
    "DSP_DC_CURRENT": "DC Current",
    "DSP_DC_POWER": "DC Power",
    "DSP_EFFICIENCY": "Efficiency",
    "DSP_PF": "Power Factor",
    "DSP_AC_VOLTAGE_PHASE": "AC Phase Voltage",
    "DSP_DC_VOLTAGE2": "DC Voltage 2",
    "DSP_DC_CURRENT2": "DC Current 2",
    "DSP_RADIATOR_TEMP": "Radiator Temperature",
    "DSP_BOOSTER_TEMP": "Booster Temperature",
    "DSP_IPM_TEMP": "IPM Temperature",
    "DSP_DSP_TEMP": "DSP Temperature",
    "DSP_ALARMS": "Alarms",
    "DSP_STATUS": "Status",
    "DSP_EVENTS": "Events",
    "DSP_FAULT_CODE": "Fault Code",
    "DSP_MODEL": "Model",
    "DSP_SERIAL_NUMBER": "Serial Number",
    "DSP_FW_VERSION": "Firmware Version",
    "DSP_DSP_VERSION": "DSP Version",
    "DSP_LAST_ALARM": "Last Alarm",
    "DSP_LAST_FAULT": "Last Fault",
    "DSP_OPERATION_TIME": "Operation Time",
    "DSP_GRID_RELAY_COUNTER": "Grid Relay Counter",
    "DSP_DC_DISCONNECT_COUNTER": "DC Disconnect Counter",
    "DSP_PV1_VOLTAGE": "PV1 Voltage",
    "DSP_PV1_CURRENT": "PV1 Current",
    "DSP_PV2_VOLTAGE": "PV2 Voltage",
    "DSP_PV2_CURRENT": "PV2 Current",
    "DSP_PV1_POWER": "PV1 Power",
    "DSP_PV2_POWER": "PV2 Power",
    "DSP_AMBIENT_TEMP": "Ambient Temperature",
    "DSP_MPPT_POWER": "MPPT Power",
    "DSP_ISOLATION": "Isolation Resistance",
    "DSP_OPERATING_HOURS": "Operating Hours",
    "DSP_SERIAL_NUMBER": "Serial Number",
    "DSP_VERSION": "Version",
    "DSP_LAST_ERROR": "Last Error",
    "DSP_INPUT_2_VOLTAGE": "Input 2 Voltage",
    "DSP_INPUT_2_CURRENT": "Input 2 Current",
    "DSP_VBULK": "Bulk Voltage",
    "DSP_ILEAK_DC_DC": "DC/DC Leakage Current",
    "DSP_ILEAK_INVERTER": "Inverter Leakage Current",
    "DSP_PIN1": "Input Power 1",
    "DSP_PIN2": "Input Power 2",
    "DSP_GRID_VOLTAGE_DC_DC": "DC/DC Grid Voltage",
    "DSP_GRID_FREQUENCY_DC_DC": "DC/DC Grid Frequency",
    "DSP_VBULK_DC_DC": "DC/DC Bulk Voltage",
    "DSP_AVERAGE_GRID_VOLTAGE": "Average Grid Voltage",
    "DSP_VBULK_MID": "Mid Bulk Voltage",
    "DSP_POWER_PEAK": "Peak Power",
    "DSP_POWER_PEAK_TODAY": "Today's Peak Power",
    "DSP_GRID_VOLTAGE_NEUTRAL": "Neutral Grid Voltage",
    "DSP_GRID_VOLTAGE_NEUTRAL_PHASE": "Neutral-Phase Grid Voltage",
    "DSP_WIND_GENERATOR_FREQUENCY": "Wind Generator Frequency",
    "DSP_GRID_CURRENT_PHASE_R": "Phase R Grid Current",
    "DSP_GRID_CURRENT_PHASE_S": "Phase S Grid Current",
    "DSP_GRID_CURRENT_PHASE_T": "Phase T Grid Current",
    "DSP_FREQUENCY_PHASE_R": "Phase R Frequency",
    "DSP_FREQUENCY_PHASE_S": "Phase S Frequency",
    "DSP_FREQUENCY_PHASE_T": "Phase T Frequency",
    "DSP_VBULK_PLUS": "Positive Bulk Voltage",
    "DSP_VBULK_MINUS": "Negative Bulk Voltage",
    "DSP_SUPERVISOR_TEMPERATURE": "Supervisor Temperature",
    "DSP_ALIM_TEMPERATURE": "Power Supply Temperature",
    "DSP_HEAT_SINK_TEMPERATURE": "Heat Sink Temperature",
    "DSP_TEMPERATURE_1": "Temperature 1",
    "DSP_TEMPERATURE_2": "Temperature 2",
    "DSP_TEMPERATURE_3": "Temperature 3",
    "DSP_FAN_1_SPEED": "Fan 1 Speed",
    "DSP_FAN_2_SPEED": "Fan 2 Speed",
    "DSP_FAN_3_SPEED": "Fan 3 Speed",
    "DSP_FAN_4_SPEED": "Fan 4 Speed",
    "DSP_FAN_5_SPEED": "Fan 5 Speed",
    "DSP_POWER_SATURATION_LIMIT": "Power Saturation Limit",
    "DSP_RIFERIMENTO_ANELLO_BULK": "Bulk Ring Reference",
    "DSP_VPANEL_MICRO": "Micro Panel Voltage",
    "DSP_GRID_VOLTAGE_PHASE_R": "Phase R Grid Voltage",
    "DSP_GRID_VOLTAGE_PHASE_S": "Phase S Grid Voltage",
    "DSP_GRID_VOLTAGE_PHASE_T": "Phase T Grid Voltage",
    "DSP_GLOBAL_STATE": "Global State",
    "DSP_INVERTER_STATE": "Inverter State",
    "DSP_DCDC_CH1_STATE": "DCDC Channel 1 State",
    "DSP_DCDC_CH2_STATE": "DSP_DCDC Channel 2 State",
    "DSP_ALARM_STATE": "Alarm State",
}

# --- COMPLETE COMMAND LIST (INCLUDING ALL SENSORS) ---
COMMANDS = {
    "DSP_GRID_POWER": b"\x30\x33\x0D",
    "DSP_DAILY_ENERGY": b"\x31\x33\x0D",
    "DSP_TOTAL_ENERGY": b"\x31\x34\x0D",
    "DSP_GRID_VOLTAGE": b"\x32\x33\x0D",
    "DSP_GRID_CURRENT": b"\x33\x33\x0D",
    "DSP_GRID_FREQUENCY": b"\x34\x33\x0D",
    "DSP_TEMPERATURE": b"\x35\x33\x0D",
    "DSP_DC_VOLTAGE": b"\x36\x33\x0D",
    "DSP_DC_CURRENT": b"\x37\x33\x0D",
    "DSP_DC_POWER": b"\x38\x33\x0D",
    "DSP_EFFICIENCY": b"\x39\x33\x0D",
    "DSP_PF": b"\x3A\x33\x0D",
    "DSP_AC_VOLTAGE_PHASE": b"\x3B\x33\x0D",
    "DSP_DC_VOLTAGE2": b"\x3C\x33\x0D",
    "DSP_DC_CURRENT2": b"\x3D\x33\x0D",
    "DSP_RADIATOR_TEMP": b"\x3E\x33\x0D",
    "DSP_BOOSTER_TEMP": b"\x3F\x33\x0D",
    "DSP_IPM_TEMP": b"\x40\x33\x0D",
    "DSP_DSP_TEMP": b"\x41\x33\x0D",
    "DSP_ALARMS": b"\x50\x33\x0D",
    "DSP_STATUS": b"\x51\x33\x0D",
    "DSP_EVENTS": b"\x52\x33\x0D",
    "DSP_FAULT_CODE": b"\x53\x33\x0D",
    "DSP_MODEL": b"\x55\x33\x0D",    # used via client.pn()
    #"DSP_SERIAL": b"\x56\x33\x0D",
    "DSP_FW_VERSION": b"\x57\x33\x0D",
    "DSP_DSP_VERSION": b"\x58\x33\x0D",
    "DSP_LAST_ALARM": b"\x59\x33\x0D",
    "DSP_LAST_FAULT": b"\x5A\x33\x0D",
    "DSP_OPERATION_TIME": b"\x5B\x33\x0D",
    "DSP_GRID_RELAY_COUNTER": b"\x5C\x33\x0D",
    "DSP_DC_DISCONNECT_COUNTER": b"\x5D\x33\x0D",
    "DSP_PV1_VOLTAGE": b"\x60\x33\x0D",
    "DSP_PV1_CURRENT": b"\x61\x33\x0D",
    "DSP_PV2_VOLTAGE": b"\x62\x33\x0D",
    "DSP_PV2_CURRENT": b"\x63\x33\x0D",
    "DSP_PV1_POWER": b"\x64\x33\x0D",
    "DSP_PV2_POWER": b"\x65\x33\x0D",
    "DSP_GLOBAL_STATE": None,
    "DSP_INVERTER_STATE": None,
    "DSP_DCDC_CH1_STATE": None,
    "DSP_DCDC_CH2_STATE": None,
    "DSP_ALARM_STATE": None,
    "DSP_SERIAL_NUMBER": None,
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all Aurora Solar Inverter sensors from config entry."""
    host = config_entry.data[CONF_HOST]
    port = config_entry.data[CONF_PORT]
    slave_id = config_entry.data[CONF_SLAVE_ID]
    name = config_entry.data.get("name", f"INV {slave_id}")

    coordinator = AuroraDataUpdateCoordinator(hass, host, port, slave_id)

    # Manuell hinzugefügte Status-Sensoren
    sensors = [
        AuroraSensor(
            coordinator=coordinator,
            sensor_type="DSP_GLOBAL_STATE",
            unit=UNITS["DSP_GLOBAL_STATE"],
            factor=FACTORS["DSP_GLOBAL_STATE"],
            name=f"INV {slave_id} {SENSOR_NAMES['DSP_GLOBAL_STATE']}",
            is_string=True,
        ),
        AuroraSensor(
            coordinator=coordinator,
            sensor_type="DSP_INVERTER_STATE",
            unit=UNITS["DSP_INVERTER_STATE"],
            factor=FACTORS["DSP_INVERTER_STATE"],
            name=f"INV {slave_id} {SENSOR_NAMES['DSP_INVERTER_STATE']}",
            is_string=True,
        ),
        AuroraSensor(
            coordinator=coordinator,
            sensor_type="DSP_DCDC_CH1_STATE",
            unit=UNITS["DSP_DCDC_CH1_STATE"],
            factor=FACTORS["DSP_DCDC_CH1_STATE"],
            name=f"INV {slave_id} {SENSOR_NAMES['DSP_DCDC_CH1_STATE']}",
            is_string=True,
        ),
        AuroraSensor(
            coordinator=coordinator,
            sensor_type="DSP_DCDC_CH2_STATE",
            unit=UNITS["DSP_DCDC_CH2_STATE"],
            factor=FACTORS["DSP_DCDC_CH2_STATE"],
            name=f"INV {slave_id} {SENSOR_NAMES['DSP_DCDC_CH2_STATE']}",
            is_string=True,
        ),
        AuroraSensor(
            coordinator=coordinator,
            sensor_type="DSP_ALARM_STATE",
            unit=UNITS["DSP_ALARM_STATE"],
            factor=FACTORS["DSP_ALARM_STATE"],
            name=f"INV {slave_id} {SENSOR_NAMES['DSP_ALARM_STATE']}",
            is_string=True,
        ),
    ]

    # Sensoren aus COMMANDS (Schleife)
    sensors += [
        AuroraSensor(
            coordinator=coordinator,
            sensor_type=st,
            unit=UNITS.get(st, ""),
            factor=FACTORS.get(st, 1),
            name=f"INV {slave_id} {SENSOR_NAMES.get(st, st)}",
            text_mapping=(
                ALARM_MESSAGES if st == "DSP_ALARMS"
                else STATUS_MESSAGES if st == "DSP_STATUS"
                else FAULT_MESSAGES if st == "DSP_FAULT_CODE"
                else None
            ),
            is_string=st in [
                "DSP_ALARMS", "DSP_STATUS", "DSP_EVENTS",
                "DSP_FAULT_CODE", "DSP_MODEL", "DSP_SERIAL_NUMBER",
                "DSP_FW_VERSION", "DSP_DSP_VERSION"
            ],
        )
        for st in COMMANDS
    ]

    async_add_entities(sensors, True)

class AuroraDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Aurora inverter."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, slave_id: int):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"INV {slave_id}",
            update_interval=timedelta(seconds=60),
        )
        self._host = host
        self._port = port
        self._slave_id = slave_id

    async def _async_update_data(self):
        """Fetch data from the Aurora inverter."""
        data = {}
        try:
            client = AuroraTCPClient(ip=self._host, port=self._port, address=self._slave_id, timeout=20)
            client.connect()

            # Status request
            data["DSP_GLOBAL_STATE"] = client.state(1)    # Global State
            data["DSP_INVERTER_STATE"] = client.state(2)  # Inverter State
            data["DSP_DCDC_CH1_STATE"] = client.state(3)  # DCDC State Channel 1
            data["DSP_DCDC_CH2_STATE"] = client.state(4)  # DCDC State Channel 2
            data["DSP_ALARM_STATE"] = client.state(5)     # Alarm State
                
            for sensor_type, command in COMMANDS.items():
                try:                   
                    if sensor_type == "DSP_GRID_POWER":
                        data[sensor_type] = client.measure(3)
                    
                    elif self._sensor_type == "DSP_MODEL":
                        self._state = client.pn()  # Modellbezeichnung abfragen
                                        
                    elif sensor_type == "DSP_DAILY_ENERGY":
                        data[sensor_type] = client.cumulated_energy(0)
                    elif sensor_type == "DSP_TOTAL_ENERGY":
                        data[sensor_type] = client.cumulated_energy(1)
                    elif sensor_type == "DSP_GRID_VOLTAGE":
                        data[sensor_type] = client.measure(1)
                    elif sensor_type == "DSP_GRID_CURRENT":
                        data[sensor_type] = client.measure(2)
                    elif sensor_type == "DSP_GRID_FREQUENCY":
                        data[sensor_type] = client.measure(4)
                    elif sensor_type == "DSP_PF":
                        data[sensor_type] = client.measure(9)
                    elif sensor_type == "DSP_DC_VOLTAGE":
                        data[sensor_type] = client.measure(23)
                    elif sensor_type == "DSP_DC_CURRENT":
                        data[sensor_type] = client.measure(25)
                    elif sensor_type == "DSP_DC_POWER":
                        data[sensor_type] = client.measure(12)
                    elif sensor_type == "DSP_TEMPERATURE":
                        data[sensor_type] = client.measure(21)
                    elif sensor_type == "DSP_RADIATOR_TEMP":
                        data[sensor_type] = client.measure(22)
                    elif sensor_type == "DSP_AMBIENT_TEMP":
                        data[sensor_type] = client.measure(15)
                    elif sensor_type == "DSP_MPPT_POWER":
                        data[sensor_type] = client.measure(16)
                    elif sensor_type == "DSP_ISOLATION":
                        data[sensor_type] = client.measure(30)
                    elif sensor_type == "DSP_OPERATING_HOURS":
                        data[sensor_type] = client.measure(18)
                    elif sensor_type == "DSP_SERIAL_NUMBER":
                        data[sensor_type] = client.serial_number()
                    elif sensor_type == "DSP_VERSION":
                        data[sensor_type] = client.version()
                    elif sensor_type == "DSP_EVENTS":
                        data[sensor_type] = client.measure(21)
                    elif sensor_type == "DSP_LAST_ERROR":
                        data[sensor_type] = client.measure(22)
                    elif sensor_type == "DSP_ALARMS":
                        data[sensor_type] = client.measure(19)
                    elif sensor_type == "DSP_FAULT_CODE":
                        data[sensor_type] = client.measure(20)
                    elif sensor_type == "DSP_STATUS":
                        data[sensor_type] = client.measure(23)
                    elif sensor_type == "DSP_INPUT_2_VOLTAGE":
                        data[sensor_type] = client.measure(26)
                    elif sensor_type == "DSP_INPUT_2_CURRENT":
                        data[sensor_type] = client.measure(27)
                    elif sensor_type == "DSP_VBULK":
                        data[sensor_type] = client.measure(5)
                    elif sensor_type == "DSP_ILEAK_DC_DC":
                        data[sensor_type] = client.measure(6)
                    elif sensor_type == "DSP_ILEAK_INVERTER":
                        data[sensor_type] = client.measure(7)
                    elif sensor_type == "DSP_PIN1":
                        data[sensor_type] = client.measure(8)
                    elif sensor_type == "DSP_PIN2":
                        data[sensor_type] = client.measure(9)
                    elif sensor_type == "DSP_GRID_VOLTAGE_DC_DC":
                        data[sensor_type] = client.measure(28)
                    elif sensor_type == "DSP_GRID_FREQUENCY_DC_DC":
                        data[sensor_type] = client.measure(29)
                    elif sensor_type == "DSP_VBULK_DC_DC":
                        data[sensor_type] = client.measure(31)
                    elif sensor_type == "DSP_AVERAGE_GRID_VOLTAGE":
                        data[sensor_type] = client.measure(32)
                    elif sensor_type == "DSP_VBULK_MID":
                        data[sensor_type] = client.measure(33)
                    elif sensor_type == "DSP_POWER_PEAK":
                        data[sensor_type] = client.measure(34)
                    elif sensor_type == "DSP_POWER_PEAK_TODAY":
                        data[sensor_type] = client.measure(35)
                    elif sensor_type == "DSP_GRID_VOLTAGE_NEUTRAL":
                        data[sensor_type] = client.measure(36)
                    elif sensor_type == "DSP_GRID_VOLTAGE_NEUTRAL_PHASE":
                        data[sensor_type] = client.measure(38)
                    elif sensor_type == "DSP_WIND_GENERATOR_FREQUENCY":
                        data[sensor_type] = client.measure(37)
                    elif sensor_type == "DSP_GRID_CURRENT_PHASE_R":
                        data[sensor_type] = client.measure(39)
                    elif sensor_type == "DSP_GRID_CURRENT_PHASE_S":
                        data[sensor_type] = client.measure(40)
                    elif sensor_type == "DSP_GRID_CURRENT_PHASE_T":
                        data[sensor_type] = client.measure(41)
                    elif sensor_type == "DSP_FREQUENCY_PHASE_R":
                        data[sensor_type] = client.measure(42)
                    elif sensor_type == "DSP_FREQUENCY_PHASE_S":
                        data[sensor_type] = client.measure(43)
                    elif sensor_type == "DSP_FREQUENCY_PHASE_T":
                        data[sensor_type] = client.measure(44)
                    elif sensor_type == "DSP_VBULK_PLUS":
                        data[sensor_type] = client.measure(45)
                    elif sensor_type == "DSP_VBULK_MINUS":
                        data[sensor_type] = client.measure(46)
                    elif sensor_type == "DSP_SUPERVISOR_TEMPERATURE":
                        data[sensor_type] = client.measure(47)
                    elif sensor_type == "DSP_ALIM_TEMPERATURE":
                        data[sensor_type] = client.measure(48)
                    elif sensor_type == "DSP_HEAT_SINK_TEMPERATURE":
                        data[sensor_type] = client.measure(49)
                    elif sensor_type == "DSP_TEMPERATURE_1":
                        data[sensor_type] = client.measure(50)
                    elif sensor_type == "DSP_TEMPERATURE_2":
                        data[sensor_type] = client.measure(51)
                    elif sensor_type == "DSP_TEMPERATURE_3":
                        data[sensor_type] = client.measure(52)
                    elif sensor_type == "DSP_FAN_1_SPEED":
                        data[sensor_type] = client.measure(53)
                    elif sensor_type == "DSP_FAN_2_SPEED":
                        data[sensor_type] = client.measure(54)
                    elif sensor_type == "DSP_FAN_3_SPEED":
                        data[sensor_type] = client.measure(55)
                    elif sensor_type == "DSP_FAN_4_SPEED":
                        data[sensor_type] = client.measure(56)
                    elif sensor_type == "DSP_FAN_5_SPEED":
                        data[sensor_type] = client.measure(57)
                    elif sensor_type == "DSP_POWER_SATURATION_LIMIT":
                        data[sensor_type] = client.measure(58)
                    elif sensor_type == "DSP_RIFERIMENTO_ANELLO_BULK":
                        data[sensor_type] = client.measure(59)
                    elif sensor_type == "DSP_VPANEL_MICRO":
                        data[sensor_type] = client.measure(60)
                    elif sensor_type == "DSP_GRID_VOLTAGE_PHASE_R":
                        data[sensor_type] = client.measure(61)
                    elif sensor_type == "DSP_GRID_VOLTAGE_PHASE_S":
                        data[sensor_type] = client.measure(62)
                    elif sensor_type == "DSP_GRID_VOLTAGE_PHASE_T":
                        data[sensor_type] = client.measure(63)
                except AuroraError as e:
                    data[sensor_type] = None
                    _LOGGER.error("Error with %s: %s", sensor_type, e)
                except Exception as e:
                    data[sensor_type] = None
                    _LOGGER.error("General error with %s: %s", sensor_type, e)

            client.close()
        except Exception as e:
            raise UpdateFailed(f"Communication error: {e}") from e
        return data

class AuroraSensor(SensorEntity):
    """Representation of an Aurora Solar Inverter sensor."""

    def __init__(
        self,
        coordinator: AuroraDataUpdateCoordinator,
        sensor_type: str,
        unit: str,
        factor: float,
        name: str,
        text_mapping: dict | None = None,
        is_string: bool = False,
    ):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._sensor_type = sensor_type
        self._unit = unit
        self._factor = factor
        self._name = name
        self._text_mapping = text_mapping
        self._is_string = is_string
        self._attr_unique_id = f"aurora_inv_{coordinator._slave_id}_{sensor_type.lower()}"
        self._attr_icon = ICON_MAPPING.get(sensor_type, "mdi:help")

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def native_value(self):
        """Return the state."""
        if self._coordinator.data is None:
            return None
        value = self._coordinator.data.get(self._sensor_type)
        if value is None:
            return None
        if self._is_string:
            return self._text_mapping.get(value, str(value)) if self._text_mapping else value
        return round(value * self._factor, 2) if self._factor != 1 else value

    @property
    def native_unit_of_measurement(self):
        """Return the unit."""
        return self._unit if not self._is_string else None

    @property
    def icon(self):
        """Return the icon."""
        return self._attr_icon

    @property
    def available(self):
        """Return availability."""
        return self._coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self):
        """Update HA state on new data."""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Register update listener."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_update)
        )

    async def async_update(self):
        """Request refresh."""
        await self._coordinator.async_request_refresh()

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
                time.sleep(1)
                continue
            return None
    return None

class AuroraSensorBase(SensorEntity):
    """Base class for all ABB Aurora sensors."""

    def __init__(self, host, port, slave_id, name, sensor_type, unit, factor=1, precision=2, is_string=False, text_mapping=None):
        """Initialize the sensor."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._attr_name = f"INV {slave_id} {SENSOR_NAMES.get(sensor_type, sensor_type)}"
        self._attr_friendly_name = f"INV {slave_id} {SENSOR_NAMES.get(sensor_type, sensor_type)}"
        self._sensor_type = sensor_type
        self._unit = unit
        self._factor = factor
        self._precision = precision
        self._is_string = is_string
        self._text_mapping = text_mapping
        self._state = None
        self._attr_native_unit_of_measurement = unit if not is_string else None
        self._attr_unique_id = f"aurora_inv_{slave_id}_{sensor_type.lower()}"
        self._attr_icon = ICON_MAPPING.get(sensor_type, "mdi:help")

    @property
    def state(self):
        """Current state of the sensor."""
        return self._state

    def update(self):
        """Update the sensor data."""
        try:
            client = AuroraTCPClient(ip=self._host, port=self._port, address=self._slave_id, timeout=20)
            client.connect()

            if self._sensor_type == "DSP_GRID_POWER":
                value = measure_with_retry(client, 3)
                self._state = round(value * self._factor, self._precision) if value is not None else None
            elif self._sensor_type == "DSP_DAILY_ENERGY":
                self._state = round(client.cumulated_energy(0), self._precision)
            elif self._sensor_type == "DSP_TOTAL_ENERGY":
                self._state = round(client.cumulated_energy(1) * 0.1, self._precision)
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
                self._state = client.pn() 
            elif self._sensor_type == "DSP_EVENTS":
                events = measure_with_retry(client, 21)
                self._state = events
            elif self._sensor_type == "DSP_LAST_ERROR":
                last_error = measure_with_retry(client, 22)
                self._state = last_error
            elif self._sensor_type == "DSP_ALARMS":
                alarms = measure_with_retry(client, 19)
                self._state = self._text_mapping.get(int(alarms), "Unknown") if alarms is not None else "Unknown"
            elif self._sensor_type == "DSP_FAULT_CODE":
                fault = measure_with_retry(client, 20)
                self._state = self._text_mapping.get(int(fault), "Unknown") if fault is not None else "Unknown"
            elif self._sensor_type == "DSP_STATUS":
                status = measure_with_retry(client, 23)
                self._state = self._text_mapping.get(int(status), "Unknown") if status is not None else "Unknown"
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

            client.close()
        except AuroraError as e:
            self._state = None
            _LOGGER.error("Error with %s: %s", self._name, e)
        except Exception as e:
            self._state = None
            _LOGGER.error("General error with %s: %s", self._name, e)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up all ABB Aurora sensors."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    slave_id = config.get(CONF_SLAVE_ID, 2)
    name = config.get("name", f"INV {slave_id}")

    # Create all sensors for this inverter
    sensors = [
        # Power and Energy
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_POWER", "W", factor=1, precision=2),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DAILY_ENERGY", "Wh", precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TOTAL_ENERGY", "kWh", factor=0.1, precision=2),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT", "A", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY", "Hz", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PF", "", factor=1, precision=2),

        # DC Circuit
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_VOLTAGE", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_CURRENT", "A", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_POWER", "W", factor=1, precision=0),

        # Temperature and Environment
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE", "°C", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_RADIATOR_TEMP", "°C", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_AMBIENT_TEMP", "°C", factor=1, precision=1),

        # Diagnostics (important!)
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALARMS", "", text_mapping=ALARM_MESSAGES),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAULT_CODE", "", text_mapping=FAULT_MESSAGES),
        AuroraSensorBase(host, port, slave_id, name, "DSP_STATUS", "", text_mapping=STATUS_MESSAGES),
        AuroraSensorBase(host, port, slave_id, name, "DSP_EVENTS", ""),
        AuroraSensorBase(host, port, slave_id, name, "DSP_LAST_ERROR", ""),

        # Serial numbers and model (as string)
        AuroraSensorBase(host, port, slave_id, name, "DSP_SERIAL_NUMBER", "", is_string=True),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MODEL", "", is_string=True),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VERSION", "", is_string=True),

        # Advanced Diagnostics
        AuroraSensorBase(host, port, slave_id, name, "DSP_ISOLATION", "kΩ", factor=1, precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_OPERATING_HOURS", "h", factor=1, precision=0),

        # Input 2
        AuroraSensorBase(host, port, slave_id, name, "DSP_INPUT_2_VOLTAGE", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_INPUT_2_CURRENT", "A", factor=1, precision=1),

        # Vbulk
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK", "V", factor=1, precision=1),

        # Leakage Currents
        AuroraSensorBase(host, port, slave_id, name, "DSP_ILEAK_DC_DC", "A", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_ILEAK_INVERTER", "A", factor=1, precision=1),

        # Pins
        AuroraSensorBase(host, port, slave_id, name, "DSP_PIN1", "W", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PIN2", "W", factor=1, precision=1),

        # DC/DC
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_DC_DC", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY_DC_DC", "Hz", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_DC_DC", "V", factor=1, precision=1),

        # Average Grid Voltage
        AuroraSensorBase(host, port, slave_id, name, "DSP_AVERAGE_GRID_VOLTAGE", "V", factor=1, precision=1),

        # Vbulk Mid
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_MID", "V", factor=1, precision=1),

        # Power Peaks
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_PEAK", "W", factor=1, precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_PEAK_TODAY", "W", factor=1, precision=0),

        # Neutral
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_NEUTRAL", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_NEUTRAL_PHASE", "V", factor=1, precision=1),

        # Wind Generator
        AuroraSensorBase(host, port, slave_id, name, "DSP_WIND_GENERATOR_FREQUENCY", "Hz", factor=1, precision=1),

        # Phase Currents
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_R", "A", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_S", "A", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT_PHASE_T", "A", factor=1, precision=1),

        # Phase Frequencies
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_R", "Hz", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_S", "Hz", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FREQUENCY_PHASE_T", "Hz", factor=1, precision=1),

        # Vbulk Plus/Minus
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_PLUS", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VBULK_MINUS", "V", factor=1, precision=1),

        # Temperatures
        AuroraSensorBase(host, port, slave_id, name, "DSP_SUPERVISOR_TEMPERATURE", "°C", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALIM_TEMPERATURE", "°C", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_HEAT_SINK_TEMPERATURE", "°C", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_1", "°C", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_2", "°C", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE_3", "°C", factor=1, precision=1),

        # Fan Speeds
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_1_SPEED", "rpm", factor=1, precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_2_SPEED", "rpm", factor=1, precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_3_SPEED", "rpm", factor=1, precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_4_SPEED", "rpm", factor=1, precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAN_5_SPEED", "rpm", factor=1, precision=0),

        # Power Saturation Limit
        AuroraSensorBase(host, port, slave_id, name, "DSP_POWER_SATURATION_LIMIT", "W", factor=1, precision=0),

        # Bulk Ring Reference
        AuroraSensorBase(host, port, slave_id, name, "DSP_RIFERIMENTO_ANELLO_BULK", "", factor=1, precision=1),

        # Micro Panel Voltage
        AuroraSensorBase(host, port, slave_id, name, "DSP_VPANEL_MICRO", "V", factor=1, precision=1),

        # Phase Voltages
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_R", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_S", "V", factor=1, precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE_PHASE_T", "V", factor=1, precision=1),
    ]
    add_entities(sensors, True)
