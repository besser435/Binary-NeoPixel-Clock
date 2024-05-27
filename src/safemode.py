import microcontroller
microcontroller.reset()

# this is hacky, but it fixes the watchdog timeout issue for now.
# See: https://learn.adafruit.com/circuitpython-safe-mode/safemode-py