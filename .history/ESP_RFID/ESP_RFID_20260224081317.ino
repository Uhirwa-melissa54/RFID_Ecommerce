#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <SPI.h>

/* ================= WIFI CONFIG ================= */
const char* WIFI_SSID = "EdNet";
const char* WIFI_PASS = "Huawei@123";

/* ================= MQTT CONFIG ================= */
const char* MQTT_BROKER = "broker.benax.rw";
const int MQTT_PORT = 1883;
const char* TEAM_ID = "team_pixel";

String CLIENT_ID = "ESP8266_" + String(TEAM_ID);
String TOPIC_STATUS = "rfid/" + String(TEAM_ID) + "/card/status";
String TOPIC_TOPUP = "rfid/" + String(TEAM_ID) + "/card/topup";

/* ================= PIN SETUP ================= */
#define RST_PIN D3
#define SS_PIN  D4
#define SCK_PIN D5
#define MISO_PIN D6
#define MOSI_PIN D7


MFRC522 rfid(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
MFRC522::StatusCode card_status;

WiFiClient espClient;
PubSubClient client(espClient);

/* ================= WIFI CONNECTION ================= */
void connectWiFi() {
  Serial.print("Connecting WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  Serial.println(WiFi.localIP());
}

/* ================= RFID WRITE FUNCTION ================= */
void writeBytesToBlock(byte block, byte buff[]) {
  // Authenticate the block before writing
  card_status = rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(rfid.uid));

  if (card_status != MFRC522::STATUS_OK) {
    Serial.print("Auth failed: ");
    Serial.println(rfid.GetStatusCodeName(card_status));
    return;
  }

  card_status = rfid.MIFARE_Write(block, buff, 16);
  if (card_status != MFRC522::STATUS_OK) {
    Serial.print("Write failed: ");
    Serial.println(rfid.GetStatusCodeName(card_status));
  } else {
    Serial.println("Balance successfully written to card!");
  }
}

/* ================= MQTT CALLBACK ================= */
void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (int i = 0; i < length; i++) msg += (char)payload[i];

  Serial.println("\nMQTT Message Received from Backend:");
  
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, msg);

  if (error) {
    Serial.println("JSON parse error");
    return;
  }

  // Extract data sent from your Flask /topup route
  String uid_from_server = doc["uid"];
  int balance = doc["new_balance"];

  Serial.println("Processing Top-up for UID: " + uid_from_server);

  // We only write if the card is currently touching the reader
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    byte buffer[16];
    String dataToWrite = "BAL:" + String(balance);
    dataToWrite.toCharArray((char*)buffer, 16);

    // Pad remaining bytes with spaces
    for (int i = dataToWrite.length(); i < 16; i++) buffer[i] = ' ';

    writeBytesToBlock(4, buffer);
    
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  } else {
    Serial.println("Error: Card not detected. Hold card against reader during top-up.");
  }
}

/* ================= SETUP ================= */
void setup() {
  Serial.begin(115200);
  SPI.begin();
  rfid.PCD_Init();

  // Initialize default key
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  connectWiFi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(callback);

  // MQTT Connection Loop
  while (!client.connected()) {
    if (client.connect(CLIENT_ID.c_str())) {
      Serial.println("MQTT Connected!");
      client.subscribe(TOPIC_TOPUP.c_str()); // This listens to your Flask app
    } else {
      delay(2000);
    }
  }
}

/* ================= LOOP ================= */
void loop() {
  if (!client.connected()) {
    if (client.connect(CLIENT_ID.c_str())) client.subscribe(TOPIC_TOPUP.c_str());
  }
  client.loop();

  // Look for cards
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;

  String uidStr = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uidStr += String(rfid.uid.uidByte[i], HEX);
  }

  Serial.println("Card Scanned: " + uidStr);
    
  // Send UID to Flask Backend via MQTT
  StaticJsonDocument<200> doc;
  doc["uid"] = uidStr;
  char buffer[200];
  serializeJson(doc, buffer);
  client.publish(TOPIC_STATUS.c_str(), buffer);

  delay(2000); // Wait 2 seconds before next scan
}