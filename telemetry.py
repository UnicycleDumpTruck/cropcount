"""Send log messages to remote log aggregation servers."""
import threading
import requests
import os
import sys
from loguru import logger
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

# Sensitive data stored in environmental variables
# On Ubuntu, put variables in /etc/environment

bucket = os.environ.get('INFLUXDB_BUCKET')
org = os.environ.get('INFLUXDB_ORG')
token = os.environ.get('INFLUXDB_TOKEN')
url = os.environ.get('INFLUXDB_URL')

client = influxdb_client.InfluxDBClient(
        url=url,
        token=token,
        org=org
)

write_api = client.write_api(write_options=SYNCHRONOUS)

p = influxdb_client.Point("exhibit_boot").tag("location", "OnTheFarm").field("exhibit_name", "conveyor")
try:
    write_api.write(bucket=bucket, org=org, record=p)
except Exception as e:
    logger.warning(f"Error sending boot point to InfluxDB: {e}")

def send_point_in_thread(label, confidence):
    logging_thread = threading.Thread(target=send_point, args=(label, confidence))
    logging_thread.start()

def send_point(label, confidence):
    try:
        p = influxdb_client.Point("conveyed_crop").tag("location", "OnTheFarm").field("label", label).field("confidence", confidence)
        write_api.write(bucket=bucket, org=org, record=p)
    except Exception as e:
        logger.warning(f"Error sending point to InfluxDB: {e}")

def send_log_message(message):
    message_thread = threading.Thread(target=send_msg, args=(message,))
    message_thread.start()
