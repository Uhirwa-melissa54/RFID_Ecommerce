from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'
# CORS allowed origins "*" is important for SocketIO to talk to the browser
socketio = SocketIO(app, cors_allowed_origins="*")

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"

# --- DATA STORAGE (Volatile - resets on restart) ---
card_balances = {}
transaction_history = [] 

# --- MQTT Logic ---
def on_connect(client, userdata, flags, rc):
    print(f"[*] Backend Bridge Connected to MQTT Broker")
    # Subscribing to the topic the ESP8266 publishes to
    client.subscribe(f"rfid/{TEAM_ID}/card/status")

def on_message(client, userdata, msg):
    try:
        # Decode the raw string from ESP8266
        raw_data = msg.payload.decode()
        print(f"DEBUG: Raw MQTT Received: {raw_data}")
        
        payload = json.loads(raw_data)
        uid = payload.get('uid')
        
        if uid:
            # If it's a new card, initialize balance to 0
            if uid not in card_balances:
                card_balances[uid] = 0
                print(f"[NEW CARD] Registered: {uid}")
            
            data_to_ui = {
                "uid": uid,
                "balance": card_balances[uid],
                "type": "SCAN" 
            }
            
            # Immediately push the scanned card data to the Web Dashboard
            socketio.emit('update_ui', data_to_ui)
            print(f"[SCAN] Card detected: {uid} | Current Balance: {card_balances[uid]}")
        
    except Exception as e:
        print(f"[!] MQTT Message Error: {e}")

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

    # Safety check: if card was scanned, it should be in card_balances
    if uid and uid != "_WAITING_FOR_TAP_":
        # Initialize if not present (safety)
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

        # Store in local history
        transaction_history.append(txn_data)
        
        # 1. Update Hardware (ESP8266 is listening to this)
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps({
            "uid": uid, 
            "new_balance": new_total
        }))
        
        # 2. Update Dashboard via SocketIO
        socketio.emit('update_ui', txn_data)
        
        print(f"[SUCCESS] Top-up {uid}: +{amount} | New: {new_total}")
        return jsonify({"status": "success", "new_balance": new_total}), 200
    
    return jsonify({"error": "No valid card signature found"}), 400

if __name__ == '__main__':
    # host='0.0.0.0' allows other devices on your WiFi to see the dashboard
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)