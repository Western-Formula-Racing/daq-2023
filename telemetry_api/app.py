import os
from flask import Flask, redirect
from werkzeug.middleware.proxy_fix import ProxyFix
import influxdb_client
import paho.mqtt.client as mqtt
import socket
from flask_cors import CORS
from data_retrieval import InfluxDataRetrieval
import sqlite3
import sys

# Global SQLite setup. SQLite connection needs to be closed every time it's opened, so new connections are made where accessed,
#   due to the volatile nature of the application
sqlite_con = sqlite3.connect("sqlite_session_hashes/session_hashes.db") 
sqlite_cur = sqlite_con.cursor()
sqlite_ret = sqlite_cur.execute("CREATE TABLE IF NOT EXISTS session_hash(hash, creation_datetime_iso)")
sqlite_con.close()

# Unique session identifier
session_hash = ""

# InfluxDB setup
influx_data_retrieval = InfluxDataRetrieval("http://influxdb:8086", os.getenv("INFLUX_TOKEN"), os.getenv("INFLUX_ORGANIZATION"))

# Callback for when MQTT connects to broker 
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("telemetry/#")


# Callback for when MQTT receives a PUBLISH message
def on_message(client, userdata, msg):
    if msg.topic == "telemetry/session_hash":
        global session_hash
        session_hash = msg.payload.decode()


# MQTT setup
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.connect("mqtt_broker", 1883, 5)

# Maintain connection to mqtt_broker on a new thread
mqttc.loop_start()

app = Flask(__name__)
CORS(app)

# Do this to tell flask's built-in server we're behind the nginx proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

@app.route("/", methods=['GET'])
def connection_status():
    # If you're not connected then you'll just get no return lol 
    return { "status": "Connected" }


@app.route("/session_hash/latest", methods=['GET'])
def current_session_hash_get():
    sqlite_con = sqlite3.connect("sqlite_session_hashes/session_hashes.db") 
    sqlite_cur = sqlite_con.cursor()
    sqlite_ret = sqlite_cur.execute("SELECT * FROM session_hash ORDER BY creation_datetime_iso DESC LIMIT 1")
    ret_val = sqlite_cur.fetchall()
    sqlite_con.close()
    return { "session_hash": ret_val[0][0] }


@app.route("/session_hash/all", methods=['GET'])
def session_hashes_get():
    sqlite_con = sqlite3.connect("sqlite_session_hashes/session_hashes.db") 
    sqlite_cur = sqlite_con.cursor()
    sqlite_ret = sqlite_cur.execute("SELECT * FROM session_hash ORDER BY creation_datetime_iso DESC")
    ret_val = sqlite_cur.fetchall()
    sqlite_con.close()
    return { "session_hashes": ret_val }


@app.route("/race_data/all/<session_hash>/<format>", methods=['GET'])
def all_latest_race_data_get_csv(session_hash = None, format = None):
    if format != "csv" and format != "motec": 
        return 'Invalid file format', 400

    if format == "csv":
        zip_name = influx_data_retrieval.writeAllDataPointsWithTagCSV(session_hash)
    elif format == "motec":
        zip_name = influx_data_retrieval.writeAllDataPointsWithTagMotec(session_hash)
    
    return redirect(f'http://{os.environ.get("RPI_HOSTNAME")}.local/static/{zip_name}', 303)

