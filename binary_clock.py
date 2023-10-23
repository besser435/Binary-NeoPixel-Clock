import time
import board
import neopixel

import adafruit_ntp
import socketpool
import time
import wifi
import os
#import adafruit_veml7700


DISPLAY_BRIGHTNESS = 0.1
SHUTOFF_LUX_THRESHOLD = 10

H_COLOR = (255, 0, 0)
M_COLOR = (0, 255, 0)
S_COLOR = (0, 0, 255)


# Hardware setup
#i2c = busio.I2C(board.SCL, board.SDA)
#veml7700 = adafruit_veml7700.VEML7700(i2c)
wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=-7)   # Set timezone here

led_neo = neopixel.NeoPixel(board.GP15, 18, brightness=DISPLAY_BRIGHTNESS, auto_write=False, bpp=4)




def binary_time():
    # Create an NTP client
    current_time = ntp.datetime
    hours = current_time.tm_hour
    mins = current_time.tm_min
    secs = current_time.tm_sec

    bin_hours = bin(hours)[2:]  # CircuitPython doesn't have zfill
    bin_hours = "0" * (6 - len(bin_hours)) + bin_hours

    bin_mins = bin(mins)[2:]
    bin_mins = "0" * (6 - len(bin_mins)) + bin_mins

    bin_secs = bin(secs)[2:]
    bin_secs = "0" * (6 - len(bin_secs)) + bin_secs

    print(f"{hours}:{mins}:{secs}")    
    print(f"{bin_hours}:{bin_mins}:{bin_secs}")

    return bin_hours, bin_mins, bin_secs


def light_shutoff():    # turns the display off if it's dark, like when you're sleeping
    lux = veml7700.lux
    light = veml7700.light
    print("Lux:", lux)
    print("Ambient Light:", light)


    if lux < SHUTOFF_LUX_THRESHOLD:
        led_neo.brightness = 0
    else:
        led_neo.brightness = DISPLAY_BRIGHTNESS
        

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
            target_color = H_COLOR if binary_values[i] == "1" else zero_color
        elif i < 12:
            target_color = M_COLOR if binary_values[i] == "1" else zero_color
        else:
            target_color = S_COLOR if binary_values[i] == "1" else zero_color
        led_neo[i] = target_color
        print(led_neo[i])
    


        """
        FADE_DURATION = 0.25  # Duration of the transition in seconds
        current_color = led_neo[i]
        step_count = int(FADE_DURATION * 10)  # Number of steps in the transition

        for step in range(step_count):
            # Calculate the color at the current step in the transition
            fraction = (step + 1) / step_count
            intermediate_color = tuple(
                int((1 - fraction) * current + fraction * target)
                for current, target in zip(current_color, target_color)
            )

            led_neo[i] = intermediate_color
            time.sleep(FADE_DURATION / step_count)

        led_neo[i] = target_color  # Set the final color"""

    led_neo.show()


while True:
    paint_display()
    #light_shutoff()

    time.sleep(1)
    print("\n" * 3)


