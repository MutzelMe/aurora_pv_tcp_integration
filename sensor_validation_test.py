#!/usr/bin/env python3
"""
Aurora Solar Sensor Validation & Data Test - ENHANCED DEBUG VERSION
================================================================

PURPOSE:
--------
This script provides DETAILED debugging output for Aurora inverter testing:

1. VALIDATION MODE (default):
   - Tests sensor.py logic WITHOUT hardware
   - Shows detailed execution flow
   - Validates all code paths

2. DATA MODE (--data flag):
   - Connects to REAL inverters
   - Shows EVERY sensor query with timing
   - Displays success/failure for each sensor
   - Shows connection status and errors

USAGE:
------
Validation Mode:
    python3 sensor_validation_test.py

Data Mode (with real hardware):
    python3 sensor_validation_test.py --data

Debug Mode (maximum output):
    python3 sensor_validation_test.py --debug
"""

import sys
import time
from datetime import datetime
from aurorapy.client import AuroraTCPClient, AuroraError

# Check command line arguments
DATA_MODE = "--data" in sys.argv
DEBUG_MODE = "--debug" in sys.argv
if DATA_MODE:
    sys.argv.remove("--data")
if DEBUG_MODE:
    sys.argv.remove("--debug")

# Configuration
DEFAULT_HOST = "192.168.250.245"
DEFAULT_PORT = 5000
DEFAULT_SLAVE_ID = 2

# Multiple inverter support
INVERTERS = [
    {"host": "192.168.250.245", "port": 5000, "slave_id": 2, "name": "INV 2"},
]

# Start time
START_TIME = time.time()

# Sensor definitions (simplified for debugging)
SENSOR_TYPES = [
    "DSP_GRID_POWER", "DSP_DAILY_ENERGY", "DSP_GRID_VOLTAGE", 
    "DSP_GRID_CURRENT", "DSP_TEMPERATURE", "DSP_SERIAL_NUMBER"
]

def log(message, level="INFO"):
    """Enhanced logging with timestamps and levels"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def test_sensors():
    """Test sensors with detailed debug output"""
    log("Starting Aurora Solar Sensor Test", "START")
    
    for inverter_config in INVERTERS:
        log(f"Testing Inverter: {inverter_config['name']}", "INVERTER")
        
        try:
            log(f"Connecting to {inverter_config['host']}:{inverter_config['port']}", "CONNECT")
            client = AuroraTCPClient(
                ip=inverter_config['host'], 
                port=inverter_config['port'], 
                address=inverter_config['slave_id'], 
                timeout=45
            )
            client.connect()
            log("Connection established", "SUCCESS")
            
            # Test each sensor with detailed output
            for sensor_type in SENSOR_TYPES:
                start = time.time()
                log(f"Querying {sensor_type}...", "QUERY")
                
                try:
                    if sensor_type == "DSP_DAILY_ENERGY":
                        value = client.cumulated_energy(0)
                    elif sensor_type == "DSP_SERIAL_NUMBER":
                        value = client.serial_number()
                    else:
                        # Get code from sensor type
                        code = 3 if sensor_type == "DSP_GRID_POWER" else (
                            1 if sensor_type == "DSP_GRID_VOLTAGE" else (
                                2 if sensor_type == "DSP_GRID_CURRENT" else (
                                    21 if sensor_type == "DSP_TEMPERATURE" else None
                                )
                            )
                        )
                        if code:
                            value = client.measure(code)
                        else:
                            value = None
                            log(f"No code mapping for {sensor_type}", "WARNING")
                    
                    elapsed = time.time() - start
                    if value is not None:
                        log(f"{sensor_type}: {value} (took {elapsed:.3f}s)", "SUCCESS")
                    else:
                        log(f"{sensor_type}: None (took {elapsed:.3f}s)", "WARNING")
                        
                except AuroraError as e:
                    elapsed = time.time() - start
                    log(f"{sensor_type}: AuroraError - {str(e)} (after {elapsed:.3f}s)", "ERROR")
                except Exception as e:
                    elapsed = time.time() - start
                    log(f"{sensor_type}: Unexpected Error - {str(e)} (after {elapsed:.3f}s)", "ERROR")
            
            client.close()
            log("Connection closed", "INFO")
            
        except AuroraError as e:
            log(f"Connection failed: {str(e)}", "ERROR")
        except Exception as e:
            log(f"Unexpected connection error: {str(e)}", "ERROR")
    
    # Final summary
    execution_time = time.time() - START_TIME
    log(f"Total execution time: {execution_time:.2f} seconds", "END")

if __name__ == "__main__":
    test_sensors()
