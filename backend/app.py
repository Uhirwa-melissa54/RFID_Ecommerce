from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion  # Added for v2 compatibility
import json
from datetime import datetime
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'noctra_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'agent' or 'sales'

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


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
    performed_by = db.Column(db.String(80))  # username
    role = db.Column(db.String(20))          # agent / sales
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()
    # Seed demo users for Agent and Salesperson roles (idempotent)
    if not User.query.filter_by(username="agent").first():
        agent = User(username="agent", role="agent", password_hash="")
        agent.set_password("password")
        db.session.add(agent)
    if not User.query.filter_by(username="sales").first():
        sales = User(username="sales", role="sales", password_hash="")
        sales.set_password("password")
        db.session.add(sales)
    db.session.commit()


# --- AUTH HELPERS ---
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "role" not in session or session.get("role") not in roles:
                return jsonify({"error": "Unauthorized"}), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator


@app.context_processor
def inject_user():
    return {
        "current_user": {
            "username": session.get("username"),
            "role": session.get("role"),
        }
    }

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
@app.route('/dashboard')
@login_required
def index():
    return render_template('dashboard.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid credentials. Try again.")
    if session.get("user_id"):
        return redirect(url_for("index"))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard_data')
@login_required
def dashboard_data():
    from sqlalchemy import func

    total_topups = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == "TOP-UP"
    ).scalar()
    total_payments = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == "PAYMENT"
    ).scalar()

    card_count = UserCard.query.count()
    total_balance = db.session.query(func.coalesce(func.sum(UserCard.balance), 0)).scalar()

    recent = (
        Transaction.query.order_by(Transaction.timestamp.desc())
        .limit(10)
        .all()
    )

    recent_list = [
        {
            "id": t.id,
            "uid": t.uid,
            "amount": t.amount,
            "type": t.type,
            "performed_by": t.performed_by,
            "role": t.role,
            "timestamp": t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for t in recent
    ]

    return jsonify(
        {
            "summary": {
                "total_topups": int(total_topups or 0),
                "total_payments": int(total_payments or 0),
                "card_count": card_count,
                "total_balance": int(total_balance or 0),
            },
            "recent_transactions": recent_list,
        }
    )


@app.route('/pay', methods=['POST'])
@login_required
@role_required("sales", "agent")
def pay():
    data = request.json
    uid = str(data.get('uid')).upper().strip()
    amount = int(data.get('amount', 0))
    card = UserCard.query.filter_by(uid=uid).first()
    if not card:
        return jsonify({"error": "Card not registered"}), 404
    if card.balance >= amount:
        card.balance -= amount
        tx = Transaction(
            uid=uid,
            amount=amount,
            type="PAYMENT",
            performed_by=session.get("username"),
            role=session.get("role"),
        )
        db.session.add(tx)
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
        return jsonify(
            {
                "status": "success",
                "new_balance": card.balance,
                "transaction_id": tx.id,
                "receipt_url": url_for("receipt", tx_id=tx.id),
            }
        ), 200
    return jsonify({"error": "Insufficient Funds"}), 400


@app.route('/topup', methods=['POST'])
@login_required
@role_required("agent")
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
    tx = Transaction(
        uid=uid,
        amount=amount,
        type="TOP-UP",
        performed_by=session.get("username"),
        role=session.get("role"),
    )
    db.session.add(tx)
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
    return jsonify(
        {
            "status": "success",
            "new_balance": card.balance,
            "transaction_id": tx.id,
            "receipt_url": url_for("receipt", tx_id=tx.id),
        }
    ), 200


@app.route('/receipt/<int:tx_id>')
@login_required
def receipt(tx_id: int):
    tx = Transaction.query.get_or_404(tx_id)
    card = UserCard.query.filter_by(uid=tx.uid).first()
    return render_template('receipt.html', tx=tx, card=card)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=9254, debug=True, allow_unsafe_werkzeug=True)