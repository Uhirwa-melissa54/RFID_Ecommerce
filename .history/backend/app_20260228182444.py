import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cyber_secret_key_99'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

TEAM_ID = "team_pixel"
MQTT_BROKER = "broker.benax.rw"
DB_FILE = "rfid_wallet.db"

# --- DATABASE LOGIC (Safe Wallet Update) ---
def init_db():
    """Initializes the database with Wallet and Ledger tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Table for current balances
    cursor.execute('''CREATE TABLE IF NOT EXISTS cards 
                      (uid TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    # Table for transaction history (The Ledger)
    cursor.execute('''CREATE TABLE IF NOT EXISTS ledger 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, 
                       type TEXT, amount INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

def db_transaction(uid, amount, txn_type):
    """Safe Wallet Update: All-or-nothing principle using SQL Transactions."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        
        # 1. Get current balance (or create card if new)
        cursor.execute("SELECT balance FROM cards WHERE uid = ?", (uid,))
        result = cursor.fetchone()
        current_balance = result[0] if result else 0
        
        if not result:
            cursor.execute("INSERT INTO cards (uid, balance) VALUES (?, ?)", (uid, 0))

        new_balance = current_balance + amount
        
        # 2. Check for insufficient funds for payments
        if new_balance < 0:
            raise ValueError("Insufficient Funds")

        # 3. Update Balance
        cursor.execute("UPDATE cards SET balance = ? WHERE uid = ?", (new_balance, uid))
        
        # 4. Record in Ledger
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO ledger (uid, type, amount, timestamp) VALUES (?, ?, ?, ?)",
                       (uid, txn_type, amount, timestamp))
        
        conn.commit()
        return True, new_balance
    except Exception as e:
        conn.rollback() # Safe Wallet Update: Cancel everything if an error occurs
        return False, str(e)
    finally:
        conn.close()

# --- MQTT CONFIG ---
def on_connect(client, userdata, flags, rc):
    print(f"[*] Connected to MQTT Broker | Topic: rfid/{TEAM_ID}/#")
    client.subscribe(f"rfid/{TEAM_ID}/card/status")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        uid = str(payload.get('uid')).upper().strip()
        
        # Fetch current balance from DB to show real data on scan
        conn = sqlite3.connect(DB_FILE)
        res = conn.execute("SELECT balance FROM cards WHERE uid = ?", (uid,)).fetchone()
        conn.close()
        balance = res[0] if res else 0

        socketio.emit('update_ui', {"uid": uid, "balance": balance, "type": "SCAN"})
    except Exception as e:
        print(f"MQTT Error: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# --- ROUTES ---

@app.route('/')
def index():
    # Headset Inventory grouped by Brand for the UI
    inventory = {
        "Sony": [{"model": "WH-1000XM5", "price": 350000}, {"model": "CH-720N", "price": 150000}],
        "Bose": [{"model": "QuietComfort", "price": 300000}, {"model": "Ultra", "price": 450000}],
        "JBL": [{"model": "Tune 760NC", "price": 120000}, {"model": "Live 660BT", "price": 180000}]
    }
    return render_template('dashboard.html', inventory=inventory)

@app.route('/topup', methods=['POST'])
def topup():
    data = request.json
    uid = data.get('uid').upper()
    amount = int(data.get('amount', 0))

    success, result = db_transaction(uid, amount, "TOPUP")
    
    if success:
        # Instruction to ESP8266
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/topup", json.dumps({"uid": uid, "new_balance": result}))
        # WebSocket to Dashboard
        socketio.emit('update_ui', {"uid": uid, "balance": result, "type": "TOP-UP", "amount": amount, "time": datetime.now().strftime("%H:%M:%S")})
        return jsonify({"status": "success", "new_balance": result}), 200
    
    return jsonify({"error": result}), 400

@app.route('/pay', methods=['POST'])
def pay():
    data = request.json
    uid = data.get('uid').upper()
    amount = int(data.get('amount', 0))

    # Payment is negative amount
    success, result = db_transaction(uid, -amount, "PAYMENT")
    
    if success:
        mqtt_client.publish(f"rfid/{TEAM_ID}/card/pay", json.dumps({"uid": uid, "new_balance": result}))
        socketio.emit('update_ui', {"uid": uid, "balance": result, "type": "PAYMENT", "amount": amount, "time": datetime.now().strftime("%H:%M:%S")})
        return jsonify({"status": "success", "new_balance": result}), 200
    
    return jsonify({"error": result}), 400

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)