import machine
import time

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
    format=machine.I2S.STEREO #MONO, # или STEREO
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
            audio_samples = bytearray(10000)
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

# Загрузите файл "test.wav" на ESP32 и вызовите функцию:
play_wav("Piano.wav")

