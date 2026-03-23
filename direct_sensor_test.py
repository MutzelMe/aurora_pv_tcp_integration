#!/usr/bin/env python3
"""
Direct Sensor Test Script.
This script directly tests the Aurora inverter sensors using the AuroraTCPClient.
"""

import sys
import time
from datetime import datetime
from aurorapy.client import AuroraTCPClient, AuroraError

# Configuration
DEFAULT_HOST = "192.168.250.245"
DEFAULT_PORT = 5000
DEFAULT_SLAVE_ID = 2

# Multiple inverter support - add more inverters to this list for sequential processing
INVERTERS = [
    {"host": "192.168.250.245", "port": 5000, "slave_id": 2, "name": "INV 2"},
    # Add more inverters here if needed:
    # {"host": "192.168.250.246", "port": 5000, "slave_id": 3, "name": "INV 3"},
]

# Check for command-line arguments to test specific sensors
TEST_SPECIFIC_SENSORS = False
SPECIFIC_SENSORS = []
if len(sys.argv) > 1:
    TEST_SPECIFIC_SENSORS = True
    SPECIFIC_SENSORS = sys.argv[1:]

# Start time for measuring execution time
START_TIME = time.time()

# --- SENSOR DEFINITIONS FROM sensor.py ---
# Use aurorapy mappings:
from aurorapy.mapping import Mapping

ALARM_MESSAGES = Mapping.GLOBAL_STATES
STATUS_MESSAGES = Mapping.GLOBAL_STATES

FAULT_MESSAGES = {
    0x0000: "No Fault",
    0x0001: "Short Circuit",
    0x0002: "Communication Error",
}

# --- SCALE FACTORS AND UNITS ---
UNITS = {
    "DSP_GRID_POWER": "W",
    "DSP_DAILY_ENERGY": "Wh",
    "DSP_WEEKLY_ENERGY": "Wh",
    "DSP_MONTHLY_ENERGY": "Wh",
    "DSP_YEARLY_ENERGY": "Wh",
    "DSP_TOTAL_ENERGY": "kWh",
    "DSP_GRID_VOLTAGE": "V",
    "DSP_GRID_CURRENT": "A",
    "DSP_GRID_FREQUENCY": "Hz",
    "DSP_TEMPERATURE": "°C",
    "DSP_DC_VOLTAGE": "V",
    "DSP_DC_CURRENT": "A",
    "DSP_DC_POWER": "W",
    "DSP_EFFICIENCY": "%",
    "DSP_PF": "",
    "DSP_AC_VOLTAGE_PHASE": "V",
    "DSP_DC_VOLTAGE2": "V",
    "DSP_DC_CURRENT2": "A",
    "DSP_RADIATOR_TEMP": "°C",
    "DSP_BOOSTER_TEMP": "°C",
    "DSP_IPM_TEMP": "°C",
    "DSP_DSP_TEMP": "°C",
    "DSP_ALARMS": "",
    "DSP_GLOBAL_STATE": "",
    "DSP_INVERTER_STATE": "",
    "DSP_DCDC_CH1_STATE": "",
    "DSP_DCDC_CH2_STATE": "",
    "DSP_ALARM_STATE": "",
    "DSP_STATUS": "",
    "DSP_EVENTS": "",
    "DSP_FAULT_CODE": "",
    "DSP_MODEL": "",
    "DSP_SERIAL_NUMBER": "",
    "DSP_FW_VERSION": "",
    "DSP_DSP_VERSION": "",
    "DSP_LAST_ALARM": "date",
    "DSP_LAST_FAULT": "date",
    "DSP_VERSION_PART1": "",
    "DSP_VERSION_PART2": "",
    "DSP_VERSION_PART3": "",
    "DSP_VERSION_PART4": "",
    "DSP_OPERATION_TIME": "h",
    "DSP_GRID_RELAY_COUNTER": "",
    "DSP_DC_DISCONNECT_COUNTER": "",
    "DSP_PV1_VOLTAGE": "V",
    "DSP_PV1_CURRENT": "A",
    "DSP_PV2_VOLTAGE": "V",
    "DSP_PV2_CURRENT": "A",
    "DSP_PV1_POWER": "W",
    "DSP_PV2_POWER": "W",
    "DSP_GLOBAL_STATE": "",
    "DSP_INVERTER_STATE": "",
    "DSP_DCDC_CH1_STATE": "",
    "DSP_DCDC_CH2_STATE": "",
    "DSP_ALARM_STATE": "",
}

