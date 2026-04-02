# Aurora Solar Integration - TODO & Roadmap

> Letzter Stand: 01.04.2026 | Version: 0.9.0

---

## ABGESCHLOSSEN

### Hotfix 0.8.1 - HA-Freeze durch blockierende TCP-Calls

| Fix | Datei | Status |
|-----|-------|--------|
| Singleton __init__-Guard (_initialized-Flag) | sensor.py | DONE |
| Health-Check measure(1) -> run_in_executor() + timeout(3s) | sensor.py | DONE |
| measure_with_retry_async() -> run_in_executor() + timeout(5s) | sensor.py | DONE |
| async_update() alle Sensor-Reads -> run_in_executor() + timeout(5s) | sensor.py | DONE |
| Bei Timeout: Pool-Connection schliessen -> Reconnect | sensor.py | DONE |
| Circuit Breaker: Reset auf 0 nach erfolgreichem Read | sensor.py | DONE |
| validate_input(): timeout=120s -> 10s, blocking calls in Executor | config_flow.py | DONE |

### Refactoring 0.8.2 - Code-Komprimierung & Bereinigung (01.04.2026)

| Fix | Datei | Status |
|-----|-------|--------|
| A1 - DSP_PF aus Register-Map entfernt (Register 9 = DSP_PIN2) | sensor.py | DONE |
| A2/A3 - Toten Code entfernt: batch_read_sensors, sync update, sync measure_with_retry | sensor.py | DONE |
| A4 - Alle deutschen Log-Messages -> Englisch, except-Bloecke konsolidiert | sensor.py | DONE |
| A5 - _disabled_sensors entfernt, Circuit Breaker als einziger Fehler-Handler | sensor.py | DONE |
| B1 - DEFAULT_PORT, DEFAULT_SLAVE_ID, DEFAULT_SCAN_INTERVAL in const.py | const.py | DONE |
| B2 - _create_sensors() + beide Setup-Funktionen dedupliziert | sensor.py | DONE |
| B3 - Sensor-Name komplett aus DSP-Prefix generiert (z.B. "Grid Voltage Phase R") | sensor.py | DONE |
| C1 - SensorDeviceClass + SensorStateClass fuer alle 68 Sensoren | sensor.py | DONE |
| SENSOR_DEFINITIONS, SENSOR_REGISTER_MAP, ENERGY_CODES, STRING_READERS als Konstanten | sensor.py | DONE |
| sensor.py von ~850 auf 471 Zeilen reduziert (~45%) | sensor.py | DONE |

### Release 0.9.0 - HA Best Practices (01.04.2026)

| Fix | Datei | Status |
|-----|-------|--------|
| C2 - device_info: alle 68 Sensoren unter einem HA-Geraet gruppiert | sensor.py | DONE |
| C3 - DataUpdateCoordinator: 1 TCP-Session statt 68 pro Zyklus | sensor.py, __init__.py | DONE |
| C4 - text_mapping angewendet: Alarm/Status/Fault im Klartext | sensor.py | DONE |
| C5 - Options-Flow Reload-Listener registriert | sensor.py | DONE |
| C6 - translations/en.json + strings.json vervollstaendigt | translations/, strings.json | DONE |
| D1 - manifest.json v0.9.0, defekten Icon-Eintrag entfernt | manifest.json | DONE |

---

## OFFEN - PHASE D: Projekt-Hygiene

### D2 - README aktualisieren
- [x] Sensor-Liste (68 Sensoren) erganzt
- [x] Energy-Dashboard-Anleitung hinzugefuegt
- [x] Waveshare-Setup mit Port 5000 als Default dokumentiert
- [x] "WORK IN PROGRESS" entfernt

### D3 - hacs.json
- [x] "homeassistant": "2025.4.0" -> "2025.11.0" aktualisiert

### Optional: DSP_PF Register recherchieren
- Power Factor (DSP_PF) ist aktuell nicht im SENSOR_REGISTER_MAP
- Korrektes Register laut ABB Aurora Protokoll-Doku eintragen
- Datei: sensor.py -> SENSOR_REGISTER_MAP