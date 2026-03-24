# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added weekly energy sensor (DSP_WEEKLY_ENERGY) using cumulated_energy(1)
- Added monthly energy sensor (DSP_MONTHLY_ENERGY) using cumulated_energy(3)
- Added yearly energy sensor (DSP_YEARLY_ENERGY) using cumulated_energy(4)
- Implemented sequential processing for multiple inverters to prevent conflicts
- Increased timeout to 45 seconds for slow inverters
- Added INVERTERS list configuration for multiple inverter support
- Enhanced config flow with actual connection validation using AuroraTCPClient
- Added specific error classes (InvalidHost, InvalidPort) for better error handling
- Translated all config flow comments to English

### Changed
- Translated all German comments and documentation to English
- Updated DSP_TOTAL_ENERGY to use correct cumulated_energy(5) parameter
- Improved error handling and logging in config flow
- Cleaned up duplicate code in __init__.py
- Removed unnecessary backup files and test scripts
- Bumped version to 0.4.0 (MINOR update for new config flow features)

### Fixed
- Fixed merge conflict markers in direct_sensor_test.py
- Removed commented-out duplicate code sections
- Cleaned up Python cache files
- Fixed 'Invalid handler specified' error by ensuring proper domain registration
- Added proper timeout handling for connection tests

### Removed
- Removed alarm_event_status_mapping.md (unnecessary documentation)
- Removed redundant test scripts (local_test.py, test_wrapper.py, local_sensor_check.py)
- Removed all backup files and Python cache directories

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