FACTORS = {
    "DSP_GRID_POWER": 1,
    "DSP_DAILY_ENERGY": 1,
    "DSP_WEEKLY_ENERGY": 1,
    "DSP_MONTHLY_ENERGY": 1,
    "DSP_YEARLY_ENERGY": 1,
    "DSP_TOTAL_ENERGY": 0.1,
    "DSP_GRID_VOLTAGE": 0.1,
    "DSP_GRID_CURRENT": 0.1,
    "DSP_GRID_FREQUENCY": 0.01,
    "DSP_TEMPERATURE": 0.1,
    "DSP_DC_VOLTAGE": 0.1,
    "DSP_DC_CURRENT": 0.1,
    "DSP_DC_POWER": 1,
    "DSP_EFFICIENCY": 0.1,
    "DSP_PF": 0.001,
    "DSP_AC_VOLTAGE_PHASE": 0.1,
    "DSP_DC_VOLTAGE2": 0.1,
    "DSP_DC_CURRENT2": 0.1,
    "DSP_RADIATOR_TEMP": 0.1,
    "DSP_BOOSTER_TEMP": 0.1,
    "DSP_IPM_TEMP": 0.1,
    "DSP_DSP_TEMP": 0.1,
    "DSP_ALARMS": 1,
    "DSP_GLOBAL_STATE": 1,
    "DSP_INVERTER_STATE": 1,
    "DSP_DCDC_CH1_STATE": 1,
    "DSP_DCDC_CH2_STATE": 1,
    "DSP_ALARM_STATE": 1,
    "DSP_STATUS": 1,
    "DSP_EVENTS": 1,
    "DSP_FAULT_CODE": 1,
    "DSP_MODEL": 1,
    "DSP_SERIAL_NUMBER": 1,
    "DSP_FW_VERSION": 1,
    "DSP_DSP_VERSION": 1,
    "DSP_LAST_ALARM": 1,
    "DSP_LAST_FAULT": 1,
    "DSP_OPERATION_TIME": 0.1,
    "DSP_GRID_RELAY_COUNTER": 1,
    "DSP_DC_DISCONNECT_COUNTER": 1,
    "DSP_PV1_VOLTAGE": 0.1,
    "DSP_PV1_CURRENT": 0.1,
    "DSP_PV2_VOLTAGE": 0.1,
    "DSP_PV2_CURRENT": 0.1,
    "DSP_PV1_POWER": 1,
    "DSP_PV2_POWER": 1,
    "DSP_GLOBAL_STATE": 1,
    "DSP_INVERTER_STATE": 1,
    "DSP_DCDC_CH1_STATE": 1,
    "DSP_DCDC_CH2_STATE": 1,
    "DSP_ALARM_STATE": 1,
}

