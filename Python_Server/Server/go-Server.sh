#!/bin/bash

FLASK_APP=site/Server.py

export FLASK_APP

FLASK_BIN=.env/bin/flask

${FLASK_BIN} run --port 80 --host="0.0.0.0"
