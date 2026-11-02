import machine
import time

# Инициализация I2C (настройте пины под свою плату)
# Для ESP32: i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
# Для Raspberry Pi Pico: i2c = machine.I2C(0, scl=machine.Pin(17), sda=machine.Pin(16))
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))

# Адрес датчика TCS34725
SENSOR_ADDR = 0x29

def write_reg(addr, reg, data):
    i2c.writeto_mem(addr, 0x80 | reg, bytes([data]))

def read_reg(addr, reg, length=1):
    return i2c.readfrom_mem(addr, 0x80 | reg, length)

# Инициализация датчика
def init_sensor():
    # Проверка подключения (регистр ID)
    if read_reg(SENSOR_ADDR, 0x12)[0] != 0x44:
        print("TCS34725 не найден!")
        return False

    # Включение питания и АЦП
    write_reg(SENSOR_ADDR, 0x00, 0x03)
    # Настройка времени интеграции (например, 2.4мс)
    write_reg(SENSOR_ADDR, 0x01, 0xFF)
    print("TCS34725 инициализирован")
    return True

# Чтение данных
def get_raw_data():
    # Чтение данных по регистрам (Clear, Red, Green, Blue)
    data = read_reg(SENSOR_ADDR, 0x14, 8)
    # Формирование значений (младший байт + старший байт << 8)
    clear = data[1] << 8 | data[0]
    red = data[3] << 8 | data[2]
    green = data[5] << 8 | data[4]
    blue = data[7] << 8 | data[6]
    return clear, red, green, blue

if init_sensor():
    while True:
        c, r, g, b = get_raw_data()
        if c > 0:
            # Расчет относительных значений (без ИК-фильтра)
            print(f"Clear: {c}, Red: {r}, Green: {g}, Blue: {b}")
            # Пример простой калибровки/интенсивности
            r_ratio = r / c
            g_ratio = g / c
            b_ratio = b / c
            print(f"R:{r_ratio:.2f} G:{g_ratio:.2f} B:{b_ratio:.2f}")
        time.sleep(0.5)
