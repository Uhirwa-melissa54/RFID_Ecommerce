from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"

# Real persistence in-memory
card_balances = {}

def on_connect(client, userdata, flags, rc):
    client.subscribe(f"rfid/{TEAM_ID}/card/status")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        uid = payload.get('uid')
        
        if uid not in card_balances:
            card_balances[uid] = 0
            
        # Send scan event to UI
        socketio.emit('update_ui', {
            "uid": uid,
            "balance": card_balances[uid],
            "type": "SCAN"
        })
    except Exception as e:
        print(f"MQTT Error: {e}")

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
    amount = int(data.get('amount', 0))

    if uid in card_balances:
        card_balances[uid] += amount
        new_balance = card_balances[uid]
        
        # Notify UI of transaction for history table
        socketio.emit('update_ui', {
            "uid": uid,
            "balance": new_balance,
            "amount": amount,
            "type": "TOP-UP"
        })
        
        # Optional: Publish back to MQTT if hardware needs to know
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps({"uid": uid, "new_balance": new_balance}))
        
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001)