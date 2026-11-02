import machine
import time
import os

# Настройка I2S
i2s = machine.I2S(0,
                  sck=machine.Pin(13),
                  ws=machine.Pin(12),
                  sd=machine.Pin(15),
                  mode=machine.I2S.RX,
                  bits=16,
                  format=machine.I2S.MONO,
                  rate= 44100, #16000,
                  ibuf=10000)

# Подготовка файла для записи
filename = 'record.raw'
samples = bytearray(1024) # Буфер для чтения данных

GAIN = 5.0

print("Запись начинается...")
with open(filename, 'wb') as f:
    for i in range(500): # Пример: запись 100 блоков
        num_read = i2s.readinto(samples)
        if num_read > 0:
            f.write(samples[:num_read])


print("Запись завершена.")

file_info = os.stat(filename)
file_size = file_info[6] # Элемент [6] - это размер в байтах
print(f"Размер файла {filename}: {file_size} байт")

# 1. Настройка пинов I2S
SCK_PIN = 26  # BCLK
WS_PIN = 25   # LRC
SD_PIN = 15   # DIN

# 2. Инициализация I2S
audio_out = machine.I2S(
    0,
    sck=machine.Pin(SCK_PIN),
    ws=machine.Pin(WS_PIN),
    sd=machine.Pin(SD_PIN),
    mode=machine.I2S.TX,
    bits=16,
    format=machine.I2S.MONO, # или STEREO
    rate=44100,
    ibuf=10000
)

# 3. Функция воспроизведения wav файла
def play_wav(filename):
    print(f"Воспроизведение {filename}...")
    try:
        with open(filename, "rb") as f:
            # Пропускаем заголовок WAV (44 байта)
            f.seek(44)

            # Буфер для чтения данных
            audio_samples = bytearray(5000)

            while True:
                # Читаем данные из файла
                n = f.readinto(audio_samples)

                if n == 0:
                    break

                # Записываем данные в I2S
                audio_out.write(audio_samples[:n])

        print("Воспроизведение завершено")
    except Exception as e:
        print(f"Ошибка: {e}")

time.sleep(1)
# Загрузите файл "test.wav" на ESP32 и вызовите функцию:
play_wav(filename)

