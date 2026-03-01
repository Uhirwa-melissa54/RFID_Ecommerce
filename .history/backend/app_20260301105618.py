from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'
CORS(app) # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- CONFIGURATION ---
TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"
TOPIC_STATUS = f"rfid/{TEAM_ID}/card/status"
TOPIC_PAY = f"rfid/{TEAM_ID}/card/pay"
TOPIC_TOPUP = f"rfid/{TEAM_ID}/card/topup"

# --- DATA STORE (In-Memory) ---
card_balances = {}
transaction_history = []
active_sessions = {} # Tracks last seen time of a card

# --- MQTT LOGIC ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[*] Connected to MQTT Broker: {MQTT_BROKER}")
        client.subscribe(TOPIC_STATUS)
    else:
        print(f"[!] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        raw_data = msg.payload.decode()
        payload = json.loads(raw_data)
        uid = str(payload.get('uid')).upper().strip()
        
        if uid:
            # If card is new, initialize it
            if uid not in card_balances:
                card_balances[uid] = 0
            
            active_sessions[uid] = datetime.now()
            
            data_to_ui = {
                "uid": uid,
                "balance": card_balances[uid],
                "type": "SCAN",
                "time": datetime.now().strftime("%H:%M:%S")
            }
            
            # Update Web Interface
            socketio.emit('update_ui', data_to_ui)
            print(f"[SCAN] UID: {uid} | Wallet: {card_balances[uid]} RWF")
            
    except Exception as e:
        print(f"[!] MQTT Processing Error: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/pay', methods=['POST'])
def pay():
    data = request.json
    uid = str(data.get('uid')).upper().strip()
    amount = int(data.get('amount', 0))

    if not uid or uid == "--- --- ---":
        return jsonify({"error": "No card detected"}), 400

    if uid in card_balances:
        if card_balances[uid] >= amount:
            card_balances[uid] -= amount
            new_total = card_balances[uid]
            
            txn_data = {
                "uid": uid, 
                "balance": new_total, 
                "amount": amount,
                "type": "PAYMENT", 
                "time": datetime.now().strftime("%H:%M:%S")
            }
            transaction_history.append(txn_data)
            
            # 1. Inform ESP8266 to update the physical card memory
            mqtt_client.publish(TOPIC_PAY, json.dumps({
                "uid": uid, 
                "new_balance": new_total
            }))
            
            # 2. Update Web Dashboard
            socketio.emit('update_ui', txn_data)
            
            return jsonify({"status": "success", "new_balance": new_total}), 200
        else:
            return jsonify({"error": "Insufficient Funds"}), 400
            
    return jsonify({"error": "Card not registered in system"}), 404

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    uid = str(data.get('uid')).upper().strip()
    
    try:
        amount = int(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    if not uid or uid == "--- --- ---":
        return jsonify({"error": "Scan a card first"}), 400

    # Process Top-up
    card_balances[uid] = card_balances.get(uid, 0) + amount
    new_total = card_balances[uid]
    
    txn_data = {
        "uid": uid, 
        "balance": new_total,
        "amount": amount,
        "type": "TOP-UP",
        "time": datetime.now().strftime("%H:%M:%S")
    }
    transaction_history.append(txn_data)
    
    # 1. Inform ESP8266 to write to physical card
    mqtt_client.publish(TOPIC_TOPUP, json.dumps({
        "uid": uid, 
        "new_balance": new_total
    }))
    
    # 2. Update Web Dashboard
    socketio.emit('update_ui', txn_data)
    
    print(f"[TOP-UP] {uid}: +{amount} RWF")
    return jsonify({"status": "success", "new_balance": new_total}), 200

# --- START SERVER ---
if __name__ == '__main__':
    # Using 0.0.0.0 makes the server accessible to the ESP8266 on your local network
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)