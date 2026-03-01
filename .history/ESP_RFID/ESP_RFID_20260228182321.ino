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
String TOPIC_PAY = "rfid/" + String(TEAM_ID) + "/card/pay";
String TOPIC_BALANCE = "rfid/" + String(TEAM_ID) + "/card/balance";

/* ================= PIN SETUP (KEPT AS IS) ================= */
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
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.println("JSON parse error");
    return;
  }

  String uid_from_server = doc["uid"];
  int balance = doc["new_balance"];

  Serial.printf("\n[TRANSACTION] UID: %s | New Bal: %d\n", uid_from_server.c_str(), balance);

  // Requirement: Physically sync balance to card if present
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    byte buffer[16];
    String dataToWrite = "BAL:" + String(balance);
    dataToWrite.toCharArray((char*)buffer, 16);
    for (int i = dataToWrite.length(); i < 16; i++) buffer[i] = ' ';

    writeBytesToBlock(4, buffer);
    
    // Notify the broker that the card physical write is complete
    StaticJsonDocument<200> res;
    res["uid"] = uid_from_server;
    res["new_balance"] = balance;
    char out[200];
    serializeJson(res, out);
    client.publish(TOPIC_BALANCE.c_str(), out);

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  } else {
    Serial.println("Alert: Card not present. Physical sync skipped.");
  }
}

/* ================= SETUP ================= */
void setup() {
  Serial.begin(115200);
  SPI.begin();
  rfid.PCD_Init();

  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  connectWiFi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(callback);
}

/* ================= RECONNECT LOGIC ================= */
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(CLIENT_ID.c_str())) {
      Serial.println("connected");
      // Subscribe to both TOPUP and PAY per assignment rules
      client.subscribe(TOPIC_TOPUP.c_str());
      client.subscribe(TOPIC_PAY.c_str());
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

/* ================= LOOP ================= */
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;

  // Standard UID Formatting (mandatory leading zeros)
  String uidStr = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uidStr += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uidStr += String(rfid.uid.uidByte[i], HEX);
  }
  uidStr.toUpperCase();

  Serial.println("Card Detected: " + uidStr);
    
  // Publish status per assignment rules
  StaticJsonDocument<200> doc;
  doc["uid"] = uidStr;
  char buffer[200];
  serializeJson(doc, buffer);
  client.publish(TOPIC_STATUS.c_str(), buffer);

  delay(2000); 
}