from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'
socketio = SocketIO(app, cors_allowed_origins="*")

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"

# --- THE DATABASE ---
card_balances = {}

# --- MQTT Logic ---
def on_connect(client, userdata, flags, rc):
    print(f"[*] Backend Bridge Connected to MQTT Broker")
    client.subscribe(f"rfid/{TEAM_ID}/card/status")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        uid = payload.get('uid')
        
        if uid not in card_balances:
            card_balances[uid] = 0
            
        data_to_ui = {
            "uid": uid,
            "balance": card_balances[uid],
            "type": "SCAN" # Tell UI this is just a scan, not a topup
        }
        
        print(f"[SCAN] Card: {uid} | Balance: {card_balances[uid]}")
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
    # ENSURE your HTML file is named dashboard.html inside the templates folder
    return render_template('dashboard.html')

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    uid = data.get('uid')
    try:
        amount = int(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    if uid and uid in card_balances:
        card_balances[uid] += amount
        new_total = card_balances[uid]
        
        # 1. Update Hardware
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps({
            "uid": uid, 
            "new_balance": new_total
        }))
        
        # 2. Update Dashboard with transaction details
        socketio.emit('update_ui', {
            "uid": uid, 
            "balance": new_total,
            "amount": amount,
            "type": "TOP-UP"
        })
        
        return jsonify({"status": "success", "new_balance": new_total}), 200
    
    return jsonify({"error": "No card scanned"}), 400

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)