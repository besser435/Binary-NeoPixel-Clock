import neopixel
import board

led_neo = neopixel.NeoPixel(board.GP15, 18, brightness=1, auto_write=False, bpp=4)



def fade(new_color, pixel):
    old_color = led_neo[pixel]
    