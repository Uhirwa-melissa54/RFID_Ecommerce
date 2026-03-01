import network
import machine
from mfrc522 import MFRC522
from umqtt.simple import MQTTClient
import ujson
import time

# --- Configuration ---
WIFI_SSID = "EdNet"
WIFI_PASS = "Huawei@123"
TEAM_ID = "team_pixel" 
MQTT_BROKER = "broker.benax.rw"
CLIENT_ID = f"ESP8266_{TEAM_ID}"

# Topics
TOPIC_STATUS = f"rfid/{TEAM_ID}/card/status"
TOPIC_TOPUP = f"rfid/{TEAM_ID}/card/topup"

# --- Wi-Fi Connection ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f'Connecting to {WIFI_SSID}...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        timeout = 0
        while not wlan.isconnected() and timeout < 15:
            time.sleep(1)
            timeout += 1
    if wlan.isconnected():
        print('WiFi Connected! IP:', wlan.ifconfig()[0])
    else:
        print('WiFi Connection Failed.')

# --- Hardware Setup ---
# Pins for ESP8266: SCK=14, MOSI=13, MISO=12, RST=0, SDA=2
reader = MFRC522(sck=14, mosi=13, miso=12, rst=0, cs=2)

# --- MQTT Callback ---
def on_message(topic, msg):
    """Triggered when the backend acknowledges a top-up"""
    try:
        data = ujson.loads(msg)
        print("-" * 30)
        print(f"CONFIRMED TRANSACTION")
        print(f"UID: {data['uid']}")
        print(f"NEW BALANCE: {data['new_balance']} RWF")
        print("-" * 30)
    except Exception as e:
        print("Error processing message:", e)

# --- Initialize ---
connect_wifi()
client = MQTTClient(CLIENT_ID, MQTT_BROKER)
client.set_callback(on_message)
client.connect()
client.subscribe(TOPIC_TOPUP)

print("System Active. Waiting for RFID card...")

# --- Main Loop ---
while True:
    try:
        # Check for incoming MQTT messages
        client.check_msg()

        # Scan for card
        (stat, tag_type) = reader.request(reader.CARD_REQIDL)
        
        if stat == reader.OK:
            (stat, raw_uid) = reader.anticoll()
            if stat == reader.OK:
                uid = "0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
                print(f"Card detected: {uid}")
                
                # We only send the UID. The backend will look up the real balance.
                payload = ujson.dumps({"uid": uid})
                client.publish(TOPIC_STATUS, payload)
                
                time.sleep(2) # Cooldown to avoid double-reads
                
    except Exception as e:
        print("Loop Error:", e)
        time.sleep(1)a