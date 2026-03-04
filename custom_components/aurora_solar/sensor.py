"""Support for ABB Aurora Solar Inverters via Waveshare RS485-to-Ethernet adapter."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_HOST, CONF_PORT
import socket
import logging

from .const import DOMAIN, CONF_SLAVE_ID

_LOGGER = logging.getLogger(__name__)

# Vollständige ABB Aurora Befehlsliste (inkl. Diagnose, Seriennummern, Events)
COMMANDS = {
    # Standard-Sensoren
    "DSP_GRID_POWER": b"\x30\x33\x0D",         # Netzleistung (W)
    "DSP_DAILY_ENERGY": b"\x31\x33\x0D",       # Tagesenergie (Wh)
    "DSP_TOTAL_ENERGY": b"\x31\x34\x0D",       # Gesamtenergie (kWh)
    "DSP_GRID_VOLTAGE": b"\x32\x33\x0D",       # Netzspannung (V)
    "DSP_GRID_CURRENT": b"\x33\x33\x0D",       # Netzstrom (A)
    "DSP_GRID_FREQUENCY": b"\x34\x33\x0D",     # Netzfrequenz (Hz)
    "DSP_TEMPERATURE": b"\x35\x33\x0D",        # Temperatur (°C)
    "DSP_DC_VOLTAGE": b"\x36\x33\x0D",         # Gleichspannung (V)
    "DSP_DC_CURRENT": b"\x37\x33\x0D",         # Gleichstrom (A)
    "DSP_DC_POWER": b"\x38\x33\x0D",           # Gleichleistung (W)
    "DSP_EFFICIENCY": b"\x39\x33\x0D",         # Wirkungsgrad (%)
    "DSP_PF": b"\x3A\x33\x0D",                 # Leistungsfaktor
    "DSP_AC_VOLTAGE_PHASE": b"\x3B\x33\x0D",   # Phasenspannung (V)
    "DSP_DC_VOLTAGE2": b"\x3C\x33\x0D",        # Gleichspannung 2 (falls vorhanden)
    "DSP_DC_CURRENT2": b"\x3D\x33\x0D",        # Gleichstrom 2 (falls vorhanden)
    "DSP_RADIATOR_TEMP": b"\x3E\x33\x0D",      # Kühlkörpertemperatur (°C)

    # Diagnose und Status
    "DSP_ALARMS": b"\x50\x33\x0D",             # Alarme (Bitmaske)
    "DSP_STATUS": b"\x51\x33\x0D",             # Betriebsstatus
    "DSP_EVENTS": b"\x52\x33\x0D",             # Ereignisse (z. B. Start/Stop)
    "DSP_FAULT_CODE": b"\x53\x33\x0D",         # Fehlercode
    "DSP_SERIAL_NUMBER": b"\x54\x33\x0D",      # Seriennummer (String)
    "DSP_VERSION": b"\x55\x33\x0D",            # Software-Version
    "DSP_MODEL": b"\x56\x33\x0D",              # Modellbezeichnung
    "DSP_DC_INPUT_VOLTAGE": b"\x57\x33\x0D",   # PV-Eingangsspannung (V)
    "DSP_MPPT_POWER": b"\x58\x33\x0D",         # MPPT-Leistung (W)
    "DSP_ISOLATION": b"\x59\x33\x0D",          # Isolationswiderstand (kΩ)
    "DSP_AMBIENT_TEMP": b"\x5A\x33\x0D",       # Umgebungs-Temperatur (°C)

    # Erweitere Diagnose (falls unterstützt)
    "DSP_DC_POWER2": b"\x5B\x33\x0D",          # MPPT2-Leistung (W)
    "DSP_DC_VOLTAGE3": b"\x5C\x33\x0D",        # MPPT3-Spannung (V)
    "DSP_LAST_ERROR": b"\x5D\x33\x0D",         # Letzter Fehler (Code)
    "DSP_OPERATING_HOURS": b"\x5E\x33\x0D",    # Betriebsstunden (h)
    "DSP_GRID_POWER_LIMIT": b"\x5F\x33\x0D",   # Netzleistungsbegrenzung (%)

    # Spezifische Events (z. B. Relaiszustände)
    "DSP_RELAY_STATUS": b"\x60\x33\x0D",       # Relais-Status
}

class AuroraSensorBase(SensorEntity):
    """Basis-Klasse für alle ABB Aurora Sensoren."""

    def __init__(self, host, port, slave_id, name, command_key, unit, data_index=0, factor=1, is_string=False):
        """Initialisiere den Sensor."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._name = f"{name} {command_key.split('_')[-1].title()}"
        self._command = bytes([slave_id]) + COMMANDS[command_key]
        self._unit = unit
        self._data_index = data_index
        self._factor = factor
        self._is_string = is_string  # Für Seriennummern/Modell
        self._state = None
        self._attr_native_unit_of_measurement = unit if not is_string else None
        self._attr_unique_id = f"aurora_{slave_id}_{command_key.lower()}"

    @property
    def state(self):
        """Aktueller Zustand des Sensors."""
        return self._state

    def update(self):
        """Aktualisiere die Sensordaten."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((self._host, self._port))
                s.send(self._command)
                response = s.recv(1024)
                if response:
                    if self._is_string:
                        # Seriennummer/Modell als String
                        self._state = response[self._data_index:].decode('ascii').strip()
                    elif self._command in (bytes([self._slave_id]) + COMMANDS["DSP_ALARMS"],
                                          bytes([self._slave_id]) + COMMANDS["DSP_FAULT_CODE"]):
                        # Alarme/Fehler als Hex oder Code
                        self._state = f"0x{response[:2].hex()}"
                    else:
                        # Standardwerte (Integer mit Skalierung)
                        self._state = int.from_bytes(
                            response[self._data_index:self._data_index + 2],
                            byteorder='little',
                            signed=True
                        ) * self._factor
                else:
                    self._state = None
                    _LOGGER.warning("Keine Antwort für %s", self._name)
        except Exception as e:
            self._state = None
            _LOGGER.error("Fehler bei %s: %s", self._name, e)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Richte ALLE ABB Aurora Sensoren ein."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    slave_id = config.get(CONF_SLAVE_ID, 2)
    name = config.get("name", f"Aurora WR {slave_id}")

    # Erstelle alle Sensoren für diesen Wechselrichter
    sensors = [
        # Leistung und Energie
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_POWER", "W"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DAILY_ENERGY", "Wh", data_index=2),
        AuroraSensorBase(host, port, slave_id, name, "DSP_TOTAL_ENERGY", "kWh", factor=0.1),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_VOLTAGE", "V"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_CURRENT", "A"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_GRID_FREQUENCY", "Hz"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_PF", "", 0, 0.01),  # Skaliert mit 0.01

        # Gleichstromkreis
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_VOLTAGE", "V"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_CURRENT", "A"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_DC_POWER", "W"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MPPT_POWER", "W"),

        # Temperatur und Umwelt
        AuroraSensorBase(host, port, slave_id, name, "DSP_TEMPERATURE", "°C"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_RADIATOR_TEMP", "°C"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_AMBIENT_TEMP", "°C"),

        # Diagnose (wichtig!)
        AuroraSensorBase(host, port, slave_id, name, "DSP_ALARMS", "", is_string=False),
        AuroraSensorBase(host, port, slave_id, name, "DSP_FAULT_CODE", "", is_string=False),
        AuroraSensorBase(host, port, slave_id, name, "DSP_STATUS", "", is_string=False),
        AuroraSensorBase(host, port, slave_id, name, "DSP_EVENTS", "", is_string=False),
        AuroraSensorBase(host, port, slave_id, name, "DSP_LAST_ERROR", "", is_string=False),

        # Seriennummern und Modell (als String)
        AuroraSensorBase(host, port, slave_id, name, "DSP_SERIAL_NUMBER", "", is_string=True),
        AuroraSensorBase(host, port, slave_id, name, "DSP_MODEL", "", is_string=True),
        AuroraSensorBase(host, port, slave_id, name, "DSP_VERSION", "", is_string=True),

        # Erweiterte Diagnose
        AuroraSensorBase(host, port, slave_id, name, "DSP_ISOLATION", "kΩ"),
        AuroraSensorBase(host, port, slave_id, name, "DSP_OPERATING_HOURS", "h"),
    ]
    add_entities(sensors, True)
