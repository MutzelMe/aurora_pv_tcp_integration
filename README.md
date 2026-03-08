# WORK IN PROGRESS

# Aurora Inverter - TCP Integration for HomeAssistant
This Integration makes use of a RS485 to Ethernet converter, like this one (non PoE Version)
[Waveshare rs485 to Ehternet](https://www.waveshare.com/rs485-to-eth-b.htm).
In some cases, Aurora/ABB PowerOne inverters are attached to a PMU PVI and this PMU-PVI uses a proprietary aurora protocol.
There is a python library (aurorapy) which is used by this integration to read Inverter Data.


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
5. Enter the waveshare details 
   Per inverter (slave ID on the Bus), you can add a device in Homeassistant
   If you don't know the slave ID of your inverter, you can find it in the settings menu of the inverter (consult the inverter manual)
<img width="50%" height="50%" alt="Homeassistant Configuration Menu" src="https://github.com/user-attachments/assets/c7be00ae-4df7-4115-b179-a5d7a6d3891a" />

