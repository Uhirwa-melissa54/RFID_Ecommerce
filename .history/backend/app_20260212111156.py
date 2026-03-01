from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'cyber_secret_key_99'
socketio = SocketIO(app, cors_allowed_origins="*")

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"

# --- Simple Database ---
# This stores the balance for every card scanned.
card_database = {}

def on_connect(client, userdata, flags, rc):
    print(f"[*] Connected to MQTT Broker")
    client.subscribe(f"rfid/{TEAM_ID}/card/status")
    client.subscribe(f"rfid/{TEAM_ID}/card/balance")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        uid = payload.get('uid')
        
        # If this is a new card, give it a starting balance of 0
        if uid not in card_database:
            card_database[uid] = 0
            
        # Update the payload with the ACTUAL balance from our database
        payload['balance'] = card_database[uid]
        
        print(f"[<] Processing {uid} | Current Balance: {card_database[uid]}")
        socketio.emit('update_ui', payload)
    except Exception as e:
        print(f"[!] Error: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    uid = data.get('uid')
    amount = int(data.get('amount'))

    if uid in card_database:
        # Update the real balance in our database
        card_database[uid] += amount
        new_balance = card_database[uid]
        
        # Tell the Hardware the update happened
        command = {"uid": uid, "new_balance": new_balance}
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps(command))
        
        # Immediately update the Dashboard
        socketio.emit('update_ui', {"uid": uid, "balance": new_balance, "msg": "Top-up Success"})
        
        return jsonify({"status": "Success", "new_balance": new_balance}), 200
    return jsonify({"error": "Card not found"}), 404

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)