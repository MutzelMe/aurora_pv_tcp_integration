# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

