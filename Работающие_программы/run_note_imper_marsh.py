import machine
import math
import struct
import time

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
oled.text('Imperial March', 0, 0)

oled.text('Star wars', 0, 30)
oled.show() # Обновить экран, чтобы увидеть изменения

# --- Configuration ---
SCK_PIN = 26
WS_PIN = 25
SD_PIN = 15
SAMPLE_RATE = 22050  # Hz
FREQUENCY = 440      # Hz (A4 Note)
VOLUME = 0.5         # 0.0 to 1.0

# --- I2S Initialization ---
audio_out = machine.I2S(
    0,
    sck=machine.Pin(SCK_PIN),
    ws=machine.Pin(WS_PIN),
    sd=machine.Pin(SD_PIN),
    mode=machine.I2S.TX,
    bits=16,
    format=machine.I2S.MONO,
    rate=SAMPLE_RATE,
    ibuf=10000,
)

# --- Generate Sine Wave Sample ---
def generate_tone(frequency, duration_s, sample_rate, volume):
    num_samples = int(sample_rate * duration_s)
    # Generate one period of sine wave
    period = sample_rate // frequency
    samples = bytearray(period * 2) # 2 bytes per 16-bit sample
    for i in range(period):
        value = int(math.sin(2 * math.pi * i / period) * 32767 * volume)
        struct.pack_into("<h", samples, i * 2, value)
    return samples

# --- Play Note Function ---
def play_note(frequency, duration_s):
    samples = generate_tone(frequency, 1, SAMPLE_RATE, VOLUME)
    # Loop the 1-second sample
    loops = int(duration_s)
    for _ in range(loops):
        audio_out.write(samples)

# --- Main ---
print(f"Playing {FREQUENCY}Hz...")

# частоты нот "Имперского марша"
frequency = (392, 100, 392, 100, 392, 100, 311, 466, 392, 311, 466, 392, 587,
             587, 587, 622, 466, 369, 311, 466, 392, 784, 392,
             392, 784, 740, 698, 659, 622, 659, 415, 554, 523,
             493, 466, 440, 466, 311, 369, 311, 466, 392)

# длительность звучания нот
interval = [500,  40, 500, 40, 500, 40, 500, 200, 700, 500, 200, 1400, 700,
            700, 700, 500, 200, 700, 500, 200, 1400, 700, 500,
            200, 700, 500, 200, 200, 200, 900, 300, 700, 500,
            200, 200, 200, 900, 300, 700, 500, 200, 1500]
interval = [int(v*0.5) for v in interval]

for f, i in zip(frequency, interval):
    play_note(f, i)  # Play 440Hz for 2 seconds
    print(i)
print("Done")
