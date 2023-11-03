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

"""
https://github.com/besser435/Binary-NeoPixel-Clock
"""

DISPLAY_BRIGHTNESS = 0.4
SHUTOFF_LUX_THRESHOLD = 60

color_options = { #7, 141, 112 pretty blue color, orange could be cool too
                1:((96, 96, 96, 96), (255, 255, 0), (61, 26, 120)), # Enby
                2:((255, 0, 0), (0, 255, 0), (0, 0, 255)),          # RGB
                3:((214, 2, 112), (155, 79, 150), (0, 56, 168)),    # Bi
                4:((255, 0, 0), (96, 96, 96, 96), (10, 49, 97)),    # USA
                5:((255, 33, 140), (255, 216, 0), (33, 177, 255)),  # Pan
                6:((3, 252, 206), (165, 3, 252), (65, 252, 3))      # Cyan, Purple, Green
}


# Hardware, WiFi, NTP, Color setup
i2c = busio.I2C(board.SCL, board.SDA)
veml = adafruit_veml7700.VEML7700(i2c)
rtc = adafruit_ds3231.DS3231(i2c)
led_neo = neopixel.NeoPixel(board.D10, 18, brightness=DISPLAY_BRIGHTNESS, auto_write=False, bpp=4)

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to: {os.getenv('CIRCUITPY_WIFI_SSID')}")

pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=-7, server="pool.ntp.org")   # Set timezone and server here
print(f"NTP server: {ntp._server}")

h_color = None
m_color = None
s_color = None
last_sync = None


def get_time():
    global last_sync
    current_time = rtc.datetime

    # If the last NTP sync was more than 45 minutes ago, sync the time first
    if last_sync is None or (current_time.tm_min - last_sync.tm_min) > (45 + randint(0, 2)): # randint per pool.ntp.org TOS   
        print("Syncing time from NTP server")
        
        ntp_time = ntp.datetime
        rtc.datetime = ntp_time # Update RTC time with NTP time
        last_sync = ntp_time    # Update the last sync time

    return rtc.datetime


def binary_time():
    current_time = get_time()
    hours = current_time.tm_hour
    mins = current_time.tm_min
    secs = current_time.tm_sec

    bin_hours = bin(hours)[2:]  # CircuitPython doesn't have zfill
    bin_hours = "0" * (6 - len(bin_hours)) + bin_hours

    bin_mins = bin(mins)[2:]
    bin_mins = "0" * (6 - len(bin_mins)) + bin_mins

    bin_secs = bin(secs)[2:]
    bin_secs = "0" * (6 - len(bin_secs)) + bin_secs

    print(f"Dec Time: {hours}:{mins}:{secs}")    
    print(f"Bin Time: {bin_hours}:{bin_mins}:{bin_secs}")

    return bin_hours, bin_mins, bin_secs


def brightness_fade(pixel: object, target_brightness: float, duration: float) -> None:
    """
    Should be its own library at some point.

    Depending on the NeoPixels used, it might not be a linear fade.
    In some cases, it will fade faster at lower brightnesses.
    """

    original_brightness = pixel.brightness
    steps = int(duration * 300)

    # Determine if increasing or decreasing brightness
    if target_brightness > original_brightness:
        step_value = (target_brightness - original_brightness) / steps
    else:
        step_value = (original_brightness - target_brightness) / steps

    # Brightness fade
    for i in range(steps + 1):
        if target_brightness > original_brightness: 
            new_brightness = original_brightness + i * step_value   # Positive fade
        else:                                     
            new_brightness = original_brightness - i * step_value   # Negative fade

        pixel.brightness = new_brightness
        pixel.show()
        time.sleep(duration / steps)
    pixel.brightness = target_brightness  # Ensure we get there / avoid float rounding errors
    pixel.show()


def light_shutoff():    # Changes the display brightness based on ambient light
    light = veml.light

    brightness_lookup = OrderedDict([   # OrderedDict; more CircuitPython fuckery (WHY IS IT NOT ORDERED!?)
        (25, 0),
        (100, 0.15),
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


def paint_display():
    """
    Hour, minute, second each get 6 bits/pixels for the 
    binary display.
    """

    bin_hours, bin_mins, bin_secs = binary_time()
    binary_values = bin_hours + bin_mins + bin_secs
    zero_color = (0, 0, 0)

    for i in range(len(binary_values)):
        if i < 6:
            target_color = h_color if binary_values[i] == "1" else zero_color
        elif i < 12:
            target_color = m_color if binary_values[i] == "1" else zero_color
        else:
            target_color = s_color if binary_values[i] == "1" else zero_color
        led_neo[i] = target_color
    led_neo.show()


def pick_color():
    global h_color, m_color, s_color
    global color_choice
    current_colors = (h_color, m_color, s_color)

    while True: # Randomly pick an option from color_options and ensure it's not the current one
        color_choice = randint(1, len(color_options))  # Number of color options
        new_colors = color_options[color_choice]

        if new_colors != current_colors:
            h_color, m_color, s_color = new_colors
            break


try:
    led_neo.fill((0, 0, 255))
    led_neo.show()
    pick_color()
    while True:
        current_time = get_time()
        if (current_time.tm_min == 0 and current_time.tm_sec == 0):
            # Change color every hour (not a great implementation)
            # Instead it should change when the current hour != last hour, then update last hour to current hour
            pick_color()

        paint_display()

        light_shutoff()
        
        print(f"Last sync: {last_sync.tm_hour}:{last_sync.tm_min}:{last_sync.tm_sec}")
        print(f"Using color set {color_choice}, with colors {h_color}, {m_color}, {s_color}")
        print("\n" * 2)
        time.sleep(1)
        
except Exception as e:
    while True:
        print(e)

        led_neo.fill((255, 0, 0))
        led_neo.show()
        light_shutoff()

        time.sleep(1)
