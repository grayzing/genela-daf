"""
Gray Greenridge
GeNeLa
2026

This script has the datalogger continuously search for an AP and then connect if its strength is sufficient.
"""

import subprocess
import yaml
import time
import requests
import os
import errno
import shutil
import csv
from pathlib import Path
from rich import print

# Load config
with open("conf.yaml", "r") as file:
    config = yaml.safe_load(file)

ap_ssid = config["networking"]["ap_ssid"]
ap_pw = config["networking"]["ap_pw"]
ap_scan_interval: float = config["networking"]["ap_scan_interval"]
ap_threshold: int = config["networking"].get("ap_threshold", 50)
buffer_csv_path: str = config["sensors"]["buffer_csv_path"]
data_reservoir_ip: str = config["networking"]["data_reservoir_ip"]


def is_already_connected():
    """Return True if currently active on the target AP, False otherwise."""
    try:
        # -t gives terse output, -f common fields. 
        # 'active' column will show 'yes' if active.
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,ACTIVE", "device", "wifi", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.splitlines():
            if not line:
                continue
            if ":" in line:
                ssid, active = line.rsplit(":", 1)
                if ssid == ap_ssid and active.lower() == "yes":
                    return True
    except subprocess.CalledProcessError:
        pass
    
    return False


def find_ap():
    """Return the signal strength of the target AP, or None."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL", "device", "wifi", "list"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error scanning for networks: {e.stderr.strip()}")
        return None

    for line in result.stdout.splitlines():
        if not line:
            continue

        if ":" in line:
            ssid, signal = line.rsplit(":", 1)
            if ssid == ap_ssid:
                try:
                    return int(signal)
                except ValueError:
                    continue

    return None


def connect():
    print(f"Connecting to {ap_ssid}...")

    result = subprocess.run(
        [
            "nmcli",
            "device",
            "wifi",
            "connect",
            ap_ssid,
            "password",
            ap_pw,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("Connected successfully!")
        return True

    print("Connection failed:")
    print(result.stderr.strip())
    return False


def main():
    print(f"Monitoring network state for AP: {ap_ssid} (Threshold: {ap_threshold}%)")
    check_file_path = Path("./soil_kpis.csv")

    while True:
        if check_file_path.is_file() and is_already_connected(): # If the Pi is connected to the AP and there are soil_kpis...
            # print(f"Already connected to {ap_ssid}. Skipping search...")
            try:
                url = f'http://{data_reservoir_ip}/soil_kpi_handler'
                
                # Need to copy the soil_kpi file so we can check CSV lines peacefully ^^
                shutil.copy(buffer_csv_path, f"./temp_buffer.csv")
                file_path = buffer_csv_path

                # Open the file in binary read mode
                with open(file_path, 'rb') as file_to_send:
                    # Key name 'file' depends on what the receiving server expects
                    files = {'file': file_to_send}
                    
                    # Send the HTTP POST request
                    response = requests.post(url, files=files)

                # Check the server response
                if response.status_code == 200:
                    print("File sent successfully!")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        row_count = sum(1 for row in reader)
                    if int(response.json()["row_count"]) == row_count:
                        print("Row counts match. Clearing the buffer!")
                        os.remove("temp_buffer.csv")
                        os.remove(buffer_csv_path)
                    else:
                        print("Row count is not the same across drone and datalogger! Possible corruption? Retaining buffer for now.")
                else:
                    print(f"Failed to send file. Status code: {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                underlying_err = e.args[0] if e.args else None
                err_num = getattr(underlying_err, 'errno', None) or getattr(getattr(underlying_err, 'reason', None), 'errno', None)

                # 1. Network is Unreachable (e.g., your local Wi-Fi/Ethernet is down)
                if err_num == errno.ENETUNREACH:
                    print("Network is unreachable. Is the AP's IP address configured correctly in conf.yaml?")
                    
                # 2. No Route to Host (e.g., local connection is fine, but target machine is missing/blocked)
                elif err_num == errno.EHOSTUNREACH:
                    print("No route to host. This is likely normal. I will retry the connection...")
                    
                else:
                    print(f"Other connection issue (Errno {err_num}): {e}\nYou should investigate that.")
                    signal = find_ap()

                    if signal is not None:
                        if signal >= ap_threshold:
                            connect()
                
        elif not is_already_connected():
            print(f"Not connected. Searching for {ap_ssid}...")
            signal = find_ap()

            if signal is None:
                print("AP not detected")
            else:
                if signal >= ap_threshold:
                    print(f"AP detected with strong signal: {signal}% >= {ap_threshold}%")
                    connect()
                else:
                    print(f"AP detected but signal is too weak: {signal}% < {ap_threshold}%")

        time.sleep(ap_scan_interval)


if __name__ == "__main__":
    main()
