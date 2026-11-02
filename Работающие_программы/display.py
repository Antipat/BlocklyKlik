from machine import Pin, I2C
import ssd1306, time

# Настройка I2C (для ESP32, выводы могут отличаться)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))

# Инициализация дисплея (128x64)
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

# Вывод текста
oled.fill(0) # Очистить дисплей
oled.text('Hello, MicroPython!', 0, 0)
oled.text('SSD1306 OLED', 0, 20)
oled.show() # Обновить экран, чтобы увидеть изменения

time.sleep(3)

oled.fill(0)                         # fill entire screen with colour=0
oled.pixel(0, 10)                    # get pixel at x=0, y=10

time.sleep(3)
oled.fill(0)
oled.pixel(0, 10, 1)                 # set pixel at x=0, y=10 to colour=1
oled.show()
time.sleep(3)

oled.fill(0)
oled.hline(0, 8, 4, 1)               # draw horizontal line x=0, y=8, width=4, colour=1
oled.show()
time.sleep(3)

oled.fill(0)
oled.vline(0, 8, 4, 1)               # draw vertical line x=0, y=8, height=4, colour=1
oled.show()
time.sleep(3)

oled.fill(0)
oled.line(0, 0, 127, 63, 1)          # draw a line from 0,0 to 127,63
oled.show()
time.sleep(3)

oled.fill(0)
oled.rect(10, 10, 107, 43, 1)        # draw a rectangle outline 10,10 to 117,53, colour=1
oled.show()
time.sleep(3)

oled.fill(0)
oled.fill_rect(10, 10, 107, 43, 1)   # draw a solid rectangle 10,10 to 117,53, colour=1
oled.show()
time.sleep(3)

oled.fill(0)
oled.text('Hello World', 0, 0, 1)    # draw some text at x=0, y=0, colour=1
oled.show()
time.sleep(3)

oled.fill(0)
oled.scroll(20, 0)                   # scroll 20 pixels to the right



### draw another FrameBuffer on top of the current one at the given coordinates
##import framebuf
##fbuf = framebuf.FrameBuffer(bytearray(8 * 8 * 1), 8, 8, framebuf.MONO_VLSB)
##fbuf.line(0, 0, 7, 7, 1)
##oled.blit(fbuf, 10, 10, 0)           # draw on top at x=10, y=10, key=0
oled.show()