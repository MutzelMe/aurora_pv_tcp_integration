"""Support for ABB Aurora Solar Inverters via Waveshare RS485-to-Ethernet adapter."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_HOST, CONF_PORT
import logging
from aurorapy.client import AuroraTCPClient, AuroraError

from .const import DOMAIN, CONF_SLAVE_ID

_LOGGER = logging.getLogger(__name__)

# Mapping für lesbare Texte
ALARM_MESSAGES = {
    0x0000: "Keine Alarme",
    0x0001: "Überlastung",
    0x0002: "Netzspannung zu hoch",
    0x0004: "Isolationsfehler",
    0x0008: "Temperatur zu hoch",
    0x0010: "Netzfrequenz außer Toleranz",
}

STATUS_MESSAGES = {
    0x00: "Aus",
    0x01: "Bereit",
    0x02: "Eingeschaltet",
    0x03: "Fehler",
    0x04: "Wartung",
}

FAULT_MESSAGES = {
    0x0000: "Kein Fehler",
    0x0001: "Kurzschluss",
    0x0002: "Kommunikationsfehler",
}

class AuroraSensorBase(SensorEntity):
    """Basis-Klasse für alle ABB Aurora Sensoren."""

    def __init__(self, host, port, slave_id, name, sensor_type, unit, factor=1, precision=2, is_string=False, text_mapping=None):
        """Initialisiere den Sensor."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._name = f"{name} {sensor_type.split('_')[-1].title()}"
        self._sensor_type = sensor_type
        self._unit = unit
        self._factor = factor
        self._precision = precision
        self._is_string = is_string
        self._text_mapping = text_mapping
        self._state = None
        self._attr_native_unit_of_measurement = unit if not is_string else None
        self._attr_unique_id = f"aurora_{slave_id}_{sensor_type.lower()}"

    @property
    def state(self):
        """Aktueller Zustand des Sensors."""
        return self._state

    def update(self):
        """Aktualisiere die Sensordaten."""
        try:
            client = AuroraTCPClient(ip=self._host, port=self._port, address=self._slave_id, timeout=10)
            client.connect()

            if self._sensor_type == "DSP_GRID_POWER":
                self._state = round(client.measure(3) * self._factor, self._precision)
            elif self._sensor_type == "DSP_DAILY_ENERGY":
                self._state = round(client.cumulated_energy(0), self._precision)
            elif self._sensor_type == "DSP_TOTAL_ENERGY":
                self._state = round(client.cumulated_energy(1) * 0.1, self._precision)
            elif self._sensor_type == "DSP_GRID_VOLTAGE":
                self._state = round(client.measure(6), self._precision)
            elif self._sensor_type == "DSP_GRID_CURRENT":
                self._state = round(client.measure(7), self._precision)
            elif self._sensor_type == "DSP_GRID_FREQUENCY":
                self._state = round(client.measure(8), self._precision)
            elif self._sensor_type == "DSP_PF":
                self._state = round(client.measure(9) * 0.01, self._precision)
            elif self._sensor_type == "DSP_DC_VOLTAGE":
                self._state = round(client.measure(10), self._precision)
            elif self._sensor_type == "DSP_DC_CURRENT":
                self._state = round(client.measure(11), self._precision)
            elif self._sensor_type == "DSP_DC_POWER":
                self._state = round(client.measure(12), self._precision)
            elif self._sensor_type == "DSP_TEMPERATURE":
                self._state = round(client.measure(13), self._precision)
            elif self._sensor_type == "DSP_RADIATOR_TEMP":
                self._state = round(client.measure(14), self._precision)
            elif self._sensor_type == "DSP_AMBIENT_TEMP":
                self._state = round(client.measure(15), self._precision)
            elif self._sensor_type == "DSP_MPPT_POWER":
                self._state = round(client.measure(16), self._precision)
            elif self._sensor_type == "DSP_ISOLATION":
                self._state = round(client.measure(17), self._precision)
            elif self._sensor_type == "DSP_OPERATING_HOURS":
                self._state = round(client.measure(18), self._precision)
            elif self._sensor_type == "DSP_SERIAL_NUMBER":
                self._state = client.serial_number()
            elif self._sensor_type == "DSP_VERSION":
                self._state = client.version()
            elif self._sensor_type == "DSP_MODEL":
                self._state = client.version()  # Annahme: Modell wird über version() abgefragt
            elif self._sensor_type == "DSP_EVENTS":
                # Annahme: Ereignisse werden über measure(21) abgefragt
                events = client.measure(21)
                self._state = events  # oder passende Textzuordnung
            elif self._sensor_type == "DSP_LAST_ERROR":
                # Annahme: Letzter Fehler wird über measure(22) abgefragt
                last_error = client.measure(22)
                self._state = last_error  # oder passende Textzuordnung
            elif self._sensor_type == "DSP_ALARMS":
                alarms = client.measure(19)
                self._state = self._text_mapping.get(alarms, "Unbekannt")
            elif self._sensor_type == "DSP_FAULT_CODE":
                fault = client.measure(20)
                self._state = self._text_mapping.get(fault, "Unbekannt")
            elif self._sensor_type == "DSP_STATUS":
                status = client.measure(23)  # Annahme: Status wird über measure(23) abgefragt
                self._state = self._text_mapping.get(status, "Unbekannt")

            client.close()
        except AuroraError as e:
            self._state = None
            _LOGGER.error("Fehler bei %s: %s", self._name, e)
        except Exception as e:
            self._state = None
            _LOGGER.error("Allgemeiner Fehler bei %s: %s", self._name, e)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Richte ALLE ABB Aurora Sensoren ein."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    slave_id = config.get(CONF_SLAVE_ID, 2)
    name = config.get("name", f"Aurora WR {slave_id}")

    # Erstelle alle Sensoren für diesen Wechselrichter
    sensors = [
        # Leistung und Energie
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_POWER", "W", factor=1, precision=2),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DAILY_ENERGY", "Wh", precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TOTAL_ENERGY", "kWh", factor=0.1, precision=2),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE", "V", precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT", "A", precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY", "Hz", precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PF", "", factor=0.01, precision=2),

        # Gleichstromkreis
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_VOLTAGE", "V", precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_CURRENT", "A", precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_POWER", "W", precision=0),

        # Temperatur und Umwelt
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE", "°C", precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_RADIATOR_TEMP", "°C", precision=1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_AMBIENT_TEMP", "°C", precision=1),

        # Diagnose (wichtig!)
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALARMS", "", text_mapping=ALARM_MESSAGES),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAULT_CODE", "", text_mapping=FAULT_MESSAGES),
        AuroraSensorBase(host, port, slave_id, name, "DSP_STATUS", "", text_mapping=STATUS_MESSAGES),
        AuroraSensorBase(host, port, slave_id, name, "DSP_EVENTS", ""),
        AuroraSensorBase(host, port, slave_id, name, "DSP_LAST_ERROR", ""),

        # Seriennummern und Modell (als String)
        AuroraSensorBase(host, port, slave_id, name, "DSP_SERIAL_NUMBER", "", is_string=True),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MODEL", "", is_string=True),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VERSION", "", is_string=True),

        # Erweiterte Diagnose
        AuroraSensorBase(host, port, slave_id, name, "DSP_ISOLATION", "kΩ", precision=0),
        AuroraSensorBase(host, port, slave_id, name, "DSP_OPERATING_HOURS", "h", precision=0),
    ]
    add_entities(sensors, True)
