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

DISPLAY_BRIGHTNESS = 0.4
SHUTOFF_LUX_THRESHOLD = 60

h_color = (255, 0, 0)
m_color = (0, 255, 0)
s_color = (0, 0, 255)


# Hardware, WiFi, NTP setup
i2c = busio.I2C(board.SCL, board.SDA)
veml = adafruit_veml7700.VEML7700(i2c)
rtc = adafruit_ds3231.DS3231(i2c)
led_neo = neopixel.NeoPixel(board.D10, 18, brightness=DISPLAY_BRIGHTNESS, auto_write=False, bpp=4)

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to: '{os.getenv('CIRCUITPY_WIFI_SSID')}")

pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=-7, server="pool.ntp.org")   # Set timezone and server here
print(f"NTP server: {ntp._server}")



last_sync = None
def get_time():
    # If the last NTP sync was more than 45 minutes ago, sync the time first.
    global last_sync
    current_time = rtc.datetime
    
    if last_sync is None or (current_time.tm_min - last_sync.tm_min) > (45 + randint(0, 2)): # randint per pool.ntp.org TOS   
        print("Syncing time from NTP server")
        ntp_time = ntp.datetime
        rtc.datetime = ntp_time  # Update RTC time with NTP time
        last_sync = ntp_time  # Update the last sync time

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

    print(f"Time: {hours}:{mins}:{secs}")    
    print(f"Bin Time: {bin_hours}:{bin_mins}:{bin_secs}")

    return bin_hours, bin_mins, bin_secs


def light_shutoff():    # turns the display off if it's dark, like when you're sleeping
    light = veml.light
    print(f"Ambient Light: {light}")

    if light > SHUTOFF_LUX_THRESHOLD:
        led_neo.brightness = DISPLAY_BRIGHTNESS
    else:
        led_neo.brightness = 0
        

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
    #7, 141, 112 pretty blue color
    color_options = {
                    1:((96, 96, 96, 96), (255, 255, 0), (61, 26, 120)), # Enby
                    2:((255, 0, 0), (0, 255, 0), (0, 0, 255)),          # RGB
                    3:((214, 2, 112), (155, 79, 150), (0, 56, 168)),    # Bi
                    4:((255, 0, 0), (96, 96, 96, 96), (10, 49, 97)),    # USA
                    5:((255, 33, 140), (255, 216, 0), (33, 177, 255))   # Pan
                    
    }

    current_colors = (h_color, m_color, s_color)

    while True: # Randomly pick an option from color_options and ensure it's not the current one
        color_choice = randint(1, len(color_options))  # Number of color options
        new_colors = color_options[color_choice]

        if new_colors != current_colors:
            h_color, m_color, s_color = new_colors
            break
    print(f"Using color set {color_choice}, with colors ({h_color}, {m_color}, {s_color})")


try:  
    led_neo.fill((0, 0, 0, 255))
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
        print("\n" * 2)
        time.sleep(1)
        
except Exception as e:
    while True:
        print(e)

        led_neo.fill((100, 0, 0))
        led_neo.show()
        light_shutoff()

        time.sleep(1)    
