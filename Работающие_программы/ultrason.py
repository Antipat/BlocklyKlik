from machine import Pin
import time

trig = Pin(14, Pin.OUT);
echo = Pin(27, Pin.IN);

dur = 0
cm = 0

def pulseIn(pin, level, timeout=1000000):
    t0 = time.ticks_us()
    # Ждем изменения уровня, если он не совпадает с требуемым
    while pin.value() == level:
        if time.ticks_diff(time.ticks_us(), t0) > timeout:
            return 0
    # Ждем начала импульса
    while pin.value() != level:
        if time.ticks_diff(time.ticks_us(), t0) > timeout:
            return 0

    # Замеряем длительность
    start = time.ticks_us()
    while pin.value() == level:
        if time.ticks_diff(time.ticks_us(), start) > timeout:
            return 0
    end = time.ticks_us()

    return time.ticks_diff(end, start)

while True:
    trig.off()
    time.sleep(0.001)
    trig.on()
    time.sleep(0.001)
    trig.off()
    time.sleep(0.001)

    dur = pulseIn(echo, 1)
    cm = (dur/2) / 29.1;
    print("cm = ", cm)

    time.sleep(0.1)

