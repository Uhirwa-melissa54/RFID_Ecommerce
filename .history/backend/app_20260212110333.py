from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

# Initialize Flask
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'

# SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Configuration ---
TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"
MQTT_PORT = 1883

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[*] SUCCESS: Connected to MQTT Broker at {MQTT_BROKER}")
        client.subscribe(f"rfid/{TEAM_ID}/card/status")
        client.subscribe(f"rfid/{TEAM_ID}/card/balance")
        socketio.emit('update_ui', {'system_msg': 'MQTT Bridge Active'})
    else:
        print(f"[!] ERROR: Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        socketio.emit('update_ui', payload)
    except Exception as e:
        print(f"[!] Payload Error: {e}")

# Initialize MQTT
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"[!] MQTT Connection Failed: {e}")

# --- Routes ---
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    uid = data.get('uid')
    amount = data.get('amount')

    if not uid or not amount:
        return jsonify({"error": "Missing UID or Amount"}), 400

    command = {"uid": uid, "amount": amount}
    topic = f"rfid/{TEAM_ID}/card/topup"
    mqtt_client.publish(topic, json.dumps(command))
    print(f"[>] MQTT Published: {topic} -> {command}")

    return jsonify({"status": "Transaction broadcasted"}), 200

# --- Run Server ---
if __name__ == '__main__':
    print(f"[*] Cyber Dashboard running on http://0.0.0.0:5001")
    # Use 0.0.0.0 to allow all hosts, port 5001 to avoid Windows socket issues
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
