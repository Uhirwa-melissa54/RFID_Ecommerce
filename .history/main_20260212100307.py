import network
import machine
from mfrc522 import MFRC522
from umqtt.simple import MQTTClient
import ujson
import time

# --- Configuration ---
WIFI_SSID = "EdNet"
WIFI_PASS = "Your_WiFi_Password"
TEAM_ID = "team_pixel" 
MQTT_BROKER = "YOUR_BROKER_IP_OR_URL"
CLIENT_ID = f"ESP8266_{TEAM_ID}"

# Topics per assignment requirements
TOPIC_STATUS = f"rfid/{TEAM_ID}/card/status"
TOPIC_TOPUP = f"rfid/{TEAM_ID}/card/topup"
TOPIC_BALANCE = f"rfid/{TEAM_ID}/card/balance"

# --- Wi-Fi Connection Function ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f'Connecting to {WIFI_SSID}...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        # Wait for connection with a timeout
        timeout = 0
        while not wlan.isconnected() and timeout < 10:
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
    """Triggered when a top-up command is received from the Backend."""
    try:
        if topic.decode() == TOPIC_TOPUP:
            data = ujson.loads(msg)
            target_uid = data['uid']
            amount = data['amount']
            
            print(f"[*] Top-up request for {target_uid}: +{amount}")
            
            # Simulated logic: In a real app, you'd update the physical card memory
            new_balance = 3000 + amount 
            
            # Publish the new balance back to the broker
            update_payload = ujson.dumps({"uid": target_uid, "new_balance": new_balance})
            client.publish(TOPIC_BALANCE, update_payload)
            print(f"[*] Balance updated and published: {new_balance}")
    except Exception as e:
        print("Error processing message:", e)

# --- Initialize System ---
connect_wifi()

client = MQTTClient(CLIENT_ID, MQTT_BROKER)
client.set_callback(on_message)
client.connect()
client.subscribe(TOPIC_TOPUP)

print(f"MQTT Connected and Subscribed to {TOPIC_TOPUP}")
print("Waiting for RFID card...")

# --- Main Loop ---
while True:
    try:
        # Check for incoming MQTT messages (non-blocking)
        client.check_msg()

        # Scan for card
        (stat, tag_type) = reader.request(reader.CARD_REQIDL)
        
        if stat == reader.OK:
            (stat, raw_uid) = reader.anticoll()
            if stat == reader.OK:
                uid = "0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
                print(f"Card detected! UID: {uid}")
                
                # Publish card UID and current balance to status topic
                payload = ujson.dumps({"uid": uid, "balance": 3000})
                client.publish(TOPIC_STATUS, payload)
                
                time.sleep(2) # Prevent rapid re-reads
                
    except Exception as e:
        print("Error in loop:", e)
        time.sleep(1)