#!/bin/sh

export INFLUXDB_TOKEN="Q4eNSdRVHhW90YLxNd0DjqJiFWrmsHABRz_vYHyg91we23IPTt6cLywxHRhM9862-kOO7KfZnmpDB5OVVBU9XQ=="
export INFLUXDB_URL="http://10.10.212.138:8086"
export INFLUXDB_ORG="marbles"
export INFLUXDB_BUCKET="rfm69"

cd /home/exhibits/cropcount && /home/exhibits/cropcount/venv/bin/python3 /home/exhibits/cropcount/main.py
