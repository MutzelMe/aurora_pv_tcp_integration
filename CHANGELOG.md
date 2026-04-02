# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.1] - 2026-04-01

### Added
- **Icon per sensor**: Each sensor now has its own MDI icon defined directly in `SENSOR_DEFINITIONS`
  (e.g. `mdi:solar-power`, `mdi:thermometer`, `mdi:fan`, `mdi:sine-wave`).
  The previous runtime lookup table (`_get_icon_for_sensor_type`) is removed.
- **`async_close()` on coordinator**: TCP connection and singleton entry are removed cleanly
  when the integration is unloaded or reloaded.
- **Config-flow description**: Setup dialog now shows an explanatory text informing users that
  host and port cannot be changed after initial setup.

### Changed
- **`SENSOR_DEFINITIONS` unified**: `SENSOR_REGISTER_MAP`, `ENERGY_CODES` and `STRING_READERS`
  merged into `SENSOR_DEFINITIONS` as a 10th-column `read_spec` + `icon`. Adding or removing a
  sensor now requires editing exactly one line.
- **Options read on every setup**: `async_setup_entry` now reads `config_entry.options` with
  fallback to `config_entry.data`, so changes to Slave-ID and Scan-Interval take effect after
  an automatic reload without restarting HA.
- **Sensor-data read timeout**: Reduced from 120 s to 30 s (sufficient for 68 registers over LAN).
- **`strings.json` / `translations/en.json`**: `slave_id` label added to Options step.

### Fixed
- **`asyncio.get_event_loop()` deprecated**: Replaced with `asyncio.get_running_loop()` in all
  three call sites (health-check, reconnect, sensor read).
- **`CONNECTION_CLASS` removed**: `config_entries.CONN_CLASS_LOCAL_POLL` was removed from HA
  in 2021; the attribute caused a warning on every startup.
- **TCP socket leak on unload**: `async_unload_entry` now calls `coordinator.async_close()`,
  which closes the socket and removes the singleton so a subsequent reload starts clean.
- **`_create_sensors` tuple unpack**: Fixed `ValueError` caused by unpacking 8 variables from
  9-element tuples after the `read_spec` column was added.
- **Unused imports**: `DEFAULT_PORT` and `DEFAULT_SLAVE_ID` removed from `sensor.py` imports.

## [0.9.0] - 2026-04-01

### Added
- **HA Energy Dashboard support**: All energy sensors now carry `SensorDeviceClass.ENERGY` and
  `SensorStateClass.TOTAL_INCREASING` / `TOTAL` – they appear automatically in the HA Energy Dashboard.
- **device_info**: All 68 sensors are now grouped under one HA device per inverter
  (manufacturer “ABB / Power-One”, model “Aurora PVI Inverter”).
- **text_mapping applied**: `DSP_ALARMS`, `DSP_STATUS`, `DSP_FAULT_CODE` now show human-readable
  text (e.g. “No Alarms”, “On”) instead of raw numeric values.
- **Options-Flow reload**: Changing options (e.g. scan interval) now triggers an automatic
  integration reload without restarting HA.
- **Translations**: `scan_interval`, `cannot_connect` and `unknown` error keys added to
  `translations/en.json`; `strings.json` created.
- **Default constants**: `DEFAULT_PORT`, `DEFAULT_SLAVE_ID`, `DEFAULT_SCAN_INTERVAL` centralised
  in `const.py` – no more hardcoded values spread across files.
- **DataUpdateCoordinator**: All 68 sensors now share one TCP session per poll cycle.
  `_fetch_all_sync()` reads every register in one executor call. Sensors show unavailable
  automatically when the coordinator fails – no per-sensor error handling needed.
- **README**: Energy Dashboard setup guide and full sensor list (68 sensors) added.

