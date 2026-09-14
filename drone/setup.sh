python3 -m venv ./daf_drone_venv/
./daf_drone_venv/bin/pip install -r requirements.txt
sudo mv drone.service /etc/systemd/system/drone.service
sudo systemctl daemon-reload
sudo systemctl enable drone.service
sudo systemctl start drone.service
