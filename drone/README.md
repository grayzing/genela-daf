# drone

The drone portion runs on a Raspberry Pi Model 3B+ with Raspberry Pi OS Bullseye. Setup is simple.

## Host the AP
You need to set up the Pi so that it hosts a hotspot on boot.

```bash
sudo nmcli device wifi hotspot ifname wlan0 ssid genela_daf password ggree024
sudo nmcli connection modify "Hotspot" connection.autoconnect yes
```

To prevent conflicts with saved Wifi connections (like UCR-SECURE), you need to disable them.

```bash
sudo nmcli connection modify "UCR-SECURE" connection.autoconnect no
```

Then reboot the Pi.

```bash
sudo reboot
```

## Host the API endpoint
You'll first need to clone the repo,

```bash
git clone https://github.com/grayzing/genela-daf.git
cd genela-daf
```

Configure `conf.yaml` with the correct destination for downloading the soil data from the logger. Then you will need to go into the `drone` directory and make a venv, installing requirements through `pip`.

```bash
python3 -m venv ./daf_drone_venv/
source ./daf_drone_venv/bin/activate
pip install -r requirements.txt
```

Now that the requirements are installed, you just need to setup the service.

```bash
sudo cp datalogger_collection.service /etc/systemd/system/datalogger_collection.service
sudo systemctl daemon-restart
sudo systemctl enable datalogger_collection.service
sudo systemctl start datalogger_collection.service
```

You can monitor the API endpoint by running

```bash
watch -n1 sudo systemctl status datalogger_collection.service
```
