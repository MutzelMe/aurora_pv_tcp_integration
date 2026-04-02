# Aurora Inverter – TCP Integration for Home Assistant
This Integration makes use of a RS485 to Ethernet converter, like this one (non PoE Version)
[Waveshare rs485 to Ehternet](https://www.waveshare.com/rs485-to-eth-b.htm).
In some cases, Aurora/ABB PowerOne inverters are attached to a PMU PVI and this PMU-PVI uses a proprietary aurora protocol.
There is a python library (aurorapy) which is used by this integration to read Inverter Data.

# Alternative Projects

If you are looking for alternative ways to monitor your Aurora inverter, you might want to check out the following projects:

- [esphome-aurora-inverter](https://github.com/michelsciortino/esphome-aurora-inverter): This project provides an ESPHome integration for ABB Aurora inverters using an ESP8266/ESP32 board. It uses the [ABBAurora](https://github.com/jrbenito/ABBAurora) library to handle the Aurora communication protocol.

## Installation
### Aurora/ABB/Firmer PVI-PMU
The integration can be used to connect a [PVI-PMU ](https://www.fimer.com/sites/default/files/PVI-PMU-APP%20NOTE%20DE-RevA.pdf)(for Power management regulation) to a Waveshare adapter.

<img width="8%" height="8%" alt="grafik" src="https://github.com/user-attachments/assets/6ac4940f-07d2-41cf-a4cc-2a5163b88d7f" />


### Waveshare RS485 Adapter
Wavesahre provides adapters to convert between RS485 and ethernet.
There are different Versions of the Waveshare adapter, below you find an example.

<img width="8%" height="8%" alt="Waveshare Adapter" src="https://github.com/user-attachments/assets/cfed2e8c-db85-452a-81ed-bc1653c7f612" />

In case you have a **Power over Ethernet** (PoE) capable Swtich, there is also a PoE version.

There is a DIN Rail (Hutschiene) version and non Din Rail devices.
In all cases, you need to connect Ethernet to your LAN which is accessible by HomeAssistant and also serial wiring (see below).

### Wiring

| PMU-PVI | Waveshare |
|-|-|
|D+|RS485A|
|D-|RS485B|
|G2|GND|

<img width="50%" height="50%"  alt="grafik" src="https://github.com/user-attachments/assets/765f635d-4a2a-4b80-be2b-2f854adaa2e4" />

## Configuration 
### Waveshare Configuration
In case DHCP isnt working for the waveshare, connect it to a PC, set an IP adresse manually on the PC and connect to the adapter (follow the wiki/manual on waveshare site)
After you made the web dashboard reachable, connect to it and set the parameters as follows.

#### Network Settings 
- **IP address**: Change to something that matches your environment and does not overlap with your DHCP pool
- **Gateway**: Change to your default gateway (but it might even work without def. gateway)
- **Device Port**: Use 5000 if possible or later change the port in the integration
- **IP mode** - static

#### Serial Settings
- **Baud Rate**: -> 19200
- **Data bits**: -> 8
- **Parity**: -> NONE
- **Stopbits**: -> 1
- **Flow Control**: -> NONE

#### Multi-Host Settings
- **Protocol**: -> NONE (!!! Important)

Like so:

<img width="1200" height="743" alt="grafik" src="https://github.com/user-attachments/assets/fed6c9f3-cc10-457d-b844-e3b9a1d5050d" />


### Homeassistant Configuration

1. Install HACS
2. Add Repo
   HACS -> click the three Dots -> add custom repo -> As URL enter: https://github.com/MutzelMe/aurora_pv_tcp_integration and choose **Integration**
3. Install Integration
   HACS -> search for "aurora", find this integration, click install
4. Add Integration to HA
   Settings -> Add Integration, search for "aurora", find this integration
5. Enter the Waveshare details
   - **Host**: IP address of the Waveshare adapter
   - **Port**: `5000` (default, change if you configured a different port)
   - **Slave ID**: RS485 address of the inverter (default `2`, check your inverter menu)
   - **Name**: Short display name, e.g. `Inverter 1`
   - **Scan Interval**: How often to poll in seconds (default `60`)

   One config entry = one inverter. Add the integration multiple times for multiple inverters.

<img width="50%" height="50%" alt="Homeassistant Configuration Menu" src="https://github.com/user-attachments/assets/c7be00ae-4df7-4115-b179-a5d7a6d3891a" />

## Energy Dashboard

All energy and power sensors carry the correct `SensorDeviceClass` and `SensorStateClass`,
so they appear in the Home Assistant Energy Dashboard automatically.

Recommended sensors to add:

| Purpose | Sensor |
|---------|--------|
| Solar production (today) | `sensor.<name>_daily_energy` |
| Solar production (total) | `sensor.<name>_total_energy` |
| Current power output | `sensor.<name>_grid_power` |

Go to **Settings → Dashboards → Energy** and add the sensors under *Solar Panels*.

## Available Sensors (68 total)

### Power & Energy
| Sensor | Unit | Notes |
|--------|------|-------|
| Grid Power | W | Current AC output power |
| DC Power | W | DC input power |
| MPPT Power | W | Maximum power point tracker |
| Pin 1 / Pin 2 | W | Input power channels |
| Power Peak | W | All-time peak power |
| Power Peak Today | W | Today’s peak power |
| Daily Energy | Wh | Resets at midnight |
| Weekly / Monthly / Yearly Energy | Wh | Cumulated periods |
| Total Energy | kWh | Lifetime production |

### Grid AC
Grid Voltage, Grid Current, Grid Frequency, Average Grid Voltage,
Grid Voltage Neutral, Grid Voltage Neutral Phase, Power Factor (if supported by inverter)

### Three-Phase
Phase R/S/T: Voltage, Current, Frequency

### DC / Bulk Voltages
DC Voltage, DC Current, Input 2 Voltage/Current, VBulk, VBulk+/−/Mid/DC-DC,
VPanel Micro, Grid Voltage DC-DC, Grid Frequency DC-DC, Wind Generator Frequency,
Ileak DC-DC, Ileak Inverter

### Temperature
Temperature, Radiator Temp, Ambient Temp, Supervisor Temp, Alim Temp,
Heat Sink Temp, Temperature 1/2/3

### Fan Speeds
Fan 1–5 Speed (rpm)

### Diagnostics
Isolation (kΩ), Operating Hours, Alarms, Fault Code, Status, Events, Last Error,
Riferimento Anello Bulk

### Device Info (string)
Serial Number, Model, Version

