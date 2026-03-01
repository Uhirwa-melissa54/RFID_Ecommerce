import network
import time

SSID = "EdNet"
PASSWORD = "Huawei@123"

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