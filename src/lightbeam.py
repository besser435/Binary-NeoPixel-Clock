import time
import busio
import board
import os
import neopixel
import adafruit_ntp
import socketpool
import wifi
import adafruit_veml7700
import adafruit_ds3231
from random import randint
from collections import OrderedDict
import digitalio
import asyncio
import adafruit_gps
import adafruit_requests
from adafruit_datetime import datetime
import math
from microcontroller import watchdog as wdt



"""
Lightbeam S3

Use on CircuitPython 9.0.0 or later

https://github.com/besser435/Lightbeam-S3
Hardware and software by besser



TODO 
move stuff to settings.toml
Create proper CP build and update pins in this file

"""

TZ_OFFSET = -7
TZ_REGION = "America/Phoenix"
NTP_SERVER = "pool.ntp.org" #TODO maybe just use pool.ntp.org instead of worldtimeapi. more reliable probably
USE_GPS_OVER_NTP = False

MAX_BRIGHTNESS = 0.4    # TODO if USB is connected, set to 0.1 to avoid overcurrent
SHUTOFF_LUX_THRESHOLD = 13

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
ldo = digitalio.DigitalInOut(board.LDO2)
ldo.direction = digitalio.Direction.OUTPUT
ldo.value = True

i2c = busio.I2C(scl=board.IO14, sda=board.IO12, frequency=400_000)

neo_disp = neopixel.NeoPixel(board.IO3, 18, brightness=0.2, auto_write=False, bpp=4)

#neo_mcu = neopixel.NeoPixel(board.IO2, 1, brightness=1, auto_write=False, bpp=4)

gnss = adafruit_gps.GPS_GtopI2C(i2c, debug=False)
#gnss_pps = digitalio.DigitalInOut(board.)
#gnss_pps.direction = digitalio.Direction.INPUT

rtc = adafruit_ds3231.DS3231(i2c)

veml = adafruit_veml7700.VEML7700(i2c)
veml.ALS_800MS
veml.ALS_GAIN_2

wdt.mode = None # disable the watchdog. (was running into it too often)

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to: {os.getenv('CIRCUITPY_WIFI_SSID')}")
print(f"IP Address: {wifi.radio.ipv4_address}")

pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET, server=NTP_SERVER)

requests = adafruit_requests.Session(pool, pool)



last_sync = None
time_now = None
time_bin = None

h_color = (255, 0, 0, 0)
m_color = (0, 255, 0, 0)
s_color = (0, 0, 255, 0)


async def brightness_fade(pixel: object, target_brightness: float, duration: float) -> None:
    """
    Should be its own library at some point.

    Depending on the NeoPixels used, it might not be a linear fade.
    In some cases, it will fade faster at lower brightnesses.
    """


    print(f"Target_brightness: {target_brightness}, duration: {duration}")


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
        await asyncio.sleep(duration / steps)
    pixel.brightness = target_brightness  # Ensure we get there / avoid float rounding errors
    pixel.show()


async def set_brightness(): # TODO if 0, disable back pixel. else 100% brightness
    while True:
        light = veml.light

        brightness_lookup = OrderedDict([   # OrderedDict; more CircuitPython fuckery (WHY IS IT NOT ORDERED!?)
            (50, 0.07),
            (120, 0.15),
            (300, 0.25),
            (400, 0.4),
            (600, 0.55),
            (800, 0.75),
            (1500, 1)
        ])


        for key, value in brightness_lookup.items():
            if light < SHUTOFF_LUX_THRESHOLD: 
                await brightness_fade(neo_disp, 0, 0.3)
                break
            elif light < key:
                await brightness_fade(neo_disp, value, 0.3)
                break
            elif light > key:
                brightness_fade(neo_disp, 1, 0.3)


        print(f"Key: {key}, value: {value}, light: {light}, neo_disp.brightness: {neo_disp.brightness}")

        await asyncio.sleep(2)


async def ntp_sync_rtc():
    global last_sync
    global time_now

    while True:
        print("Syncing time from NTP server...")
        
        #ntp_time = ntp.datetime
        #rtc.datetime = ntp_time     # Update RTC datetime with NTP datetime
        #last_sync = ntp_time


        request = requests.get(f"http://worldtimeapi.org/api/timezone/{TZ_REGION}")

        time = request.json()["datetime"]
        dt_object = datetime.fromisoformat(time)
        time_struct = dt_object.timetuple()

        rtc.datetime = time_struct
        last_sync = time_struct

        await asyncio.sleep(3600 + randint(-5, 5))


