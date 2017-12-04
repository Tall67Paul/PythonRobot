#!/bin/sh
# launcher.sh
# Navigate to the home directory, then to this directory,
# then execute python script, then back home

cd /
cd /media/pi/VOLVO/Robot
python MyPythonRobotController.py
cd /

# This is linked to crontab.  To edit, type "sudo crontab -e"
