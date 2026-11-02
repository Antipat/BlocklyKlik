import time
from machine import Pin

line1 = Pin(5, Pin.IN) #Pin.OPEN_DRAIN)
line2 = Pin(23, Pin.IN) # Pin.OPEN_DRAIN)


print("Sensor Line!")
while True:
    print("Line1 = ", line1.value())
    print("Line2 = ", line2.value())
    time.sleep(0.2)

