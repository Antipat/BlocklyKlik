
import time

from machine import Pin, PWM

VCC = Pin(2, Pin.OUT)
VCC.on()
motor1 = Pin(17, Pin.OUT)
velocity1 = PWM(Pin(16), freq=1000, duty=512)

motor2 = Pin(0, Pin.OUT)
velocity2 = PWM(Pin(4), freq=1000, duty=512)

print("Mainn!")

velocity1.init()
velocity2.init()

def set_pwm_value(value):
    # Ограничиваем значение диапазоном 0-255
    value = max(0, min(value, 255))
    # duty_u16 принимает значения 0-65535,
    # поэтому преобразуем 0-255 -> 0-65535 (умножаем на 257)
    velocity1.duty_u16(value * 257)
    velocity2.duty_u16(value * 257)
    print(f"Set PWM: {value}")


motor1.value(1)
motor2.value(1)
# Плавное увеличение яркости
for i in range(0, 256, 5):
    set_pwm_value(i)
    time.sleep(0.1)
# Плавное уменьшение яркости
for i in range(255, -1, -5):
    set_pwm_value(i)
    time.sleep(0.1)

motor1.value(0)
motor2.value(0)

# Плавное увеличение яркости
for i in range(0, 256, 5):
    set_pwm_value(i)
    time.sleep(0.1)

# Плавное уменьшение яркости
for i in range(255, -1, -5):
    set_pwm_value(i)
    time.sleep(0.1)

# Стоп

velocity.deinit()
VCC.off()
