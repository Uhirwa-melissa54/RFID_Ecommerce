from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'
socketio = SocketIO(app, cors_allowed_origins="*")

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"

# --- THE DATABASE (Source of Truth) ---
# Format: {"0xabc123": 5000}
card_balances = {}

# --- MQTT Logic ---
def on_connect(client, userdata, flags, rc):
    print(f"[*] Backend Bridge Connected to MQTT Broker")
    client.subscribe(f"rfid/{TEAM_ID}/card/status")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        uid = payload.get('uid')
        
        # If card is new to the system, initialize it with 0 RWF
        if uid not in card_balances:
            card_balances[uid] = 0
            
        # Send the REAL balance from our database to the dashboard
        data_to_ui = {
            "uid": uid,
            "balance": card_balances[uid]
        }
        
        print(f"[SCAN] Card: {uid} | DB Balance: {card_balances[uid]}")
        socketio.emit('update_ui', data_to_ui)
        
    except Exception as e:
        print(f"[!] MQTT Error: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# --- Routes ---
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    uid = data.get('uid')
    try:
        amount = int(data.get('amount', 0))
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400

    if uid in card_balances:
        # Update the Database
        card_balances[uid] += amount
        new_total = card_balances[uid]
        
        # 1. Update the Hardware (so the ESP8266 knows)
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps({
            "uid": uid, 
            "new_balance": new_total
        }))
        
        # 2. Update the Dashboard UI immediately
        socketio.emit('update_ui', {"uid": uid, "balance": new_total})
        
        print(f"[TOPUP] {uid} | Added: {amount} | New Total: {new_total}")
        return jsonify({"status": "success", "new_balance": new_total}), 200
    
    return jsonify({"error": "No card scanned yet"}), 400

if __name__ == '__main__':
    # Running on 5001 to avoid common Windows conflicts
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)