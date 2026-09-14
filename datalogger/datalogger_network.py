"""
Gray Greenridge
GeNeLa
2026

This script has the datalogger continuously search for an AP and then connect if its strength is sufficient.
"""

import subprocess
import yaml
import time

from rich import print

# Load config
with open("conf.yaml", "r") as file:
    config = yaml.safe_load(file)

ap_ssid = config["networking"]["ap_ssid"]
ap_pw = config["networking"]["ap_pw"]
ap_scan_interval: float = config["networking"]["ap_scan_interval"]
ap_threshold: int = config["networking"].get("ap_threshold", 50)


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

    while True:
        if is_already_connected():
            print(f"Already connected to {ap_ssid}. Skipping search...")
        else:
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