# --- HUMAN READABLE SENSOR NAMES ---
SENSOR_NAMES = {
    "DSP_GRID_POWER": "Grid Power",
    "DSP_DAILY_ENERGY": "Daily Energy",
    "DSP_WEEKLY_ENERGY": "Weekly Energy",
    "DSP_MONTHLY_ENERGY": "Monthly Energy",
    "DSP_YEARLY_ENERGY": "Yearly Energy",
    "DSP_TOTAL_ENERGY": "Total Energy",
    "DSP_GRID_VOLTAGE": "Grid Voltage",
    "DSP_GRID_CURRENT": "Grid Current",
    "DSP_GRID_FREQUENCY": "Grid Frequency",
    "DSP_TEMPERATURE": "Temperature",
    "DSP_DC_VOLTAGE": "DC Voltage",
    "DSP_DC_CURRENT": "DC Current",
    "DSP_DC_POWER": "DC Power",
    "DSP_EFFICIENCY": "Efficiency",
    "DSP_PF": "Power Factor",
    "DSP_AC_VOLTAGE_PHASE": "AC Phase Voltage",
    "DSP_DC_VOLTAGE2": "DC Voltage 2",
    "DSP_DC_CURRENT2": "DC Current 2",
    "DSP_RADIATOR_TEMP": "Radiator Temperature",
    "DSP_BOOSTER_TEMP": "Booster Temperature",
    "DSP_IPM_TEMP": "IPM Temperature",
    "DSP_DSP_TEMP": "DSP Temperature",
    "DSP_ALARMS": "Alarms",
    "DSP_GLOBAL_STATE": "Global State",
    "DSP_INVERTER_STATE": "Inverter State",
    "DSP_DCDC_CH1_STATE": "DCDC Channel 1 State",
    "DSP_DCDC_CH2_STATE": "DCDC Channel 2 State",
    "DSP_ALARM_STATE": "Alarm State",
    "DSP_STATUS": "Status",
    "DSP_EVENTS": "Events",
    "DSP_FAULT_CODE": "Fault Code",
    "DSP_MODEL": "Model",
    "DSP_SERIAL_NUMBER": "Serial Number",
    "DSP_FW_VERSION": "Firmware Version",
    "DSP_DSP_VERSION": "DSP Version",
    "DSP_LAST_ALARM": "Last Alarm",
    "DSP_LAST_FAULT": "Last Fault",
    "DSP_OPERATION_TIME": "Operation Time",
    "DSP_GRID_RELAY_COUNTER": "Grid Relay Counter",
    "DSP_DC_DISCONNECT_COUNTER": "DC Disconnect Counter",
    "DSP_PV1_VOLTAGE": "PV1 Voltage",
    "DSP_PV1_CURRENT": "PV1 Current",
    "DSP_PV2_VOLTAGE": "PV2 Voltage",
    "DSP_PV2_CURRENT": "PV2 Current",
    "DSP_PV1_POWER": "PV1 Power",
    "DSP_PV2_POWER": "PV2 Power",
    "DSP_AMBIENT_TEMP": "Ambient Temperature",
    "DSP_MPPT_POWER": "MPPT Power",
    "DSP_ISOLATION": "Isolation Resistance",
    "DSP_OPERATING_HOURS": "Operating Hours",
    "DSP_SERIAL_NUMBER": "Serial Number",
    "DSP_VERSION": "Version",
    "DSP_LAST_ERROR": "Last Error",
    "DSP_INPUT_2_VOLTAGE": "Input 2 Voltage",
    "DSP_INPUT_2_CURRENT": "Input 2 Current",
    "DSP_VBULK": "Bulk Voltage",
    "DSP_ILEAK_DC_DC": "DC/DC Leakage Current",
    "DSP_ILEAK_INVERTER": "Inverter Leakage Current",
    "DSP_PIN1": "Input Power 1",
    "DSP_PIN2": "Input Power 2",
    "DSP_GRID_VOLTAGE_DC_DC": "DC/DC Grid Voltage",
    "DSP_GRID_FREQUENCY_DC_DC": "DC/DC Grid Frequency",
    "DSP_VBULK_DC_DC": "DC/DC Bulk Voltage",
    "DSP_AVERAGE_GRID_VOLTAGE": "Average Grid Voltage",
    "DSP_VBULK_MID": "Mid Bulk Voltage",
    "DSP_POWER_PEAK": "Peak Power",
    "DSP_POWER_PEAK_TODAY": "Today's Peak Power",
    "DSP_GRID_VOLTAGE_NEUTRAL": "Neutral Grid Voltage",
    "DSP_GRID_VOLTAGE_NEUTRAL_PHASE": "Neutral-Phase Grid Voltage",
    "DSP_WIND_GENERATOR_FREQUENCY": "Wind Generator Frequency",
    "DSP_GRID_CURRENT_PHASE_R": "Phase R Grid Current",
    "DSP_GRID_CURRENT_PHASE_S": "Phase S Grid Current",
    "DSP_GRID_CURRENT_PHASE_T": "Phase T Grid Current",
    "DSP_FREQUENCY_PHASE_R": "Phase R Frequency",
    "DSP_FREQUENCY_PHASE_S": "Phase S Frequency",
    "DSP_FREQUENCY_PHASE_T": "Phase T Frequency",
    "DSP_VBULK_PLUS": "Positive Bulk Voltage",
    "DSP_VBULK_MINUS": "Negative Bulk Voltage",
    "DSP_SUPERVISOR_TEMPERATURE": "Supervisor Temperature",
    "DSP_ALIM_TEMPERATURE": "Power Supply Temperature",
    "DSP_HEAT_SINK_TEMPERATURE": "Heat Sink Temperature",
    "DSP_TEMPERATURE_1": "Temperature 1",
    "DSP_TEMPERATURE_2": "Temperature 2",
    "DSP_TEMPERATURE_3": "Temperature 3",
    "DSP_FAN_1_SPEED": "Fan 1 Speed",
    "DSP_FAN_2_SPEED": "Fan 2 Speed",
    "DSP_FAN_3_SPEED": "Fan 3 Speed",
    "DSP_FAN_4_SPEED": "Fan 4 Speed",
    "DSP_FAN_5_SPEED": "Fan 5 Speed",
    "DSP_POWER_SATURATION_LIMIT": "Power Saturation Limit",
    "DSP_RIFERIMENTO_ANELLO_BULK": "Bulk Ring Reference",
    "DSP_VPANEL_MICRO": "Micro Panel Voltage",
    "DSP_GRID_VOLTAGE_PHASE_R": "Phase R Grid Voltage",
    "DSP_GRID_VOLTAGE_PHASE_S": "Phase S Grid Voltage",
    "DSP_GRID_VOLTAGE_PHASE_T": "Phase T Grid Voltage",
    "DSP_GLOBAL_STATE": "Global State",
    "DSP_INVERTER_STATE": "Inverter State",
    "DSP_DCDC_CH1_STATE": "DCDC Channel 1 State",
    "DSP_DCDC_CH2_STATE": "DSP_DCDC Channel 2 State",
    "DSP_ALARM_STATE": "Alarm State",
}

