import can
import cantools
import asyncio
from typing import List
import sys
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.util.date_utils_pandas import PandasDateTimeHelper
import influxdb_client.client.util.date_utils as date_utils
import pandas as pd
from datetime import datetime
import paho.mqtt.client as mqtt
from pprint import pprint
from hashlib import sha256
from random import randbytes
import sqlite3

sqlite_con = sqlite3.connect("sqlite_session_hashes/session_hashes.db") 
sqlite_cur = sqlite_con.cursor()
sqlite_ret = sqlite_cur.execute("CREATE TABLE IF NOT EXISTS session_hash(hash, creation_datetime_iso)")

# Generate hash to delineate data recording sessions, making sure value is unique
while True:
    global session_hash
    session_hash = str(sha256(randbytes(32)).hexdigest())
    sqlite_ret = sqlite_cur.execute("SELECT * FROM session_hash WHERE hash = ?", (session_hash,))
    if sqlite_ret.fetchone() is None:
        break

sqlite_ret = sqlite_cur.execute("INSERT INTO session_hash VALUES (?, ?)", (session_hash, datetime.now().isoformat(),))
sqlite_con.commit()
sqlite_con.close()

print("Session hash: " + session_hash)

# nanosecond precision
date_utils.date_helper = PandasDateTimeHelper()

# influxDb config
influx_token = os.environ.get('INFLUX_TOKEN')
influx_bucket = os.environ.get('INFLUX_BUCKET')
influx_org = os.environ.get('INFLUX_ORGANIZATION')
influx_url = "http://localhost:8086"
influx_client = InfluxDBClient(
    url = influx_url, 
    org = influx_org,
    token = influx_token
)
influx_write_api = influx_client.write_api(write_options = SYNCHRONOUS)

# load DBCs
dbs = {}
arbitration_id_to_db_name_map = {}
for file_name in os.listdir('./dbc'):
    if file_name[-3:] == "dbc":
        dbs[f"{file_name[0:-4]}"] = cantools.database.load_file(f"dbc/{file_name}")
        # map the arbitration IDs to the device name
        for message in dbs[file_name[0:-4]].messages:
            arbitration_id_to_db_name_map[message.frame_id] = file_name[0:-4]


# print out info
for db_name in dbs:
    db = dbs[db_name]
    print(f"db {db_name} messages:")
    messages = db.messages
    pprint(messages)
    for message in messages:
        print(f"{message.name} signals:")
        pprint(db.get_message_by_name(message.name).signals)

# Flush stdout buffer to print the debug messages 
sys.stdout.flush() 

# MQTT publisher setup
clientName = "daq"


def on_connect(client, userdata, flags, reason_codes, properties):
    print("Connected with result code " + str(rc))


def on_publish(client, userdata, result):
    #print("MQTT data published")
    pass


mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, clientName)
mqttClient.on_connect = on_connect
mqttClient.on_publish = on_publish

mqttClient.connect("localhost", 1883)


# CAN Bus stuff
def decode_and_broadcast(msg: can.Message) -> None:
    db = dbs[arbitration_id_to_db_name_map[msg.arbitration_id]] # hashmap; constant lookup time 
    decoded = db.decode_message(msg.arbitration_id, msg.data)
    board_name = db.get_message_by_frame_id(msg.arbitration_id).name
    body = { 
        "measurement": board_name,
        "time": pd.Timestamp(msg.timestamp, unit='s'),
        "fields": decoded,
        "tags": {
            "session_hash": session_hash
        }
    }
    data_point = Point.from_dict(body)
    influx_write_api.write(bucket = influx_bucket, record = data_point)
    for reading in decoded:
        mqttStr = f"{board_name}/{reading}"
        mqttClient.publish(mqttStr, decoded[reading])


async def blocking_reader(reader: can.AsyncBufferedReader) -> None:
    while True:
        await reader.get_message()


async def blocking_session_hash_broadcaster() -> None:
    while True:
        mqttClient.publish("telemetry/session_hash", session_hash)
        await asyncio.sleep(1/10) # once per 100 ms

# Note: if the physical buses don't produce anything even though they should, add CAN filtering 
# Start an interface using the socketcan interface, using the can0 physical device at a 500KHz frequency with the above filters
# bus_one = can.interface.Bus(bustype='socketcan', channel='can0', bitrate=500000)
# bus_two = can.interface.Bus(bustype='socketcan', channel='can1', bitrate=500000)

# Use the virtual CAN interface in lieu of a physical connection
bus_one = can.interface.Bus(bustype="socketcan", channel="vcan0")
bus_two = can.interface.Bus(bustype="socketcan", channel="vcan1")

async def main() -> None:
    reader_bus_one = can.AsyncBufferedReader()
    reader_bus_two = can.AsyncBufferedReader()

    # Logger can be used to log to Influx, it just has to be made (see logic in listeners.py)
    logger = can.Logger("logfile.asc")

    listeners_bus_one: List[can.notifier.MessageRecipient] = [
        decode_and_broadcast,  # Callback function
        reader_bus_one,  # AsyncBufferedReader() listener
        logger,  # Regular Listener object
    ]

    listeners_bus_two: List[can.notifier.MessageRecipient] = [
        decode_and_broadcast, 
        reader_bus_two,  
        logger, 
    ]

    # Create Notifier with an explicit loop to use for scheduling of callbacks
    loop = asyncio.get_running_loop()
    notifier_bus_one = can.Notifier(bus_one, listeners_bus_one, loop=loop)
    notifier_bus_two = can.Notifier(bus_two, listeners_bus_two, loop=loop)

    # Right now, this will be running until the car is turned off, so no end 
    await asyncio.gather(
        blocking_reader(reader_bus_one),
        blocking_reader(reader_bus_two),
        blocking_session_hash_broadcaster()
    )


if __name__ == "__main__":
    asyncio.run(main())
