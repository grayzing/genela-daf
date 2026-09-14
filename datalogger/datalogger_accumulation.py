"""
Gray Greenridge
GeNeLa
ggree024@ucr.edu

This script queries the SDI12 <-> USB adapter made by Dr. Liu and then saves it so a .csv file
"""
import serial.tools.list_ports
import serial
import time
import yaml
import sys
import os
import csv
from datetime import datetime
from pathlib import Path
from rich import print

# Load configuration
with open("conf.yaml", "r") as file:
    config = yaml.safe_load(file)

sensor_addresses: list[int] = config["sensors"]["sensor_sdi12_addresses"]
soil_kpi_csv_path = config["sensors"]["buffer_csv_path"]
sensor_query_periodicity_s: int = config["sensors"]["sensor_periodicity_s"]

def get_sdi12_to_usb_port() -> serial.Serial | None:
    print("Finding port for SDI12 <-> USB")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        # FTDI chip (VID 0x0403) = SDI-12 adapter
        if port.vid == 0x0403:
            print(f"Found candidate port: {port.device} ({port.description})")
            return serial.Serial(
                            port=port.device,
                            baudrate=9600,
                            bytesize=8,
                            parity="N")
    return None

def ensure_csv_initialized(file_path: str) -> None:
    """Creates the CSV file and writes the header if it doesn't exist.

    This is intentionally cheap (a stat + optional create) so it's safe to call
    before every single append, not just once at boot. That matters because the
    networking component claims the buffer file with an atomic os.replace()
    (buffer.csv -> buffer_sending.csv) before it sends + deletes it, rather than
    deleting buffer.csv in place. After a claim, buffer.csv simply won't exist
    for a moment, and this function transparently recreates it (with header) the
    next time we go to append, so no readings are lost and no torn/headerless
    file is ever produced.
    """
    path = Path(file_path)
    # Ensure directory structure exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write header if file is missing or empty
    if not path.exists() or os.path.getsize(file_path) == 0:
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "sensor_address",
                "volumetric_water_content_percent",
                "soil_temperature_celsius",
                "soil_permittivity",
                "soil_bulk_ec_us_cm",
                "raw_response"
            ])
        print(f"[green]Initialized CSV at: {file_path}[/green]")


def append_row_atomic(file_path: str, row: list) -> None:
    """Appends a single row to the buffer CSV, re-initializing the file first if
    the networking component has rotated/claimed it since our last write.

    Each call opens, writes, and closes the file immediately (no long-lived file
    handle), which is what makes the rename-based handoff with the networking
    component safe: if a rename happens between our ensure_csv_initialized()
    check and this open(), the OS just creates a brand-new file at this path on
    open('a') with O_CREAT -- the renamed-away copy is untouched and still
    correctly holds everything written before the claim.
    """
    ensure_csv_initialized(file_path)
    with open(file_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


# Boot Initialization
ensure_csv_initialized(soil_kpi_csv_path)

ser = get_sdi12_to_usb_port()
time.sleep(2.5) # delay for arduino bootloader and the 1 second delay of the adapter.

if ser is None:
    print("No candidate port found. Is the SDI-12 to USB adapter receiving power? Exiting...")
    sys.exit()

print("[green]Starting measurement accumulation loop...[/green]")

while True:
    for address in sensor_addresses:
        time.sleep(1)
        m_command = f"{address}M!".encode('utf-8')
        ser.write(m_command)
        
        sdi_12_line = ser.readline()
        sdi_12_line = ser.readline()
        
        d_command = f"{address}D0!".encode('utf-8')
        ser.write(d_command)
        
        sdi_12_line = ser.readline()
        sdi_12_line = sdi_12_line[:-2]
        
        raw_decoded = sdi_12_line.decode('utf-8', errors='ignore')
        print(f"Sensor reading for sensor with address {address}: {raw_decoded}")

        try:
            # Parse SDI-12 response payload
            split_sensor_data = raw_decoded.split('+')

            volumetric_water_content_percent = float(split_sensor_data[1])
            soil_temperature_degrees_celsius = float(split_sensor_data[2])
            soil_permittivity = float(split_sensor_data[3])
            soil_bulk_ec = float(split_sensor_data[4])

            # Append parsed payload to CSV (safe against the networking
            # component claiming/rotating the buffer file mid-loop)
            timestamp = datetime.now().isoformat()
            append_row_atomic(soil_kpi_csv_path, [
                timestamp,
                address,
                volumetric_water_content_percent,
                soil_temperature_degrees_celsius,
                soil_permittivity,
                soil_bulk_ec,
                raw_decoded
            ])
            print(f"[blue]Successfully saved measurement for address {address} to CSV.[/blue]")

        except (IndexError, ValueError) as e:
            print(f"[red]Error parsing payload from sensor {address} ('{raw_decoded}'): {e}[/red]")

    time.sleep(sensor_query_periodicity_s)