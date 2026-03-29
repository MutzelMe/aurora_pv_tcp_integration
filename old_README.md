# Aurora Solar Inverter Integration

This integration provides support for ABB Aurora Solar Inverters via the Waveshare RS485-to-Ethernet adapter.

## Documentation

For more information about the Aurora protocol and the available commands, please refer to the following resources:

- [AuroraPy README](https://github.com/viswind/aurorapy/blob/master/README.md)
- [AuroraPy Documentation](https://github.com/viswind/aurorapy/blob/master/docs/docs.md)

## Alternative Projects

If you are looking for alternative ways to monitor your Aurora inverter, you might want to check out the following projects:

- [esphome-aurora-inverter](https://github.com/michelsciortino/esphome-aurora-inverter): This project provides an ESPHome integration for ABB Aurora inverters using an ESP8266/ESP32 board. It uses the [ABBAurora](https://github.com/jrbenito/ABBAurora) library to handle the Aurora communication protocol.

## Features

- Monitor power generation and energy production.
- Track grid parameters such as voltage, current, and frequency.
- Monitor DC circuit parameters.
- Access diagnostic information and alarms.

## Installation

1. Copy the `custom_components/aurora_solar` directory to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via the Home Assistant UI.

## Configuration

The integration requires the following configuration parameters:

- **Host**: IP address of the Waveshare RS485-to-Ethernet adapter.
- **Port**: Port number of the adapter (default: 5000).
- **Slave ID**: Slave ID of the inverter (default: 2).

## Sensors

The integration provides the following sensors:

### Power and Energy
- Grid Power
- Daily Energy
- Total Energy
- DC Power
- MPPT Power
- Power Peak
- Power Peak Today
- Input Power 1
- Input Power 2

### Grid Parameters
- Grid Voltage
- Grid Current
- Grid Frequency
- Power Factor
- Average Grid Voltage

### DC Circuit
- DC Voltage
- DC Current
- Input 2 Voltage
- Input 2 Current

### Voltages
- Bulk Voltage
- DC/DC Bulk Voltage
- Mid Bulk Voltage
- Positive Bulk Voltage
- Negative Bulk Voltage
- DC/DC Grid Voltage
- Neutral Grid Voltage
- Neutral-Phase Grid Voltage
- Micro Panel Voltage

### Phase Values
- Phase R Grid Current
- Phase S Grid Current
- Phase T Grid Current
- Phase R Frequency
- Phase S Frequency
- Phase T Frequency
- Phase R Grid Voltage
- Phase S Grid Voltage
- Phase T Grid Voltage

### Temperatures
- Temperature
- Radiator Temperature
- Ambient Temperature
- Supervisor Temperature
- Power Supply Temperature
- Heat Sink Temperature
- Temperature 1
- Temperature 2
- Temperature 3

### Fan Speeds
- Fan 1 Speed
- Fan 2 Speed
- Fan 3 Speed
- Fan 4 Speed
- Fan 5 Speed

### Leak Currents
- DC/DC Leakage Current
- Inverter Leakage Current

### Diagnostics
- Isolation Resistance
- Operating Hours
- Power Saturation Limit
- Bulk Ring Reference

### Status and Alarms
- Alarms
- Status
- Events
- Fault Code
- Last Error

### Metadata
- Serial Number
- Model
- Version
- DC/DC Grid Frequency
- Wind Generator Frequency

## Troubleshooting

If you encounter issues with the integration, please check the following:

1. Ensure the Waveshare RS485-to-Ethernet adapter is properly connected to the inverter.
2. Verify the IP address, port, and slave ID configuration.
3. Check the Home Assistant logs for error messages.

## License

This integration is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.
