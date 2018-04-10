#!/bin/bash
source /home/r/py3env/bin/activate
cd /var/www/html/cast
FLASK_APP=backend.py exec python -m flask run --port 3113
