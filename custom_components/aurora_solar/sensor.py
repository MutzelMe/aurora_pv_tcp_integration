class AuroraSensor(SensorEntity):
    def __init__(self, host, port, slave_id, name):
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._name = name
        self._state = None
        self._attr_native_unit_of_measurement = "W"
        self._attr_name = f"{name} Leistung"

    def update(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((self._host, self._port))
            # Slave-ID in den Befehl einbauen (z. B. \x02 für Slave 2, \x03 für Slave 3)
            command = bytes([self._slave_id]) + b"\x30\x33\x0D"
            s.send(command)
            response = s.recv(1024)
            s.close()
            if response and len(response) >= 2:
                self._state = int.from_bytes(response[:2], byteorder='little', signed=True)
            else:
                self._state = None
        except Exception as e:
            self._state = None
            _LOGGER.error(f"Fehler bei der Abfrage: {e}")
