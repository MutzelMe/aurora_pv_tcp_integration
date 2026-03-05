from aurorapy.client import AuroraTCPClient, AuroraError
import json
from datetime import datetime, timedelta
import time

# Konfiguration
TARGET_IP = "192.168.250.245"
TARGET_PORT = 5000
INVERTER_ADDRESS = 2  # Slave-ID deines Wechselrichters

def measure_with_retry(client, code, retries=2):
    for attempt in range(retries + 1):
        try:
            value = client.measure(code)
            # Filtere nur extrem kleine oder extrem große Werte, die offensichtlich unplausibel sind
            if (abs(value) < 1e-30 and value != 0.0) or abs(value) > 1e10:
                return "Wert unplausibel"
            return value
        except AuroraError as e:
            if "Reading Timeout" in str(e) and attempt < retries:
                time.sleep(1)  # Warte 1 Sekunde vor dem nächsten Versuch
                continue
            return f"Fehler: {str(e)}"
    return "Maximale Anzahl von Wiederholungen erreicht"

def test_comprehensive_data_all_measures():
    try:
        client = AuroraTCPClient(ip=TARGET_IP, port=TARGET_PORT, address=INVERTER_ADDRESS, timeout=10)
        client.connect()

        # Daten abfragen
        data = {}

        # 50: State Request
        try:
            data["global_state"] = client.state(1)
        except AttributeError:
            data["global_state"] = "Methode nicht verfügbar"

        try:
            data["inverter_state"] = client.state(2)
        except AttributeError:
            data["inverter_state"] = "Methode nicht verfügbar"

        try:
            data["DCDC_ch1_state"] = client.state(3)
        except AttributeError:
            data["DCDC_ch1_state"] = "Methode nicht verfügbar"

        try:
            data["DCDC_ch2_state"] = client.state(4)
        except AttributeError:
            data["DCDC_ch2_state"] = "Methode nicht verfügbar"

        try:
            data["alarm_state"] = client.state(5)
        except AttributeError:
            data["alarm_state"] = "Methode nicht verfügbar"

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
        measure_codes = {
            1: "grid_voltage",
            2: "grid_current",
            3: "grid_power",
            4: "frequency",
            5: "vbulk",
            6: "ileak_dc_dc",
            7: "ileak_inverter",
            8: "pin1",
            9: "pin2",
            21: "inverter_temperature",
            22: "booster_temperature",
            23: "input_1_voltage",
            25: "input_1_current",
            26: "input_2_voltage",
            27: "input_2_current",
            28: "grid_voltage_dc_dc",
            29: "grid_frequency_dc_dc",
            30: "isolation_resistance",
            31: "vbulk_dc_dc",
            32: "average_grid_voltage",
            33: "vbulk_mid",
            34: "power_peak",
            35: "power_peak_today",
            36: "grid_voltage_neutral",
            37: "wind_generator_frequency",
            38: "grid_voltage_neutral_phase",
            39: "grid_current_phase_r",
            40: "grid_current_phase_s",
            41: "grid_current_phase_t",
            42: "frequency_phase_r",
            43: "frequency_phase_s",
            44: "frequency_phase_t",
            45: "vbulk_plus",
            46: "vbulk_minus",
            47: "supervisor_temperature",
            48: "alim_temperature",
            49: "heat_sink_temperature",
            50: "temperature_1",
            51: "temperature_2",
            52: "temperature_3",
            53: "fan_1_speed",
            54: "fan_2_speed",
            55: "fan_3_speed",
            56: "fan_4_speed",
            57: "fan_5_speed",
            58: "power_saturation_limit",
            59: "riferimento_anello_bulk",
            60: "vpanel_micro",
            61: "grid_voltage_phase_r",
            62: "grid_voltage_phase_s",
            63: "grid_voltage_phase_t"
        }

        for code, name in measure_codes.items():
            try:
                data[name] = measure_with_retry(client, code)
            except AttributeError:
                data[name] = "Methode nicht verfügbar"
            except Exception as e:
                data[name] = f"Fehler: {str(e)}"

        client.close()

        # Daten als JSON speichern
        with open('comprehensive_data_all_measures.json', 'w') as f:
            json.dump(data, f, indent=4)

        print("Daten erfolgreich in 'comprehensive_data_all_measures.json' gespeichert.")

    except AuroraError as e:
        print(f"Fehler bei der Kommunikation: {str(e)}")
    except Exception as e:
        print(f"Allgemeiner Fehler: {str(e)}")

if __name__ == "__main__":
    test_comprehensive_data_all_measures()
