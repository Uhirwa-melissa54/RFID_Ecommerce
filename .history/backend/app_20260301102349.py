from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"

card_balances = {}
transaction_history = [] 

def on_connect(client, userdata, flags, rc):
    print(f"[*] Backend Bridge Connected to MQTT Broker")
    client.subscribe(f"rfid/{TEAM_ID}/card/status")

def on_message(client, userdata, msg):
    try:
        raw_data = msg.payload.decode()
        payload = json.loads(raw_data)
        # Normalize UID to uppercase immediately
        uid = str(payload.get('uid')).upper()
        
        if uid:
            if uid not in card_balances:
                card_balances[uid] = 0
            
            data_to_ui = {
                "uid": uid,
                "balance": card_balances[uid],
                "type": "SCAN" 
            }
            
            socketio.emit('update_ui', data_to_ui)
            print(f"[PUSH TO WEB] UID: {uid} | Balance: {card_balances[uid]}")
        
    except Exception as e:
        print(f"[!] MQTT Message Error: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

@app.route('/')
def index():
    return render_template('dashboard.html')
@app.route('/pay', methods=['POST'])
def pay():
    data = request.json
    uid = str(data.get('uid')).upper().strip()
    amount = int(data.get('amount', 0))

    if uid in card_balances:
        # Safe Wallet Update check
        if card_balances[uid] >= amount:
            card_balances[uid] -= amount
            new_total = card_balances[uid]
            
            txn_data = {
                "uid": uid, "balance": new_total, "amount": amount,
                "type": "PAYMENT", "time": datetime.now().strftime("%H:%M:%S")
            }
            transaction_history.append(txn_data)
            
            # Send MQTT command to ESP8266 to confirm purchase locally
            mqtt_client.publish(f"rfid/{TEAM_ID}/card/pay", json.dumps({"uid": uid, "new_balance": new_total}))
            
            socketio.emit('update_ui', txn_data)
            return jsonify({"status": "success", "new_balance": new_total}), 200
        else:
            return jsonify({"error": "Insufficient Funds"}), 400
            
    return jsonify({"error": "Card not found"}), 404
@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    # Normalize UID from frontend to uppercase
    uid = str(data.get('uid')).upper().strip()
    
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

        transaction_history.append(txn_data)
        
        # This sends the instruction to the ESP8266 to physically write to the card
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps({
            "uid": uid, 
            "new_balance": new_total
        }))
        
        socketio.emit('update_ui', txn_data)
        
        print(f"[SUCCESS] Top-up {uid}: +{amount} | New: {new_total}")
        return jsonify({"status": "success", "new_balance": new_total}), 200
    
    return jsonify({"error": "No valid card signature found"}), 400

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)