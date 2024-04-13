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


"""
https://github.com/besser435/Lightbeam-S3
"""


TZ_OFFSET = -7
MAX_BRIGHTNESS = 0.4
SHUTOFF_LUX_THRESHOLD = 50


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
neo_disp = neopixel.NeoPixel(board.IO3, 18, brightness=0.4, auto_write=False, bpp=4)

#neo_mcu = neopixel.NeoPixel(board.IO2, 1, brightness=1, auto_write=False, bpp=4)

i2c = busio.I2C(scl=board.IO13, sda=board.IO14, frequency=100_000)

rtc = adafruit_ds3231.DS3231(i2c)

veml = adafruit_veml7700.VEML7700(i2c)

gnss = adafruit_gps.GPS_GtopI2C(i2c, debug=False)
#gnss_pps = digitalio.DigitalInOut(board.)
#gnss_pps.direction = digitalio.Direction.INPUT

#ldo = digitalio.DigitalInOut(board.LDO2)
#ldo.direction = digitalio.Direction.OUTPUT
#ldo.value = True

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to: {os.getenv('CIRCUITPY_WIFI_SSID')}")
print(f"IP Address: {wifi.radio.ipv4_address}")

pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET, server="pool.ntp.org")   # Set timezone and server here
print(f"NTP server: {ntp._server}")

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


    print(f"target_brightness: {target_brightness}, duration: {duration}")


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


async def set_brightness(): # TODO if 0, disable back pixel. else 100% brightness
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
            #if light < SHUTOFF_LUX_THRESHOLD: 
            if light < 25: 
                brightness_fade(neo_disp, 0, 0.8)
                break

            elif light < key:
                #brightness_fade(neo_disp, value, 0.8)
                neo_disp.brightness = value
                break
            else:
                neo_disp.brightness = 1


        neo_disp.show()


        print(f"key: {key}, value: {value}, light: {light}, neo_disp.brightness: {neo_disp.brightness}")

        await asyncio.sleep(2)


async def sync_rtc():
    global last_sync
    global time_now

    while True:
        print("Syncing time from NTP server...")
        
        ntp_time = ntp.datetime
        rtc.datetime = ntp_time # Update RTC time with NTP time
        last_sync = ntp_time    # Update the last sync time

        await asyncio.sleep(3600 + randint(-5, 5))


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
    while True:
        if last_sync is not None:
            """
            Hour, minute, second each get 6 bits/pixels for the 
            binary display.
            """

            bin_hours, bin_mins, bin_secs = time_bin
            binary_values = bin_hours + bin_mins + bin_secs
            zero_color = (0, 0, 0)


            if time_now.tm_min == 0 and time_now.tm_sec == 0:
                pick_color()


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

        await asyncio.sleep(0.2)



async def main():
    print("Lightbeam S3")
    neo_disp.fill((0, 0, 64))
    neo_disp.show()

    pick_color()

    #set_brightness_task = asyncio.create_task(set_brightness())
    sync_rtc_task = asyncio.create_task(sync_rtc())
    update_times_task = asyncio.create_task(update_times())
    paint_display_task = asyncio.create_task(paint_display())
    info_print_task = asyncio.create_task(info_print())




    await asyncio.gather(#set_brightness_task, 
                        sync_rtc_task,
                        update_times_task,
                        paint_display_task,
                        info_print_task
                        )

asyncio.run(main())