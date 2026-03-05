### This file is used to test the aurora inverter (via TCP) locally without Homeassistant.

from aurorapy.client import AuroraTCPClient, AuroraError
import json
from datetime import datetime, timedelta

# Konfiguration
TARGET_IP = "192.168.250.245"
TARGET_PORT = 5000
INVERTER_ADDRESS = 2  # Slave-ID deines Wechselrichters

def test_comprehensive_data():
    try:
        client = AuroraTCPClient(ip=TARGET_IP, port=TARGET_PORT, address=INVERTER_ADDRESS, timeout=10)
        client.connect()

        # Daten abfragen
        data = {}

        # 50: State Request
        try:
            data["state"] = client.state_request()
        except AttributeError:
            data["state"] = "Methode nicht verfügbar"

        # 58: Version Reading
        try:
            data["version"] = client.version()
        except AttributeError:
            data["version"] = "Methode nicht verfügbar"

        # 63: Serial Number Reading
        try:
            data["serial_number"] = client.serial_number()
        except AttributeError:
            data["serial_number"] = "Methode nicht verfügbar"

        # 65: Manufacturing Week and Year
        try:
            data["manufacturing_week_year"] = client.manufacturing_week_year()
        except AttributeError:
            try:
                data["manufacturing_week_year"] = client.manufacturing_date()
            except AttributeError:
                data["manufacturing_week_year"] = "Methode nicht verfügbar"

        # 68: Cumulated Float Energy Readings
        try:
            data["daily_energy_float"] = client.cumulated_energy(period=1)
            data["week_energy_float"] = client.cumulated_energy(period=2)
            data["month_energy_float"] = client.cumulated_energy(period=3)
            data["year_energy_float_global"] = client.cumulated_energy(period=4, global_measure=True)
            data["total_energy_float_global"] = client.cumulated_energy(period=6, global_measure=True)
        except AttributeError:
            data["cumulated_float_energy"] = "Methode nicht verfügbar"

        # 70: Time/Date Reading
        try:
            seconds_since_2000 = client.time_date()
            data["time_date"] = (datetime(2000, 1, 1) + timedelta(seconds=seconds_since_2000)).strftime("%Y-%m-%d %H:%M:%S")
        except AttributeError:
            data["time_date"] = "Methode nicht verfügbar"

        # 72: Firmware Release Reading
        try:
            data["firmware_micro_release_C"] = client.firmware(3)
        except AttributeError:
            data["firmware_micro_release_C"] = "Methode nicht verfügbar"

        # 78: Cumulated Energy Readings
        try:
            data["daily_energy"] = client.cumulated_energy(1)
            data["week_energy"] = client.cumulated_energy(2)
            data["month_energy"] = client.cumulated_energy(3)
            data["year_energy"] = client.cumulated_energy(4)
            data["total_energy"] = client.cumulated_energy(5)
        except AttributeError:
            data["cumulated_energy"] = "Methode nicht verfügbar"

        # 86: Last Four Alarms
        try:
            data["last_four_alarms"] = client.alarms()
        except AttributeError:
            data["last_four_alarms"] = "Methode nicht verfügbar"

        # 59: Measure Requests
        try:
            data["grid_voltage"] = client.measure(1)
            data["grid_current"] = client.measure(2)
            data["grid_power"] = client.measure(3)
            data["frequency"] = client.measure(4)
            data["inverter_temperature"] = client.measure(21)
            data["booster_temperature"] = client.measure(22)
            data["input_1_voltage"] = client.measure(23)
            data["input_1_current"] = client.measure(25)
            data["isolation_resistance"] = client.measure(30)
        except AttributeError:
            data["measure_requests"] = "Methode nicht verfügbar"

        client.close()

        # Daten als JSON speichern
        with open('comprehensive_data.json', 'w') as f:
            json.dump(data, f, indent=4)

        print("Daten erfolgreich in 'comprehensive_data.json' gespeichert.")

    except AuroraError as e:
        print(f"Fehler bei der Kommunikation: {str(e)}")
    except Exception as e:
        print(f"Allgemeiner Fehler: {str(e)}")

if __name__ == "__main__":
    test_comprehensive_data()
