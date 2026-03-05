# aurora_pv_tcp_integration

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