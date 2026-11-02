from machine import Pin, I2C
import time

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
addr = 0x20

# Записать 0xFF, чтобы перевести пины в режим входа
i2c.writeto(addr, b'\xFF')

while True:
    data = i2c.readfrom(addr, 1)
    print("All pins:", bin(data[0]))
    # Чтение 0-го пина
    print("Pin 0:", (data[0] & 0x01))
    time.sleep(0.5)
    for i in data:
        print("Data:", i)