### Changed
- **Sensor names**: Full type name used (e.g. "Grid Voltage Phase R" instead of just "R").
- **manifest.json**: Version bumped to 0.9.0; broken `icons.icon` entry removed.
- **hacs.json**: Minimum HA version updated to `2025.11.0`.
- **sensor.py**: Reduced from ~850 lines to 471 lines (~45%) by extracting `SENSOR_DEFINITIONS`,
  `SENSOR_REGISTER_MAP`, `ENERGY_CODES`, `STRING_READERS` as module-level constants and
  introducing `_create_sensors()` factory.

### Fixed
- **DSP_PF register collision**: `DSP_PF` (Power Factor) removed from `SENSOR_REGISTER_MAP`
  – both `DSP_PF` and `DSP_PIN2` incorrectly shared register 9. `DSP_PIN2` retains register 9.
- **`_disabled_sensors` dead code**: Redundant second error-tracking mechanism removed.
- **German log messages**: All log strings unified to English.
- **Circuit breaker gap**: `except Exception` block now also increments failure counter.

## [0.8.0] - 2026-03-29

### Added
- **Performance Optimization**: Implemented connection pooling to reduce TCP connections from 140+ to 2 per update cycle
- **AuroraConnectionPool**: New singleton-based connection management system with automatic health checks
- **Async Support**: Converted sensor update method to async_update() for better performance
- **Automatic Reconnection**: Connection pool automatically handles connection failures and reconnects

### Changed
- **Major Performance Improvement**: Reduced TCP connection overhead by 98% (140+ connections → 2 connections per cycle)
- **Sensor Update Method**: Changed from synchronous update() to asynchronous async_update()
- **Connection Management**: Replaced direct AuroraTCPClient instantiation with pooled connections

### Fixed
- **Memory Leaks**: Connection pool automatically manages connection lifecycle with 5-minute timeout
- **Connection Stability**: Health checks prevent using stale or failed connections
- **Race Conditions**: Async locking prevents concurrent connection creation issues

### Performance
- **Connection Reduction**: 98% fewer TCP connections per update cycle
- **Stability**: Improved adapter stability with fewer connection churn
- **Error Handling**: Automatic recovery from network issues
- **Resource Usage**: Reduced memory footprint with connection reuse

## [0.6.0] - 2026-03-29

### Added
- Added configurable scan interval to prevent "Updating aurora_solar sensor took longer than the scheduled update interval" warnings
- Added scan interval configuration to config flow (default: 60 seconds)
- Added scan interval to options flow for runtime configuration changes
- Added scan interval as extra state attribute for visibility in sensor attributes

### Fixed
- Fixed options flow 500 Internal Server Error by removing manual config_entry assignment
- Fixed AuroraSolarOptionsFlow initialization to properly use parent class

### Changed
- Updated all sensor entities to support configurable scan intervals
- Improved backward compatibility for existing installations

## [0.5.1] - 2024-03-24

### Fixed
- Fixed options flow 500 Internal Server Error by adding proper error handling
- Fixed integration icon display by implementing official Home Assistant icon structure
- Fixed icon format: 64x64 PNG in images/ directory with proper manifest.json "icons" object
- Stabilized unique_id generation for better entity compatibility
- Added missing icons for all sensor types (temperature, frequency, diagnostics, etc.)

## [0.5.0] - 2024-03-24

### Added
- Added comprehensive icon support for all sensor types using Material Design Icons
- Added config flow field for custom inverter naming with guidance for short names
- Added English translations for config flow interface
- Implemented modern async_setup_entry for sensor platform

### Changed
- Improved entity naming to be cleaner and more concise (e.g., "Inverter 1 Grid Power" instead of "aurora solar aurora 3 dsp grid power")
- Enhanced unique_id generation to remove redundant "dsp_" prefixes
- Updated config flow to use user-provided names for better entity organization

## [0.2.2]

### Added
- Initial HACS integration support
- Basic sensor platform implementation
- Config flow for user-friendly setup
- Core Aurora inverter sensors

### Changed
- Improved sensor organization and categorization
- Enhanced error handling and retry logic

### Fixed
- Various bug fixes and stability improvements

## [0.1.0]

### Added
- Initial project setup
- Basic Aurora TCP communication
- Core sensor functionality

