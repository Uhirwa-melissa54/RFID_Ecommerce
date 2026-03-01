from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'

# SocketIO needs to allow CORS so the frontend can listen to it
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"

# --- DATA STORAGE ---
card_balances = {}
transaction_history = [] 

# --- MQTT Logic ---
def on_connect(client, userdata, flags, rc):
    print(f"[*] Backend Bridge Connected to MQTT Broker")
    client.subscribe(f"rfid/{TEAM_ID}/card/status")

def on_message(client, userdata, msg):
    try:
        raw_data = msg.payload.decode()
        payload = json.loads(raw_data)
        uid = payload.get('uid')
        
        if uid:
            # Initialize balance if new
            if uid not in card_balances:
                card_balances[uid] = 0
            
            # Prepare data specifically for the frontend
            data_to_ui = {
                "uid": uid,
                "balance": card_balances[uid],
                "type": "SCAN",
                "time": datetime.now().strftime("%H:%M:%S")
            }
            
            # CRITICAL: This sends the data to your dashboard.html
            socketio.emit('update_ui', data_to_ui)
            print(f"[PUSH TO WEB] UID: {uid} | Balance: {card_balances[uid]}")
        
    except Exception as e:
        print(f"[!] MQTT Error: {e}")

# --- Initialize MQTT ---
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
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    if uid and uid != "--- --- ---":
        if uid not in card_balances:
            card_balances[uid] = 0
            
        card_balances[uid] += amount
        new_total = card_balances[uid]
        
        txn_data = {
            "uid": uid, 
            "balance": new_total,
            "amount": amount,
            "type": "TOP-UP",
            "time": datetime.now().strftime("%H:%M:%S")
        }

        # 1. Store locally
        transaction_history.append(txn_data)
        
        # 2. Tell the ESP8266 to update the physical card balance
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps({
            "uid": uid, 
            "new_balance": new_total
        }))
        
        # 3. Tell the Frontend to update the numbers on screen
        socketio.emit('update_ui', txn_data)
        
        print(f"[SUCCESS] Top-up {uid}: +{amount} -> New Total: {new_total}")
        return jsonify({"status": "success", "new_balance": new_total}), 200
    
    return jsonify({"error": "No card selected"}), 400

if __name__ == '__main__':
    # Use port 5001 to match your frontend script
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)