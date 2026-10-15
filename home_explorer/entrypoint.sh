#!/bin/sh
set -eu
mkdir -p /data
chown -R explorer:explorer /data
exec su explorer -c 'python -B /opt/home-explorer/server.py'
