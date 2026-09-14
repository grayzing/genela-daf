python3 -m venv ./daf_drone_venv/
./daf_drone_venv/bin/pip install -r requirements.txt
sudo mv datalogger.service /etc/systemd/system/datalogger.service
sudo systemctl daemon-reload
sudo systemctl enable datalogger.service
sudo systemctl start datalogger.service
