import time
import board
import os
import busio
import neopixel
import adafruit_ntp
import socketpool
import wifi
import adafruit_veml7700
import adafruit_ds3231
from random import randint
from collections import OrderedDict
import asyncio


"""
https://github.com/besser435/Binary-NeoPixel-Clock
"""

DISPLAY_BRIGHTNESS = 0.4
SHUTOFF_LUX_THRESHOLD = 60

color_options = { 
    1:((96, 96, 96, 96), (255, 255, 0), (61, 26, 120)),     # Enby
    2:((255, 0, 0), (0, 255, 0), (0, 0, 255)),              # RGB
    3:((214, 2, 112), (155, 79, 150), (0, 56, 168)),        # Bi
    4:((255, 5, 5), (110, 80, 80, 80), (5, 0, 255)),        # USA
    5:((255, 33, 140), (255, 216, 0), (33, 177, 255)),      # Pan
    6:((3, 252, 206), (165, 3, 252), (65, 252, 3)),         # Cyan, Purple, Green
    7:((96, 96, 96, 96), (255, 112, 193), (91, 206, 250)),  # Trans
    8:((255, 20, 0), (255, 154, 0), (15, 0, 215))           # Arizona
}


# Hardware, WiFi, NTP, Color setup
i2c = busio.I2C(board.SCL, board.SDA)
veml = adafruit_veml7700.VEML7700(i2c)
rtc = adafruit_ds3231.DS3231(i2c)
led_neo = neopixel.NeoPixel(board.D10, 18, brightness=DISPLAY_BRIGHTNESS, auto_write=False, bpp=4)

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to: {os.getenv('CIRCUITPY_WIFI_SSID')}")
print(f"IP Address: {wifi.radio.ipv4_address}")

pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=-7, server="pool.ntp.org")   # Set timezone and server here
print(f"NTP server: {ntp._server}")

h_color = None
m_color = None
s_color = None
last_sync = None





async def set_brightness():
    while True:
        light = veml.light

        # TODO set gain

        
        brightness_lookup = OrderedDict([   # OrderedDict; more CircuitPython fuckery (WHY IS IT NOT ORDERED!?)
            (55, 0),
            (120, 0.15),
            (300, 0.25),
            (400, 0.4),
            (600, 0.55),
            (800, 0.75),
            (1500, 1)
        ])

        for key, value in brightness_lookup.items():
            if light < 25: 
                brightness_fade(led_neo, 0, 0.8)
                break

            if light < key:
                led_neo.brightness = value
                break
            else:
                led_neo.brightness = 1
        print(f"key: {key}, value: {value}, light: {light}")

        await asyncio.sleep(2)