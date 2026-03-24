# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added comprehensive icon support for all sensor types using Material Design Icons
- Added config flow field for custom inverter naming with guidance for short names
- Added English translations for config flow interface
- Implemented modern async_setup_entry for sensor platform

### Changed
- Improved entity naming to be cleaner and more concise (e.g., "Inverter 1 Grid Power" instead of "aurora solar aurora 3 dsp grid power")
- Enhanced unique_id generation to remove redundant "dsp_" prefixes
- Updated config flow to use user-provided names for better entity organization
- Bumped version to 0.5.0 (MINOR update for icon support and naming improvements)

### Fixed
- Added missing icons for temperature, frequency, power factor, and diagnostic sensors
- Ensured all sensor types have appropriate icons assigned
- Maintained backward compatibility with legacy setup_platform method

## [0.2.2] - 2025-04-01

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

## [0.1.0] - 2025-03-01

### Added
- Initial project setup
- Basic Aurora TCP communication
- Core sensor functionality

[Unreleased]: https://github.com/MutzelMe/aurora_pv_tcp_integration/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/MutzelMe/aurora_pv_tcp_integration/releases/tag/v0.2.2
[0.1.0]: https://github.com/MutzelMe/aurora_pv_tcp_integration/releases/tag/v0.1.0