# --- COMPLETE COMMAND LIST (INCLUDING ALL SENSORS) ---
# Mapping from sensor type to code (integer)
SENSOR_CODES = {
    "DSP_GRID_POWER": 3,
    "DSP_DAILY_ENERGY": None,  # special handling
    "DSP_WEEKLY_ENERGY": None,  # special handling
    "DSP_MONTHLY_ENERGY": None,  # special handling
    "DSP_YEARLY_ENERGY": None,  # special handling
    "DSP_TOTAL_ENERGY": None,  # special handling
    "DSP_GRID_VOLTAGE": 1,
    "DSP_GRID_CURRENT": 2,
    "DSP_GRID_FREQUENCY": 4,
    "DSP_TEMPERATURE": 21,
    "DSP_DC_VOLTAGE": 23,
    "DSP_DC_CURRENT": 25,
    "DSP_DC_POWER": 12,
    "DSP_EFFICIENCY": 20,
    "DSP_PF": 9,
    "DSP_AC_VOLTAGE_PHASE": 30,
    "DSP_DC_VOLTAGE2": 24,
    "DSP_DC_CURRENT2": 26,
    "DSP_RADIATOR_TEMP": 22,
    "DSP_BOOSTER_TEMP": 27,
    "DSP_IPM_TEMP": 28,
    "DSP_DSP_TEMP": 29,
    "DSP_ALARMS": 19,
    "DSP_GLOBAL_STATE": None,  # used via client.state(1)
    "DSP_INVERTER_STATE": None,  # used via client.state(2)
    "DSP_DCDC_CH1_STATE": None,  # used via client.state(3)
    "DSP_DCDC_CH2_STATE": None,  # used via client.state(4)
    "DSP_ALARM_STATE": None,  # used via client.state(5)
    "DSP_STATUS": 23,
    "DSP_EVENTS": 21,
    "DSP_FAULT_CODE": 20,
    "DSP_MODEL": None,    # used via client.pn()
    "DSP_SERIAL_NUMBER": None,  # used via client.serial_number()
    "DSP_FW_VERSION": None,  # used via client.version()
    "DSP_DSP_VERSION": None,  # used via client.version()
    "DSP_LAST_ALARM": None,
    "DSP_LAST_FAULT": None,
    "DSP_OPERATION_TIME": 18,
    "DSP_GRID_RELAY_COUNTER": 31,
    "DSP_DC_DISCONNECT_COUNTER": 32,
    "DSP_PV1_VOLTAGE": 33,
    "DSP_PV1_CURRENT": 34,
    "DSP_PV2_VOLTAGE": 35,
    "DSP_PV2_CURRENT": 36,
    "DSP_PV1_POWER": 37,
    "DSP_PV2_POWER": 38,
    "DSP_AMBIENT_TEMP": 15,
    "DSP_MPPT_POWER": 16,
    "DSP_ISOLATION": 30,
    "DSP_OPERATING_HOURS": 18,
    "DSP_SERIAL_NUMBER": None,  # used via client.serial_number()
    "DSP_VERSION": None,  # used via client.version()
    "DSP_LAST_ERROR": 22,
    "DSP_INPUT_2_VOLTAGE": 26,
    "DSP_INPUT_2_CURRENT": 27,
    "DSP_VBULK": 5,
    "DSP_ILEAK_DC_DC": 6,
    "DSP_ILEAK_INVERTER": 7,
    "DSP_PIN1": 8,
    "DSP_PIN2": 9,
    "DSP_GRID_VOLTAGE_DC_DC": 28,
    "DSP_GRID_FREQUENCY_DC_DC": 29,
    "DSP_VBULK_DC_DC": 31,
    "DSP_AVERAGE_GRID_VOLTAGE": 32,
    "DSP_VBULK_MID": 33,
    "DSP_POWER_PEAK": 34,
    "DSP_POWER_PEAK_TODAY": 35,
    "DSP_GRID_VOLTAGE_NEUTRAL": 36,
    "DSP_GRID_VOLTAGE_NEUTRAL_PHASE": 38,
    "DSP_WIND_GENERATOR_FREQUENCY": 37,
    "DSP_GRID_CURRENT_PHASE_R": 39,
    "DSP_GRID_CURRENT_PHASE_S": 40,
    "DSP_GRID_CURRENT_PHASE_T": 41,
    "DSP_FREQUENCY_PHASE_R": 42,
    "DSP_FREQUENCY_PHASE_S": 43,
    "DSP_FREQUENCY_PHASE_T": 44,
    "DSP_GRID_VOLTAGE_PHASE_R": 61,
    "DSP_GRID_VOLTAGE_PHASE_S": 62,
    "DSP_GRID_VOLTAGE_PHASE_T": 63,
    "DSP_SUPERVISOR_TEMPERATURE": 47,
    "DSP_ALIM_TEMPERATURE": 48,
    "DSP_HEAT_SINK_TEMPERATURE": 49,
    "DSP_TEMPERATURE_1": 50,
    "DSP_TEMPERATURE_2": 51,
    "DSP_TEMPERATURE_3": 52,
    "DSP_FAN_1_SPEED": 53,
    "DSP_FAN_2_SPEED": 54,
    "DSP_FAN_3_SPEED": 55,
    "DSP_FAN_4_SPEED": 56,
    "DSP_FAN_5_SPEED": 57,
    "DSP_POWER_SATURATION_LIMIT": 58,
    "DSP_RIFERIMENTO_ANELLO_BULK": 59,
    "DSP_VPANEL_MICRO": 60,
    "DSP_VBULK_PLUS": 45,
    "DSP_VBULK_MINUS": 46,
}

