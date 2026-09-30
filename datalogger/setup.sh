python3 -m venv ./daf_datalogger_venv/
./daf_datalogger_venv/bin/pip install -r requirements.txt
sudo mv datalogger.service /etc/systemd/system/datalogger.service
sudo mv datalogger_network.service /etc/systemd/system/datalogger_network.service
sudo systemctl daemon-reload
sudo systemctl enable datalogger.service datalogger_network.service
sudo systemctl start datalogger.service datalogger_network.service
