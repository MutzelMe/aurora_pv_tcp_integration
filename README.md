# WORK IN PROGRESS

# Aurora Inverter - TCP Integration for HomeAssistant

This Integration makes use of a [Waveshare rs485 to Ehternet](https://www.waveshare.com/rs485-to-eth-b.htm) device to convert RS485 signal to ehternet.
My Aurora/ABB PowerOne Inverter is attached to a PMU PVI and does NOT use TCP Modbus but a proprietary aurora protocol.

There is a python library (aurorapy) which is used by this integration to read Inverter Data.

-----------



Aurora Inverter -> Homeassistant Script for TCP to RS485 Adapters

Add to ```configuration.yaml```
``` yaml
sensor:
  - platform: aurora_solar
    host: 192.168.250.245  # IP deines Waveshare-Adapters
    port: 5000   # anpassen
    slave_id: 2  # Slave-ID deines Wechselrichters
    name: "Aurora Wechselrichter 1"
    scan_interval: 60  # Aktualisiere alle 60 Sekunden statt 30
    
  - platform: aurora_solar
    host: 192.168.250.245  # IP deines Waveshare-Adapters
    port: 5000   # anpassen
    slave_id: 3  # Slave-ID deines Wechselrichters
    name: "Aurora Wechselrichter 2"
    scan_interval: 60  # Aktualisiere alle 60 Sekunden statt 30
```