# List of all sensor types to test (from sensor.py)
SENSOR_TYPES = list(SENSOR_CODES.keys()) + [
    "DSP_VERSION_PART1", "DSP_VERSION_PART2", "DSP_VERSION_PART3", "DSP_VERSION_PART4"
]

# If specific sensors are requested, use only those
if TEST_SPECIFIC_SENSORS:
    SENSOR_TYPES = SPECIFIC_SENSORS

def measure_with_retry(client, code, retries=3):
    """Versucht, einen Wert mit Wiederholungen bei Timeout abzufragen."""
    for attempt in range(retries):
        try:
            value = client.measure(code)
            if (abs(value) < 1e-30 and value != 0.0) or abs(value) > 1e10:
                return None
            return value
        except AuroraError as e:
            if "Reading Timeout" in str(e) or "No route to host" in str(e):
                time.sleep(1)
                continue
            return None
    return None

def test_sensors():
    """Test all sensors using the AuroraTCPClient directly."""
    print("\n" + "="*80)
    print(f"Aurora Solar Inverter Sensor Check - {datetime.now()}")
    print("="*80)
    
    # Process inverters sequentially to avoid conflicts
    for inverter_config in INVERTERS:
        print(f"\n--- Testing Inverter {inverter_config['name']} ---")
        
        data = {}
        errors = []
        
        try:
            client = AuroraTCPClient(
                ip=inverter_config['host'], 
                port=inverter_config['port'], 
                address=inverter_config['slave_id'], 
                timeout=45  # Increased timeout for slow inverters
            )
            client.connect()
            
            # Test all sensors
            for sensor_type in SENSOR_TYPES:
                try:
                    if sensor_type == "DSP_DAILY_ENERGY":
                        data[sensor_type] = client.cumulated_energy(0)
                    elif sensor_type == "DSP_WEEKLY_ENERGY":
                        data[sensor_type] = client.cumulated_energy(1)
                    elif sensor_type == "DSP_MONTHLY_ENERGY":
                        data[sensor_type] = client.cumulated_energy(3)
                    elif sensor_type == "DSP_YEARLY_ENERGY":
                        data[sensor_type] = client.cumulated_energy(4)
                    elif sensor_type == "DSP_TOTAL_ENERGY":
                        data[sensor_type] = client.cumulated_energy(5)
                    elif sensor_type == "DSP_ALARMS":
                        data[sensor_type] = client.alarms()
                    elif sensor_type == "DSP_SERIAL_NUMBER":
                        data[sensor_type] = client.serial_number()
                    elif sensor_type == "DSP_MODEL":
                        data[sensor_type] = client.pn()
                    elif sensor_type == "DSP_VERSION":
                        version = client.version()
                        version_parts = str(version).split(' - ')
                        data["DSP_VERSION"] = version
                        if len(version_parts) >= 1:
                            data["DSP_VERSION_PART1"] = version_parts[0]
                        if len(version_parts) >= 2:
                            data["DSP_VERSION_PART2"] = version_parts[1]
                        if len(version_parts) >= 3:
                            data["DSP_VERSION_PART3"] = version_parts[2]
                        if len(version_parts) >= 4:
                            data["DSP_VERSION_PART4"] = version_parts[3]
                    elif sensor_type == "DSP_VERSION_PART1":
                        version = client.version()
                        version_parts = str(version).split(' - ')
                        data["DSP_VERSION_PART1"] = version_parts[0] if len(version_parts) >= 1 else None
                    elif sensor_type == "DSP_VERSION_PART2":
                        version = client.version()
                        version_parts = str(version).split(' - ')
                        data["DSP_VERSION_PART2"] = version_parts[1] if len(version_parts) >= 2 else None
                    elif sensor_type == "DSP_VERSION_PART3":
                        version = client.version()
                        version_parts = str(version).split(' - ')
                        data["DSP_VERSION_PART3"] = version_parts[2] if len(version_parts) >= 3 else None
                    elif sensor_type == "DSP_VERSION_PART4":
                        version = client.version()
                        version_parts = str(version).split(' - ')
                        data["DSP_VERSION_PART4"] = version_parts[3] if len(version_parts) >= 4 else None
                    elif sensor_type == "DSP_GLOBAL_STATE":
                        data[sensor_type] = client.state(1)
                    elif sensor_type == "DSP_INVERTER_STATE":
                        data[sensor_type] = client.state(2)
                    elif sensor_type == "DSP_DCDC_CH1_STATE":
                        data[sensor_type] = client.state(3)
                    elif sensor_type == "DSP_DCDC_CH2_STATE":
                        data[sensor_type] = client.state(4)
                    elif sensor_type == "DSP_ALARM_STATE":
                        data[sensor_type] = client.state(5)
                    else:
                        code = SENSOR_CODES.get(sensor_type)
                        if code is not None:
                            data[sensor_type] = measure_with_retry(client, code)
                        else:
                            data[sensor_type] = None
                except AuroraError as e:
                    errors.append(f"{sensor_type}: {str(e)}")
                except Exception as e:
                    errors.append(f"{sensor_type} (Unexpected): {str(e)}")
            
            client.close()
        except AuroraError as e:
            errors.append(f"Connection Error (Aurora) for {inverter_config['name']}: {str(e)}")
            client.close() if 'client' in locals() else None
        except Exception as e:
            errors.append(f"Connection Error (Unexpected) for {inverter_config['name']}: {str(e)}")
            client.close() if 'client' in locals() else None
    
    # Print results for this inverter
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
        
        for category, sensor_types in categories.items():
            print(f"\n{category}")
            print("-" * len(category))
            for sensor_type in sensor_types:
                if sensor_type in data:
                    unit = UNITS.get(sensor_type, "")
                    # Rename PIN1 and PIN2 to PWR_IN1 and PWR_IN2
                    display_name = sensor_type.replace("DSP_PIN1", "PWR_IN1").replace("DSP_PIN2", "PWR_IN2")
                    # Rename DC Circuit values to DSP_DC_IN1 and DSP_DC_IN2
                    display_name = display_name.replace("DSP_DC_VOLTAGE", "DSP_DC_IN1_VOLTAGE").replace("DSP_DC_CURRENT", "DSP_DC_IN1_CURRENT")
                    # Check for plausible values
                    value = data[sensor_type]
                    if value is not None:
                        if isinstance(value, (int, float)) and abs(value) > 1e-30:
                            print(f"  {display_name}: {value} {unit}")
                        elif isinstance(value, (list, tuple)):
                            print(f"  {display_name}: {value} {unit}")
                        else:
                            print(f"  {display_name}: {value} {unit}")
    
    # Print execution time
    execution_time = time.time() - START_TIME
    print(f"\nTotal execution time: {execution_time:.2f} seconds")
    print("="*80 + "\n")

    # Print results
    categories = {
        "1. Power and Energy": [
            "DSP_GRID_POWER", "DSP_DAILY_ENERGY", "DSP_WEEKLY_ENERGY", "DSP_MONTHLY_ENERGY", "DSP_YEARLY_ENERGY", "DSP_TOTAL_ENERGY",
            "DSP_DC_POWER", "DSP_MPPT_POWER", "DSP_POWER_PEAK",
            "DSP_POWER_PEAK_TODAY", "DSP_PIN1", "DSP_PIN2"
=======
if __name__ == "__main__":
    test_sensors()
=======
    # Print results
    categories = {
        "1. Power and Energy": [
            "DSP_GRID_POWER", "DSP_DAILY_ENERGY", "DSP_WEEKLY_ENERGY", "DSP_MONTHLY_ENERGY", "DSP_YEARLY_ENERGY", "DSP_TOTAL_ENERGY",
            "DSP_DC_POWER", "DSP_MPPT_POWER", "DSP_POWER_PEAK",
            "DSP_POWER_PEAK_TODAY", "DSP_PIN1", "DSP_PIN2"
        ],
    
    # Print execution time
    execution_time = time.time() - START_TIME
    print(f"\nTotal execution time: {execution_time:.2f} seconds")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_sensors()
        "2. Grid Parameters": [
            "DSP_GRID_VOLTAGE", "DSP_GRID_CURRENT", "DSP_GRID_FREQUENCY",
            "DSP_PF", "DSP_AVERAGE_GRID_VOLTAGE"
        ],
        "3. DC Circuit": [
            "DSP_DC_VOLTAGE", "DSP_DC_CURRENT", "DSP_INPUT_2_VOLTAGE",
            "DSP_INPUT_2_CURRENT"
        ],
        "4. Voltages": [
            "DSP_VBULK", "DSP_VBULK_DC_DC", "DSP_VBULK_MID",
            "DSP_VBULK_PLUS", "DSP_VBULK_MINUS", "DSP_GRID_VOLTAGE_DC_DC",
            "DSP_GRID_VOLTAGE_NEUTRAL", "DSP_GRID_VOLTAGE_NEUTRAL_PHASE",
            "DSP_VPANEL_MICRO"
        ],
        "5. Phase Values": [
            "DSP_GRID_CURRENT_PHASE_R", "DSP_GRID_CURRENT_PHASE_S",
            "DSP_GRID_CURRENT_PHASE_T", "DSP_FREQUENCY_PHASE_R",
            "DSP_FREQUENCY_PHASE_S", "DSP_FREQUENCY_PHASE_T",
            "DSP_GRID_VOLTAGE_PHASE_R", "DSP_GRID_VOLTAGE_PHASE_S",
            "DSP_GRID_VOLTAGE_PHASE_T"
        ],
        "6. Temperatures": [
            "DSP_TEMPERATURE", "DSP_RADIATOR_TEMP", "DSP_AMBIENT_TEMP",
            "DSP_SUPERVISOR_TEMPERATURE", "DSP_ALIM_TEMPERATURE",
            "DSP_HEAT_SINK_TEMPERATURE", "DSP_TEMPERATURE_1",
            "DSP_TEMPERATURE_2", "DSP_TEMPERATURE_3"
        ],
        "7. Fan Speeds": [
            "DSP_FAN_1_SPEED", "DSP_FAN_2_SPEED", "DSP_FAN_3_SPEED",
            "DSP_FAN_4_SPEED", "DSP_FAN_5_SPEED"
        ],
        "8. Leak Currents": [
            "DSP_ILEAK_DC_DC", "DSP_ILEAK_INVERTER"
        ],
        "9. Diagnostics": [
            "DSP_ISOLATION", "DSP_OPERATING_HOURS",
            "DSP_POWER_SATURATION_LIMIT", "DSP_RIFERIMENTO_ANELLO_BULK"
        ],
        "10. Status and Alarms": [
            "DSP_ALARMS", "DSP_FAULT_CODE", "DSP_ALARM_STATE",
            "DSP_GLOBAL_STATE", "DSP_INVERTER_STATE", "DSP_DCDC_CH1_STATE",
            "DSP_DCDC_CH2_STATE"
        ],
        "11. Metadata": [
            "DSP_SERIAL_NUMBER", "DSP_MODEL", "DSP_VERSION_PART1", "DSP_VERSION_PART2",
            "DSP_VERSION_PART3", "DSP_VERSION_PART4", "DSP_GRID_FREQUENCY_DC_DC",
            "DSP_WIND_GENERATOR_FREQUENCY"
        ],
    }
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
    
    for category, sensor_types in categories.items():
        print(f"\n{category}")
        print("-" * len(category))
        for sensor_type in sensor_types:
            if sensor_type in data:
                unit = UNITS.get(sensor_type, "")
                # Rename PIN1 and PIN2 to PWR_IN1 and PWR_IN2
                display_name = sensor_type.replace("DSP_PIN1", "PWR_IN1").replace("DSP_PIN2", "PWR_IN2")
                # Rename DC Circuit values to DSP_DC_IN1 and DSP_DC_IN2
                display_name = display_name.replace("DSP_DC_VOLTAGE", "DSP_DC_IN1_VOLTAGE").replace("DSP_DC_CURRENT", "DSP_DC_IN1_CURRENT")
                # Check for plausible values
                value = data[sensor_type]
                if value is not None:
                    if isinstance(value, (int, float)) and abs(value) > 1e-30:
                        print(f"  {display_name}: {value} {unit}")
                    elif isinstance(value, (list, tuple)):
                        print(f"  {display_name}: {value} {unit}")
                    else:
                        print(f"  {display_name}: {value} {unit}")
    
    # Print execution time
    execution_time = time.time() - START_TIME
    print(f"\nExecution time: {execution_time:.2f} seconds")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_sensors()
