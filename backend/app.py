from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion  # Added for v2 compatibility
import json
from datetime import datetime
import os

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'noctra_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- MODELS ---
class UserCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- CONFIGURATION ---
TEAM_ID = "team_noctra"
MQTT_BROKER = "broker.benax.rw"
TOPIC_STATUS = f"rfid/{TEAM_ID}/card/status"
TOPIC_PAY = f"rfid/{TEAM_ID}/card/pay"
TOPIC_TOPUP = f"rfid/{TEAM_ID}/card/topup"

# --- MQTT LOGIC ---
def on_connect(client, userdata, flags, rc):
    print(f"[*] MQTT Connected to: {MQTT_BROKER}")
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    with app.app_context():
        try:
            payload = json.loads(msg.payload.decode())
            uid = str(payload.get('uid')).upper().strip()
            if uid:
                card = UserCard.query.filter_by(uid=uid).first()
                if not card:
                    card = UserCard(uid=uid, balance=0)
                    db.session.add(card)
                card.last_seen = datetime.utcnow()
                db.session.commit()
                socketio.emit('update_ui', {
                    "uid": uid,
                    "balance": card.balance,
                    "type": "SCAN",
                    "time": datetime.now().strftime("%H:%M:%S")
                })
        except Exception as e:
            print(f"[!] MQTT Error: {e}")

mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION1)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"MQTT Connection Failed: {e}")

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/pay', methods=['POST'])
def pay():
    data = request.json
    uid = str(data.get('uid')).upper().strip()
    amount = int(data.get('amount', 0))
    card = UserCard.query.filter_by(uid=uid).first()
    if not card:
        return jsonify({"error": "Card not registered"}), 404
    if card.balance >= amount:
        card.balance -= amount
        db.session.add(Transaction(uid=uid, amount=amount, type="PAYMENT"))
        db.session.commit()
        mqtt_client.publish(TOPIC_PAY, json.dumps({"uid": uid, "new_balance": card.balance}))
        res_data = {
            "uid": uid,
            "balance": card.balance,
            "amount": amount,
            "type": "PAYMENT",
            "time": datetime.now().strftime("%H:%M:%S")
        }
        socketio.emit('update_ui', res_data)
        return jsonify({"status": "success", "new_balance": card.balance}), 200
    return jsonify({"error": "Insufficient Funds"}), 400

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    uid = str(data.get('uid')).upper().strip()
    amount = int(data.get('amount', 0))
    if not uid or uid == "--- --- ---":
        return jsonify({"error": "Scan card first"}), 400
    card = UserCard.query.filter_by(uid=uid).first()
    if not card:
        card = UserCard(uid=uid, balance=0)
        db.session.add(card)
    card.balance += amount
    db.session.add(Transaction(uid=uid, amount=amount, type="TOP-UP"))
    db.session.commit()
    mqtt_client.publish(TOPIC_TOPUP, json.dumps({"uid": uid, "new_balance": card.balance}))
    res_data = {
        "uid": uid,
        "balance": card.balance,
        "amount": amount,
        "type": "TOP-UP",
        "time": datetime.now().strftime("%H:%M:%S")
    }
    socketio.emit('update_ui', res_data)
    return jsonify({"status": "success", "new_balance": card.balance}), 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=9254, debug=True, allow_unsafe_werkzeug=True)