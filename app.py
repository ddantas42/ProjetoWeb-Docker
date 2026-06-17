from flask import Flask, render_template
import requests
import os
import paho.mqtt.client as mqtt
import threading
import json

app = Flask(__name__)

IOT_REST_BASE_URL = os.getenv("IOT_REST_BASE_URL", "https://cjsg.ddns.net:8443")
IOT_REST_VERIFY_SSL = os.getenv("IOT_REST_VERIFY_SSL", "false").lower() == "true"

IOT_MQTT_HOST = os.getenv("IOT_MQTT_HOST", "cjsg.ddns.net")
IOT_MQTT_PORT = int(os.getenv("IOT_MQTT_PORT", 1883))
IOT_MQTT_USER = os.getenv("IOT_MQTT_USER", "cd")
IOT_MQTT_PASSWORD = os.getenv("IOT_MQTT_PASSWORD", '1qaz"WSX')


mqtt_state = {
    "weather": {
        "temperature": None,
        "humidity": None,
        "time": None,
        "name": None,
        "latitude": None,
        "longitude": None
    },
    "power": {
        "voltage": None,
        "current": None,
        "power": None,
        "energy": None,
        "frequency": None,
        "powerFactor": None,
        "time": None,
        "name": None,
        "latitude": None,
        "longitude": None
    }
}

lock = threading.Lock()


def on_connect(client, userdata, flags, rc):
    print("MQTT CONNECT RC =", rc)
    client.subscribe("#")


def on_disconnect(client, userdata, rc):
    print("MQTT DISCONNECT RC =", rc)

def on_message(client, userdata, msg):
    global mqtt_state

    payload = msg.payload.decode(errors="ignore")

    print("MQTT MSG:", msg.topic, payload)

    try:
        parsed = json.loads(payload)
    except:
        return

    topic = msg.topic.strip("/")

    with lock:
        if topic not in mqtt_state:
            mqtt_state[topic] = {}

        mqtt_state[topic].update(parsed)

def start_mqtt():
    client = mqtt.Client()

    client.username_pw_set(IOT_MQTT_USER, IOT_MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(IOT_MQTT_HOST, IOT_MQTT_PORT, 60)

    client.loop_start()

    while True:
        pass


@app.route("/")
def index():
    try:
        r = requests.get(
            f"{IOT_REST_BASE_URL}/weather/values/",
            timeout=5,
            verify=IOT_REST_VERIFY_SSL
        )
        data = r.json()
    except Exception as e:
        data = {"error": str(e)}

    with lock:
        mqtt = mqtt_state.copy()

    return render_template("index.html", data=data, mqtt=mqtt)


if __name__ == "__main__":
    t = threading.Thread(target=start_mqtt)
    t.daemon = True
    t.start()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )