import time
import board
import os
import busio
import neopixel
import adafruit_ntp
import socketpool
import wifi
#import adafruit_veml7700
#import adafruit_ds3231

DISPLAY_BRIGHTNESS = 0.4
SHUTOFF_LUX_THRESHOLD = 10

H_COLOR = (7, 141, 112)
M_COLOR = (255, 255, 0)
S_COLOR = (61, 26, 120)


# Hardware setup
#i2c = busio.I2C(board.SCL, board.SDA)
#veml = adafruit_veml7700.VEML7700(i2c)
#rtc = adafruit_ds3231.DS3231(i2c)
led_neo = neopixel.NeoPixel(board.GP15, 18, brightness=DISPLAY_BRIGHTNESS, auto_write=False, bpp=4)

wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=-7, server="pool.ntp.org")   # Set timezone here
print("NTP server",ntp._server) # NOTE defaults to some adafruit pool, I want to use pool.ntp.org



last_sync = None

def get_time():
    # If the last NTP sync was more than 45 minutes ago, sync the time first.
    global last_sync
    current_time = rtc.datetime
    
    if last_sync is None or (current_time.tm_min - last_sync.tm_min) > 45:
        # Perform NTP time synchronization
        ntp_time = ntp.datetime
        rtc.datetime = ntp_time  # Update RTC time with NTP time
        last_sync = ntp_time  # Update the last sync time
        
    return rtc.datetime



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
    lux = veml.lux
    light = veml.light
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



try:
    while True:
        paint_display()
        #light_shutoff()

        time.sleep(1)
        print("\n" * 3)
except Exception as e:
    print(e)
    start = time.monotonic()
    for i in range(10):
        led_neo.fill((100, 0, 0))
        led_neo.show()
        print(i)
    end = time.monotonic()
    print(end - start)


