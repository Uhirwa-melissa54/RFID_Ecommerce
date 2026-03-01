import network
import time

SSID = "Your_WiFi_Name"
PASSWORD = "Your_WiFi_Password"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            pass
    print('Connected! Network config:', wlan.ifconfig())

connect_wifi()