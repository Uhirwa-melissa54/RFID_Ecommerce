from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import os

# Initialize Flask with the correct template folder location
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'

# SocketIO for real-time neon updates
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Configuration ---
TEAM_ID = "team_pixel" 
MQTT_BROKER = "broker.benax.rw" # Change to your VPS IP or public broker
MQTT_PORT = 1883

# --- MQTT Logic ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[*] SUCCESS: Connected to MQTT Broker at {MQTT_BROKER}")
        # Subscribe to all topics related to this team
        client.subscribe(f"rfid/{TEAM_ID}/card/status")
        client.subscribe(f"rfid/{TEAM_ID}/card/balance")
        # Notify the UI that the backend-to-MQTT bridge is active
        socketio.emit('update_ui', {'system_msg': 'MQTT Bridge Active'})
    else:
        print(f"[!] ERROR: Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[<] MQTT Received: {msg.topic} -> {payload}")
        
        # Forward the data to the Neon Dashboard via WebSockets
        socketio.emit('update_ui', payload)
    except Exception as e:
        print(f"[!] Payload Error: {e}")

# Initialize MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"[!] MQTT Connection Failed: {e}")

# --- HTTP Routes ---

@app.route('/')
def index():
    """Serves the Neon Cyber Dashboard"""
    return render_template('dashboard.html')

@app.route('/topup', methods=['POST'])
def topup():
    """Triggered by the 'Finalize Deposit' button on the UI"""
    try:
        data = request.json
        uid = data.get('uid')
        amount = data.get('amount')
        
        if not uid or not amount:
            return jsonify({"error": "Missing UID or Amount"}), 400

        # Create the command for the ESP8266
        command = {"uid": uid, "amount": amount}
        topic = f"rfid/{TEAM_ID}/card/topup"
        
        mqtt_client.publish(topic, json.dumps(command))
        print(f"[>] MQTT Published: {topic} -> {command}")
        
        return jsonify({"status": "Transaction broadcasted to Edge"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Using eventlet or gevent is recommended for SocketIO, 
    # but for local testing, the default works fine.
    print(f"[*] Cyber Dashboard active at http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=500, debug=True)