async def gnss_sync_rtc():
    global last_sync
    global time_now

    while True:
        print("Syncing time from GNSS...")


        gnss.update()
        print(f"GNSS 3D Fix: {gnss.fix_quality_3d}")
        print(f"GNSS Sats: {gnss.satellites}")

        if gnss.has_fix:
            # rtc.datetime = (gnss.timestamp_utc.tm_year,
            #                 gnss.timestamp_utc.tm_mon,
            #                 gnss.timestamp_utc.tm_mday,
            #                 gnss.timestamp_utc.tm_hour,
            #                 gnss.timestamp_utc.tm_min,
            #                 gnss.timestamp_utc.tm_sec, 0, 0
            #                 )
            
            # last_sync = gnss.timestamp_utc
            print(f"GNSS Time: {gnss.timestamp_utc.tm_hour}:{gnss.timestamp_utc.tm_min}:{gnss.timestamp_utc.tm_sec}")
            pass

        await asyncio.sleep(1)


async def pick_color():
    global h_color, m_color, s_color
    global color_choice
    current_colors = (h_color, m_color, s_color)

    while True: # Randomly pick an option from color_options and ensure it's not the current one
        color_choice = randint(1, len(color_options))  # Number of color options
        new_colors = color_options[color_choice]

        if new_colors != current_colors:
            h_color, m_color, s_color = new_colors
            break


async def update_times():    # very funky, some stuff is done twice and is stupid
    global time_now
    global time_bin

    while True:
        # Update time
        time_now = rtc.datetime 

        # Update binary time
        hours = time_now.tm_hour
        mins = time_now.tm_min
        secs = time_now.tm_sec

        bin_hours = bin(hours)[2:]  # CircuitPython doesn't have zfill
        bin_hours = "0" * (6 - len(bin_hours)) + bin_hours

        bin_mins = bin(mins)[2:]
        bin_mins = "0" * (6 - len(bin_mins)) + bin_mins

        bin_secs = bin(secs)[2:]
        bin_secs = "0" * (6 - len(bin_secs)) + bin_secs

        
        time_bin = bin_hours, bin_mins, bin_secs

        await asyncio.sleep(0)


async def paint_display():
    hour_checked = None

    while True:
        if last_sync:
            bin_hours, bin_mins, bin_secs = time_bin
            binary_values = bin_hours + bin_mins + bin_secs
            zero_color = (0, 0, 0, 0)


        if time_now.tm_hour != hour_checked:    # Change color every hour
            hour_checked = time_now.tm_hour
            await pick_color()


        for i in range(len(binary_values)):
            if i < 6:
                target_color = h_color if binary_values[i] == "1" else zero_color
            elif i < 12:
                target_color = m_color if binary_values[i] == "1" else zero_color
            else:
                target_color = s_color if binary_values[i] == "1" else zero_color
            neo_disp[i] = target_color

        neo_disp.show()

        await asyncio.sleep(0)


async def info_print():
    while True:
        print(f"Dec Time: {time_now.tm_hour}:{time_now.tm_min}:{time_now.tm_sec}")    
        print(f"Bin Time: {time_bin[0]}:{time_bin[1]}:{time_bin[2]}")
        print(f"Last sync: {last_sync.tm_hour}:{last_sync.tm_min}:{last_sync.tm_sec}")

        print(f"Using color set {color_choice}, with colors {h_color}, {m_color}, {s_color}")

        print("\n\n")

        await asyncio.sleep(0.1)



async def main():
    print("Lightbeam S3")
    neo_disp.fill((0, 0, 64))
    neo_disp.show()

    await pick_color()


    set_brightness_task = asyncio.create_task(set_brightness())
    ntp_sync_rtc_task = asyncio.create_task(ntp_sync_rtc())
    #gnss_sync_rtc_task = asyncio.create_task(gnss_sync_rtc())
    update_times_task = asyncio.create_task(update_times())
    paint_display_task = asyncio.create_task(paint_display())
    info_print_task = asyncio.create_task(info_print())

    await asyncio.gather(set_brightness_task, 
                        ntp_sync_rtc_task,
                        #gnss_sync_rtc_task,
                        update_times_task,
                        paint_display_task,
                        info_print_task
                        )

asyncio.run(main())