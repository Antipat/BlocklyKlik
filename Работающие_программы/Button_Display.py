from machine import Pin, I2C
import time
import ssd1306

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
addr = 0x20

# Записать 0xFF, чтобы перевести пины в режим входа
i2c.writeto(addr, b'\xFF')

# Инициализация дисплея (128x64)
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# Вывод текста
oled.fill(0) # Очистить дисплей
oled.text('Hello, MicroPython!', 0, 0)
oled.text('SSD1306 OLED', 0, 20)
oled.show() # Обновить экран, чтобы увидеть изменения
text =''
while True:
    data = i2c.readfrom(addr, 1)
    print("All pins:", bin(data[0]))
    # Чтение 0-го пина
    #print("Pin 0:", (data[0] & 0x01))
    time.sleep(0.5)
    for i in data:
        print("Data:", i)
        if i == 251:
            text = "Left"
        elif i == 247:
            text = "Right"
        elif i == 254:
            text = "Up"
        elif i == 253:
            text = "Down"
        elif i == 223:
            text = "A"
        elif i == 191:
            text = "B"


    oled.fill(0) # Очистить дисплей
    oled.text(f'Button = {text}', 0, 0)
    oled.show() # Обновить экран, чтобы увидеть изменения



