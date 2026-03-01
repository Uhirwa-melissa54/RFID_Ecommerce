from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# Allow CORS so your web dashboard can connect
socketio = SocketIO(app, cors_allowed_origins="*")

TEAM_ID = "team_pixel" # Must match your ESP8266
MQTT_BROKER = "YOUR_BROKER_IP_OR_URL"

# --- MQTT Logic ---
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT with result code {rc}")
    # Subscribe to status and balance updates from ESP8266
    client.subscribe(f"rfid/{TEAM_ID}/card/status")
    client.subscribe(f"rfid/{TEAM_ID}/card/balance")

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    print(f"Received from ESP: {payload}")
    
    # Push the data to the Web Dashboard via WebSocket
    socketio.emit('update_ui', payload)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# --- HTTP Routes ---
@app.route('/topup', methods=['POST'])
def topup():
    """Received from Dashboard via HTTP"""
    data = request.json
    uid = data.get('uid')
    amount = data.get('amount')
    
    # Create the MQTT command for the ESP8266
    command = {"uid": uid, "amount": amount}
    mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps(command))
    
    return jsonify({"status": "Top-up command sent to device"}), 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)