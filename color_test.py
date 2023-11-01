import board
import os
import busio
import neopixel
from collections import OrderedDict
import time

led_neo = neopixel.NeoPixel(board.D10, 18, brightness=0, auto_write=False, bpp=4)

3, 252, 206
65, 252, 3
h_color = (3, 252, 206)
m_color = (165, 3, 252)
s_color = (65, 252, 3)


for i in range(10):
    for i in range(18):
        if i < 6:
            target_color = h_color 
        elif i < 12:
            target_color = m_color
        else:
            target_color = s_color
        led_neo[i] = target_color
    led_neo.show()





"""
brightness_lookup = OrderedDict([   # OrderedDict; more CircuitPython fuckery (WHY IS IT NOT ORDERED!?)
    (60, 0),
    (200, 0.15),
    (300, 0.25),
    (400, 0.4),
    (600, 0.55),
    (800, 0.75),
    (1500, 1)
])
print("starting")
led_neo.brightness = 0
for key, value in brightness_lookup.items():
    led_neo.brightness = value
    
    print(f"key: {key}, value: {value}")
    print(led_neo.brightness)
    led_neo.show()

    time.sleep(0.05)
print("done")
"""





"""led_neo.brightness = 0
led_neo.show()
time.sleep(0.5)

# Define the duration and the number of steps
duration = 1  # in seconds
steps = 300   # number of steps for the transition
desired_brightness = 0.5
for i in range(steps + 1):
    brightness = i / steps  # Calculate the current brightness level

    led_neo.brightness = brightness
    led_neo.show()

    if brightness >= desired_brightness: break

    print(led_neo.brightness)
    time.sleep(duration / steps)  # Wait for the calculated duration for each step
print("done", led_neo.brightness)
time.sleep(3)


for i in range(steps + 1):
    brightness = 1 - i / steps
    led_neo.brightness = brightness
    led_neo.show()
    print(f"Current Brightness: {led_neo.brightness}")
    time.sleep(duration / steps)



"""
import time


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


brightness_fade(led_neo, 1, 0.5)

brightness_fade(led_neo, 0, 0.5)