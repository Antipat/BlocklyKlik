import pygame
import sys
import os

import serial
import serial.tools.list_ports  # Для автоматического поиска доступных COM-портов
import threading
import queue  # Безопасная очередь для передачи данных между потоками

import subprocess
import os
import time
import json

# Инициализация Pygame-CE
pygame.init()

# Настройка окна приложения
#screen = pygame.display.set_mode((1024, 600))

# --- ИСПРАВЛЕННАЯ НАСТРОЙКА ОКНА НА ПОЛНЫЙ ЭКРАН ---
monitor_info = pygame.display.Info()

# Автоматически берем РЕАЛЬНЫЕ ширину и высоту вашего монитора
SCREEN_WIDTH = monitor_info.current_w
SCREEN_HEIGHT = monitor_info.current_h - 60  # Вычитаем 60 пикселей, чтобы снизу не залезать под панель задач Windows

# Создаем изменяемое окно, которое сразу открывается во весь экран
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("BLOCKLY/KLIK 2.0")
font = pygame.font.SysFont("Arial", 16)
clock = pygame.time.Clock()
# Включаем автоповтор клавиш для удобного стирания текста через Backspace
pygame.key.set_repeat(400, 50)

# Переменные для новой панели кода (справа)
# Изначально отдаем под код 300 пикселей от правого края экрана
code_panel_x = SCREEN_WIDTH - 300
is_resizing_code_panel = False      # Флаг: держим ли мы мышку на границе
is_dragging_new_block = False # Флаг: тащим ли мы абсолютно новый блок, только что взятый из меню

MIN_CODE_PANEL_WIDTH = 200          # Минимальная ширина панели кода
MAX_CODE_PANEL_WIDTH = 600          # Максимальная ширина панели кода

# Глобальная переменная, где будет храниться текст текущего скетча
current_arduino_code_text = "// Блоки еще не собраны.\n// Нажмите SPACE для сборки кода."

# --- НАСТРОЙКИ СКРОЛЛБАРА ЛЕВОЙ ПАНЕЛИ ---
SCROLLBAR_WIDTH = 12                # Ширина полосы бегунка
is_dragging_scrollbar = False       # Удерживает ли пользователь бегунок мышью
scrollbar_rect = pygame.Rect(0, 0, 0, 0) # Хитбокс бегунка (рассчитывается динамически)
# Добавьте к настройкам скроллбара:
scrollbar_drag_offset_y = 0
total_menu_height = 0 # Чтобы переменная была видна в коде мыши до первого рендера

code_panel_scroll_y = 0  # Инициализируем скролл панели кода нулевым значением

# Буфер обмена для хранения скопированной цепочки блоков
clipboard_blocks = []


# --- СПИСКИ ТИПОВ БЛОКОВ С ДВУМЯ ПОЛЯМИ ВВОДА ---
BLOCKS_WITH_TWO_INPUTS = [
    # Порты и пины
    "pin_digital", "pin_pwm", "pin_read_digital", "pin_read_analog",
    # Сервоприводы
    "init_servo", "write_servo",
    # Математика и Переменные
    "math_add", "math_sub", "math_div", "var_int", "var_float", "var_string", "var_array",
    # Циклы и датчики
    "logic_for", "logic_for_advanced", "ir_init", "ir_read_to_var", "ir_hex_val",  "serial_init", "serial_print_format", "type_cast",
    "sonar_init", "sonar_read", "tcs_init", "tcs_read", "klik_motor_obj", "klik_motor_start", "klik_motor_set_addr",
    "klik_motor_init_setup", "klik_motor_power_set", "klik_motor_speed_get", "klik_motor_stop_set", "bluetooth_read",
    "func_definition"
]


# Цвета для подсветки кода C++
COLOR_SYNTAX_KEYWORD = (234, 92, 120)   # Розовый (void, setup, loop, if, else, return)
COLOR_SYNTAX_TYPE = (78, 201, 176)      # Бирюзовый (int, float, char, String, Servo)
COLOR_SYNTAX_FUNCTION = (220, 220, 170)  # Светло-желтый (digitalWrite, delay, pin_mode)
COLOR_SYNTAX_NUMBER = (181, 206, 168)    # Светло-зеленый (цифры: 0-255, 9600)
COLOR_SYNTAX_COMMENT = (106, 153, 85)   # Зеленый (комментарии: // ...)
COLOR_SYNTAX_INCLUDE = (206, 145, 120)  # Оранжево-коричневый (#include, <Wire.h>)
COLOR_CODE_TEXT = (236, 240, 241)       # Обычный белый текст (скобки, переменные)

# Списки ключевых слов для парсера
CPP_KEYWORDS = {"void", "setup", "loop", "if", "else", "while", "for", "return"}
CPP_TYPES = {"int", "float", "char", "double", "long", "short", "bool", "String", "Servo", "KLIK_I2C_Motor", "IRrecv", "decode_results"}
CPP_FUNCTIONS = {"digitalWrite", "analogWrite", "pinMode", "delay", "delayMicroseconds", "pulseIn", "attach", "write", "begin", "print", "println"}

# Состояния интерфейса: "workspace" (обычный режим), "save_dialog", "open_dialog"
app_state = "workspace"

# Переменные для окна SAVE
save_filename_text = "my_robot_project" # Имя файла по умолчанию в поле ввода
save_input_active = True                 # Фокус на поле ввода имени файла

# Переменные для окна OPEN
project_files_list = [] # Список найденных файлов .json
selected_file_idx = -1  # Индекс выбранного файла в списке
open_menu_scroll_y = 0  # Скролл для списка файлов, если их много

# Константы стиля
COLOR_BG = (240, 242, 245)
COLOR_PANEL_BG = (220, 225, 230)
COLOR_PANEL_BORDER = (180, 185, 190)
COLOR_BLOCK = (52, 152, 219)
COLOR_BLOCK_TEXT = (255, 255, 100)
COLOR_INPUT_BG = (255, 255, 255)
COLOR_INPUT_TEXT = (55, 55, 255)
COLOR_INPUT_BORDER = (41, 128, 185)
COLOR_INPUT_ACTIVE = (230, 126, 34)

# Новые цвета для категорий блоков (в формате RGB)
COLOR_CAT_LOGIC = (128, 0, 128)      # Фиолетовый (Циклы, условия, задержка)
COLOR_CAT_PINS = (75, 0, 130)       # Индиго (HIGH/LOW, PWM)
COLOR_CAT_MATH = (0, 128, 0)       # Зеленый (Математика)
COLOR_CAT_VARS = (230, 126, 34)       # Оранжевый (Переменные и списки)
COLOR_CAT_SERVO = (52, 152, 219)      # Синий (Оставим для ваших серво-блоков)
COLOR_CAT_IR = (22, 160, 133)         # Бирюзовый / Темно-зеленый (Для ИК-пульта)

# Новые цвета для Монитора порта
COLOR_MON_BG = (20, 24, 30)       # Глубокий темный фон терминала
COLOR_MON_TEXT = (46, 204, 113)   # Зеленый «хакерский» текст (прием данных)
COLOR_MON_SEND = (52, 152, 219)   # Синий текст (отправленные пользователем данные)
COLOR_BTN_CONN = (39, 174, 96)    # Зеленая кнопка «Подключить»
COLOR_BTN_DISC = (192, 41, 43)    # Красная кнопка «Отключить»
# Объявляем цвет для новой категории "Функции" (Красивый фиолетовый/аметистовый)
COLOR_CAT_FUNC = (155, 89, 182)

PANEL_WIDTH = 320

# Инициализация звукового движка
if not pygame.mixer.get_init():
    pygame.mixer.init()

CLICK_SOUND_FILE = "Bat.wav"  # Файл лежит прямо в корне рядом со скриптом
click_sound = None

if os.path.exists(CLICK_SOUND_FILE):
    try:
        click_sound = pygame.mixer.Sound(CLICK_SOUND_FILE)
        click_sound.set_volume(0.3)  # Громкость 30%, чтобы звук не раздражал при частых кликах
    except Exception as e:
        print("Ошибка загрузки Bat.wav:", e)
else:
    print(f"Предупреждение: Файл {CLICK_SOUND_FILE} не найден рядом с проектом.")

Fon_FILE = "Fon.wav"  # Файл лежит прямо в корне рядом со скриптом
fon_sound_K = None

if os.path.exists(Fon_FILE):
    try:
        fon_sound_K = pygame.mixer.Sound(Fon_FILE)
        fon_sound_K.set_volume(0.3)  # Громкость 30%, чтобы звук не раздражал при частых кликах
    except Exception as e:
        print("Ошибка загрузки Bat.wav:", e)
else:
    print(f"Предупреждение: Файл {Fon_FILE} не найден рядом с проектом.")


# --- ИНИЦИАЛИЗАЦИЯ ИКОНКИ ПРОЕКТА ---
ICON_FILE = "NikiLogo.png"  # Имя файла вашей иконки (лучше всего PNG с прозрачностью, 32x32 или 64x64)

if os.path.exists(ICON_FILE):
    try:
        project_icon = pygame.image.load(ICON_FILE)
        pygame.display.set_icon(project_icon)
    except Exception as e:
        print("Не удалось загрузить иконку проекта:", e)
else:
    print(f"Предупреждение: Файл иконки {ICON_FILE} не найден рядом с проектом.")


def get_resource_path(relative_path):
    """ Возвращает абсолютный путь к ресурсу, учитывая сборку PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ПРИМЕР ИСПОЛЬЗОВАНИЯ В КОДЕ:
# Вместо: play_sound("Bat.wav")
# Используйте: play_sound(get_resource_path("Bat.wav"))

icon_path = get_resource_path("NikiLogo.png")
bat_sound = get_resource_path("Bat.wav")
fon_sound = get_resource_path("Fon.wav")

# Включаем жирный шрифт
font.set_bold(True)


# КЛАСС БЛОКА (WORKSPACE) ---
class Block:
    def __init__(self, name, x, y, block_type, default_val="90", color=(52, 152, 219)):
        self.name = name
        self.x = x
        self.y = y
        self.width = 400  # Ширина увеличена, чтобы помещались 2 инпута
        self.height = 50
        self.block_type = block_type
        self.color = color

        # Первый инпут (левый) оставляем аккуратным для имен переменных или пинов
        self.input_rect = pygame.Rect(170, 12, 60, 26)

        # Второй инпут (правый) сдвигаем чуть правее и расширяем до 110 пикселей!
        self.input_rect2 = pygame.Rect(245, 12, 110, 26)

        # ТЕПЕРЬ ПЕРВЫЙ ИНПУТ (Имя переменной / Номер пина / Объект) — слева
        if "var" in block_type or "logic_for" in block_type:
            self.input_value = str("x")  # Явное создание новой независимой строки
        elif "pin" in block_type:
            self.input_value = str("13")
        elif "ir_init" in block_type:
            self.input_value = str("11")  # По умолчанию ИК вешаем на 11 пин
        elif "ir_read_to_var" in block_type:
            self.input_value = str("cmd")     # Подсказка для имени переменной
        elif "ir_hex_val" in block_type:
            self.input_value = str("FF30CF")  # Пример HEX-кода кнопки

        elif "bluetooth_read" in block_type:
            self.input_value = str("A4")  # Пин EN / Enable по умолчанию
            # Значение второго инпута автоматически подставит "x" из default_val

        elif "pin_read_digital" in block_type:
            self.input_value = str("2")
        elif "pin_read_analog" in block_type:
            self.input_value = str("A0")
        # Найдите цепочку if/elif для block_type внутри __init__ и добавьте:
        elif "serial_init" in block_type:
            self.input_value = str("Serial")  # Название объекта порта
        elif "serial_print" in block_type:
            self.input_value = str("Hello")   # Текст или переменная по умолчанию
        # Найдите цепочку if/elif для block_type внутри __init__ и добавьте:
        elif "serial_print_format" in block_type or "type_cast" in block_type:
            self.input_value = str("x")  # По умолчанию предлагаем читать переменную x
        # Найдите цепочку if/elif для block_type внутри __init__ и добавьте:
        elif "sonar_init" in block_type:
            self.input_value = str("11")      # По умолчанию TRIG пин = 11
            # Поле default_val передаст значение "12" во второй инпут (ECHO)
        elif "sonar_read" in block_type:
            self.input_value = str("distance") # Имя переменной, куда сохраняем данные
            # Во втором инпуте по умолчанию будет "cm" (просто как визуальное обозначение)
        # Найдите цепочку if/elif для block_type внутри __init__ и добавьте:
        elif "tcs_init" in block_type:
            self.input_value = str("tcs")       # Имя объекта датчика по умолчанию
            self.input_value2 = str("4X")       # Уровень усиления GAIN (1X, 4X, 16X, 60X)
        elif "tcs_read" in block_type:
            self.input_value = str("R")         # Канал для чтения по умолчанию (R, G, B или C)

        # Найдите цепочку if/elif для block_type внутри __init__ и добавьте:
        elif "klik_motor_obj" in block_type:
            self.input_value = str("mot1")        # Имя объекта
            self.input_value2 = str("0x0A")       # Адрес I2C

        elif "klik_motor_start" in block_type:
            self.input_value = str("mot")         # Каким мотором управляем
            self.input_value2 = str("Serial")      # Куда выводить адрес (в Serial)
        elif "klik_motor_start" in block_type:
            self.input_value = str("mot")         # Каким мотором управляем
            self.input_value2 = str("&Wire")     # Передаем адрес шины I2C по умолчанию

        elif "klik_motor_init_setup" in block_type:
            self.input_value = str("mot")        # Первое поле: имя объекта мотора
            self.input_value2 = str("32")         # Второе поле: радиус колеса в мм по умолчанию
        elif "klik_motor_power_set" in block_type:
            self.input_value = str("mot")              # Имя объекта мотора
            self.input_value2 = str("100.0, MOT_PWM")   # Обязательные параметры по умолчанию
        elif "klik_motor_speed_get" in block_type:
            self.input_value = str("x")                 # Переменная для сохранения результата
            self.input_value2 = str("mot, MOT_RPM")    # Имя мотора и параметр через запятую
        elif "klik_motor_stop_set" in block_type:
            self.input_value = str("mot")          # Имя объекта мотора
            self.input_value2 = str("0.5, MOT_MET") # Параметры остановки по умолчанию

        elif "logic_for_advanced" in block_type:
            self.input_value = str("i")       # Имя переменной цикла по умолчанию
            # Значение второго инпута (default_val) автоматически подставит "0, 100, 1"

        elif "delay" in block_type:
            # Для задержки первое поле очищаем, а время ("500") передастся во второе поле из default_val
            self.input_value = str("500")
        elif "end_bracket" in block_type:
            # Для закрывающей скобки оба поля должны быть пустыми
            self.input_value = str("")
            default_val = "" # Сбрасываем дефолтное значение для второго поля

        # --- ТЕКСТОВАЯ КОНКАТЕНАЦИЯ ---
        elif "string_concat" in block_type:
            self.input_value = str("x")       # Левое поле (например, имя переменной)
            self.input_value2 = str("abc")    # Правое поле (текст по умолчанию вместо скрытого)

            # Принудительно проверяем, что блок находится в списке двух инпутов,
            # чтобы Pygame знал, что его нужно отрисовывать!
            if "string_concat" not in BLOCKS_WITH_TWO_INPUTS:
                BLOCKS_WITH_TWO_INPUTS.append("string_concat")


        else:
            self.input_value = str("myServo")

        self.is_input_active = False
        # ТЕПЕРЬ ВТОРОЙ ИНПУТ (Значение / Состояние) — справа
        #self.input_rect2 = pygame.Rect(245, 12, 60, 26)
        self.input_value2 = str(default_val) if default_val else str("0")
        self.is_input_active2 = False

        # Укажите это в самом конце метода __init__ вашего класса Block
        self.cursor_index = len(self.input_value)   # Позиция курсора в первом инпуте
        self.cursor_index2 = len(self.input_value2) # Позиция курсора во втором инпуте


        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.parent_block = None
        self.child_block = None
        ###
        # Ромбовидное поле нужно только для блоков ветвления (if, else if)
        self.is_diamond_input = "if_block" in self.block_type or "else_if" in self.block_type or "logic_if" in self.block_type

        # Если это блок IF, увеличиваем инпут, чтобы ромб выглядел крупным и пропорциональным
        if self.is_diamond_input:
            self.input_rect = pygame.Rect(150, 9, 110, 32)

        ###

    def get_global_input_rect(self, scroll_y=0):
        """Возвращает актуальный хитбокс первого инпута на экране"""
        return self.input_rect.move(self.x, self.y - scroll_y)

    def get_global_input_rect2(self, scroll_y=0):
        """Возвращает актуальный хитбокс второго инпута на экране"""
        return self.input_rect2.move(self.x, self.y - scroll_y)


    def draw(self, surface, is_selected=False, scroll_y=0):
        # 1. ЗАЩИТА: Автоматическое определение формы пазла на лету
        if not hasattr(self, "shape_type"):
            if "read" in self.block_type or "get" in self.block_type or "hex_val" in self.block_type or "sonar_read" in self.block_type:
                self.shape_type = "value"
            # Добавьте в цепочку условий для определения shape_type:
            elif "logic_compare" in self.block_type or "logic_operation" in self.block_type or "boolean" in self.block_type:
                self.shape_type = "boolean" # Форма ромба / шестиугольника

            elif "logic_for" in self.block_type:
                self.shape_type = "c_shape"
##            elif "end_bracket" in self.block_type:
##                self.shape_type = "bracket"
            elif "loop" in self.block_type or "core_" in self.block_type:
                self.shape_type = "hat"
            else:
                self.shape_type = "command"
            # "setup" in self.block_type or

        # Вычисляем визуальную координату Y с учетом прокрутки холста
        render_y = self.y - scroll_y

        # Базовый прямоугольник для расчетов (хитбокс остается прежним)
        block_rect = pygame.Rect(self.x, render_y, self.width, self.height)

        # --- НОВАЯ СИСТЕМА ОТРИСОВКИ ФИГУР ПАЗЛОВ ---
        # Выбираем цвет обводки: оранжевый, если выбран, иначе темная тень базового цвета
        if is_selected:
            border_color = (230, 126, 34)
            border_width = 3
        else:
            border_color = [max(0, c - 40) for c in self.color]
            border_width = 2

        # Генерируем точки контура в зависимости от shape_type
        points = []
        x, y, w, h = self.x, render_y, self.width, self.height

        if self.shape_type == "command":
            points = [
                (x, y), (x + 15, y), (x + 20, y + 6), (x + 32, y + 6), (x + 37, y), (x + w, y),
                (x + w, y + h),
                (x + 37, y + h), (x + 32, y + h + 6), (x + 20, y + h + 6), (x + 15, y + h),
                (x, y + h)
            ]

        elif self.shape_type == "hat":
            points = [
                (x, y + 10), (x + 15, y), (x + w - 15, y), (x + w, y + 10),
                (x + w, y + h),
                (x + 37, y + h), (x + 32, y + h + 6), (x + 20, y + h + 6), (x + 15, y + h),
                (x, y + h)
            ]


        elif self.shape_type == "bracket":
            points = [
                (x, y), (x + 15, y), (x + 20, y + 6), (x + 32, y + 6), (x + 37, y), (x + w, y),
                (x + w, y + h),
                (x, y + h)
            ]
        elif self.shape_type == "value":
##            points = [
##                (x, y), (x + w, y),
##                (x + w, y + 10), (x + w + 6, y + 15), (x + w + 6, y + h - 15), (x + w, y + h - 10), (x + w, y + h),
##                (x, y + h),
##                (x, y + h - 10), (x + 6, y + h - 15), (x + 6, y + 15), (x, y + 10)
##            ]
            points = [
                (x, y), (x + 15, y), (x + 20, y + 6), (x + 32, y + 6), (x + 37, y), (x + w, y),
                (x + w, y + h),
                (x + 37, y + h), (x + 32, y + h + 6), (x + 20, y + h + 6), (x + 15, y + h),
                (x, y + h)
            ]

        elif self.shape_type == "boolean":
            # Ромбовидный/шестиугольный блок для условий (True/False, >, <)
            # Срезает левые и правые углы, превращая торцы в треугольные стрелки
            points = [
                (x + 15, y),          # Верхняя левая точка
                (x + w - 15, y),      # Верхняя правая точка
                (x + w, y + h // 2),  # Самый правый острый угол (середина высоты)
                (x + w - 15, y + h),  # Ниже правая точка
                (x + 15, y + h),      # Нижняя левая точка
                (x, y + h // 2)       # Самый левый острый угол (середина высоты)
            ]


        elif self.shape_type == "c_shape":
            # Красивый, пропорциональный C-блок в стиле Blockly
            # Верхняя перекладина имеет стандартную высоту h
            points = [
                # 1. Верхняя грань с выемкой пазла
                (x, y), (x + 15, y), (x + 20, y + 6), (x + 32, y + 6), (x + 37, y), (x + w, y),
                # 2. Опускаемся по правому краю верхней перекладины
                (x + w, y + h),
                # 3. Идем налево под верхней перекладиной, формируя ВНУТРЕННИЙ ВЫСТУП наружу
                (x + 55, y + h),
                (x + 50, y + h + 6),
                (x + 38, y + h + 6),
                (x + 33, y + h),
                (x + 25, y + h),
                # 4. Опускаемся ниже по внутренней ножке (делаем выступ вниз на 12 пикселей для боковой стенки)
                (x + 25, y + h + 15),
                (x, y + h + 15) # Левый нижний угол блока
                # Возвращаемся вверх по левой стене к началу (x, y)
            ]


        # Отрисовка фигурной подложки пазла
        if points:
            pygame.draw.polygon(surface, self.color, points)
            pygame.draw.polygon(surface, border_color, points, width=border_width)
        else:
            # Откат к обычному прямоугольнику, если тип вдруг не распознан
            pygame.draw.rect(surface, self.color, block_rect, border_radius=8)
            pygame.draw.rect(surface, border_color, block_rect, width=border_width, border_radius=8)

        # --- ВАШ ОРИГИНАЛЬНЫЙ КОД ОТРИСОВКИ ТЕКСТА И ИНПУТОВ ---
        text_surf = font.render(self.name, True, COLOR_BLOCK_TEXT)
        surface.blit(text_surf, (self.x + 15, render_y + 15))

        if "core_" not in self.block_type and self.block_type not in ("end_bracket"):
            # --- ТАЙМЕР МИГАНИЯ КУРСОРA ---
            show_cursor = (pygame.time.get_ticks() // 500) % 2 == 0

            # --- ПЕРВЫЙ ИНПУТ (Есть всегда, кроме core_) ---
            global_input_rect = self.input_rect.move(self.x, render_y)
            inp_border_color = COLOR_INPUT_ACTIVE if self.is_input_active else COLOR_INPUT_BORDER

            val_surf = font.render(self.input_value, True, COLOR_INPUT_TEXT)

            # Используем флаг: ромб нарисуется только на блоках ветвления
                        # Используем флаг: ромб нарисуется только на блоках ветвления
            if getattr(self, "is_diamond_input", False):
                ix, iy, iw, ih = global_input_rect.x, global_input_rect.y, global_input_rect.width, global_input_rect.height
                diamond_points = [
                    (ix + iw // 2, iy),       # Верхняя точка
                    (ix + iw, iy + ih // 2),  # Правая точка
                    (ix + iw // 2, iy + ih),  # Нижняя точка
                    (ix, iy + ih // 2)        # Левая точка
                ]
                pygame.draw.polygon(surface, COLOR_INPUT_BG, diamond_points)
                pygame.draw.polygon(surface, inp_border_color, diamond_points, width=2)

                # 1. ВЫЧИСЛЯЕМ ТОЧНУЮ СТАРТОВУЮ ПОЗИЦИЮ НАЧАЛА ТЕКСТА (ЦЕНТРИРОВАНИЕ)
                text_x = ix + (iw - val_surf.get_width()) // 2
                text_y = iy + (ih - val_surf.get_height()) // 2
                surface.blit(val_surf, (text_x, text_y))

                # 2. ОТРИСОВКА КУРСОРA ДЛЯ РОМБА (СТРОГО ОТ СТАРТА ЦЕНТРИРОВАННОГО ТЕКСТА)
                if self.is_input_active and show_cursor:
                    text_before_cursor = self.input_value[:self.cursor_index]
                    surf_before = font.render(text_before_cursor, True, COLOR_INPUT_TEXT)

                    # Курсор сдвигается вправо ровно от динамического начала текста text_x
                    cursor_x = text_x + surf_before.get_width()

                    cursor_top = iy + 6
                    cursor_bottom = iy + ih - 6
                    pygame.draw.line(surface, COLOR_INPUT_TEXT, (cursor_x, cursor_top), (cursor_x, cursor_bottom), width=2)

            # ВАРИАНТ 2: Обычный прямоугольный инпут для всех остальных блоков
            else:
                pygame.draw.rect(surface, COLOR_INPUT_BG, global_input_rect, border_radius=4)
                pygame.draw.rect(surface, inp_border_color, global_input_rect, border_radius=4, width=2)

                text_x = global_input_rect.x + 6
                text_y = global_input_rect.y + (global_input_rect.height - val_surf.get_height()) // 2
                surface.blit(val_surf, (text_x, text_y))

                # КУРСОР ДЛЯ ПРЯМОУГОЛЬНИКА (Рисуется ТОЛЬКО тут и считает позицию от левого края)
                if self.is_input_active and show_cursor:
                    text_before_cursor = self.input_value[:self.cursor_index]
                    surf_before = font.render(text_before_cursor, True, COLOR_INPUT_TEXT)

                    cursor_x = text_x + surf_before.get_width()
                    cursor_top = global_input_rect.y + 4
                    cursor_bottom = global_input_rect.bottom - 4
                    pygame.draw.line(surface, COLOR_INPUT_TEXT, (cursor_x, cursor_top), (cursor_x, cursor_bottom), width=2)



            # --- ВТОРОЙ ИНПУТ (Только если блок в списке BLOCKS_WITH_TWO_INPUTS) ---
            if self.block_type in BLOCKS_WITH_TWO_INPUTS:
                global_input_rect2 = self.input_rect2.move(self.x, render_y)
                inp_border_color2 = COLOR_INPUT_ACTIVE if self.is_input_active2 else COLOR_INPUT_BORDER
                pygame.draw.rect(surface, COLOR_INPUT_BG, global_input_rect2, border_radius=4)
                pygame.draw.rect(surface, inp_border_color2, global_input_rect2, border_radius=4, width=2)

                val_surf2 = font.render(self.input_value2, True, COLOR_INPUT_TEXT)
                surface.blit(val_surf2, (global_input_rect2.x + 6, global_input_rect2.y + 4))

                # Отрисовка курсора для второго инпута (СТРОГО внутри условия второго инпута!)
                if self.is_input_active2 and show_cursor:
                    text_before_cursor2 = self.input_value2[:self.cursor_index2]
                    surf_before2 = font.render(text_before_cursor2, True, COLOR_INPUT_TEXT)
                    cursor_x2 = global_input_rect2.x + 6 + surf_before2.get_width() + 2
                    pygame.draw.line(surface, COLOR_INPUT_TEXT, (cursor_x2, global_input_rect2.y + 4), (cursor_x2, global_input_rect2.bottom - 4), width=2)



    def update_position(self, x, y):
        self.x = x
        self.y = y
        if self.child_block:
            self.child_block.update_position(x, y + self.height + 2)

    def is_descendant(self, block):
        current = self.child_block
        while current:
            if current == block:
                return True
            current = current.child_block
        return False

    def handle_event(self, event, all_blocks, scroll_y=0):
        # 1. Рассчитываем физическое положение блока и его инпутов НА ЭКРАНЕ
        # (Просто вычитаем скролл из мировых координат блока)
        render_y = self.y - scroll_y
        block_rect = pygame.Rect(self.x, render_y, self.width, self.height)
        global_input_rect = self.input_rect.move(self.x, render_y)
        global_input_rect2 = self.input_rect2.move(self.x, render_y)

        # Обработку событий ведем по ЧИСТЫМ физическим координатам мыши на экране
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Получаем точные экранные координаты мыши в момент клика
            mx, my = pygame.mouse.get_pos()

            # Клик по первому инпуту
            if "core_" not in self.block_type and global_input_rect.collidepoint((mx, my)):
                self.is_input_active = True
                self.is_input_active2 = False
                self.is_dragging = False
                self.cursor_index = len(self.input_value)
                return True
            # Клик по второму инпуту
            elif self.block_type in BLOCKS_WITH_TWO_INPUTS and global_input_rect2.collidepoint((mx, my)):
                self.is_input_active2 = True
                self.is_input_active = False
                self.is_dragging = False
                self.cursor_index2 = len(self.input_value2)
                return True
            else:
                self.is_input_active = False
                self.is_input_active2 = False

            # Клик по телу блока (Начало повторного перетаскивания)
            if block_rect.collidepoint((mx, my)):
                self.is_dragging = True

                # --- ЖЕСТКОЕ ИСПРАВЛЕНИЕ: Считаем оба смещения строго ЭКРАН МИНУС ЭКРАН ---
                # Экранный X блока (это просто self.x, так как по X скролла нет) минус экранная мышь
                self.drag_offset_x = self.x - mx
                # Экранный Y блока (render_y) минус экранная мышь
                self.drag_offset_y = render_y - my

                if self.parent_block:
                    self.parent_block.child_block = None
                    self.parent_block = None
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                self.check_snap(all_blocks)
                return True

        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            return True


        elif event.type == pygame.KEYDOWN:
            # --- ЛОГИКА ДЛЯ ПЕРВОГО ИНПУТА ---
            if self.is_input_active:
                if event.key == pygame.K_BACKSPACE:
                    if self.cursor_index > 0:
                        self.input_value = self.input_value[:self.cursor_index - 1] + self.input_value[self.cursor_index:]
                        self.cursor_index -= 1
                elif event.key == pygame.K_DELETE:
                    if self.cursor_index < len(self.input_value):
                        self.input_value = self.input_value[:self.cursor_index] + self.input_value[self.cursor_index + 1:]
                elif event.key == pygame.K_LEFT:
                    self.cursor_index = max(0, self.cursor_index - 1)
                elif event.key == pygame.K_RIGHT:
                    self.cursor_index = min(len(self.input_value), self.cursor_index + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.is_input_active = False
                elif len(self.input_value) < 30 and event.unicode and event.unicode.isprintable():
                    self.input_value = self.input_value[:self.cursor_index] + event.unicode + self.input_value[self.cursor_index:]
                    self.cursor_index += 1
                return True

            # --- ЛОГИКА ДЛЯ ВТОРОГО ИНПУТА ---
            elif self.is_input_active2:
                if event.key == pygame.K_BACKSPACE:
                    if self.cursor_index2 > 0:
                        self.input_value2 = self.input_value2[:self.cursor_index2 - 1] + self.input_value2[self.cursor_index2:]
                        self.cursor_index2 -= 1
                elif event.key == pygame.K_DELETE:
                    if self.cursor_index2 < len(self.input_value2):
                        self.input_value2 = self.input_value2[:self.cursor_index2] + self.input_value2[self.cursor_index2 + 1:]
                elif event.key == pygame.K_LEFT:
                    self.cursor_index2 = max(0, self.cursor_index2 - 1)
                elif event.key == pygame.K_RIGHT:
                    self.cursor_index2 = min(len(self.input_value2), self.cursor_index2 + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.is_input_active2 = False
                elif len(self.input_value2) < 20 and event.unicode and event.unicode.isprintable():
                    self.input_value2 = self.input_value2[:self.cursor_index2] + event.unicode + self.input_value2[self.cursor_index2:]
                    self.cursor_index2 += 1
                return True

        return False


    def check_snap(self, all_blocks):
        # --- НАЧАЛО ВСТАВКИ ДЛЯ ФУНКЦИЙ ---
        # Шапка функции — это самостоятельный корень, она не может прилипать к другим цепочкам
        if self.block_type == "func_definition":
            return

        SNAP_DISTANCE = 25
        for other in all_blocks:
            if other == self or other.parent_block == self or self.is_descendant(other):
                continue

            if other.child_block is None:
                target_x = other.x
                target_y = other.y + other.height + 2

                distance = pygame.math.Vector2(self.x - target_x, self.y - target_y).length()
                if distance < SNAP_DISTANCE:
                    other.child_block = self
                    self.parent_block = other

                    root = other
                    while root.parent_block:
                        root = root.parent_block
                    root.update_position(root.x, root.y)
                    break


    def get_structured_code(self, all_blocks=[]):
        # Переменные поменялись ролями!
        var_or_pin = self.input_value if self.input_value else "x"
        val = self.input_value2 if self.input_value2 else "0"

        if self.block_type in ("core_setup", "core_loop"):
            return {"global": "", "setup": "", "loop": ""}

        # --- НАЧАЛО ВСТАВКИ ДЛЯ ФУНКЦИЙ ---
        elif self.block_type == "func_definition":
            # Возвращаем имя функции в секцию "loop" для тела функции
            func_name = var_or_pin.strip() if var_or_pin.strip() else "myFunction"
            return {"global": f"void {func_name}();\n", "setup": "", "loop": f"void {func_name}() {{\n"}

        elif self.block_type == "func_call":
            # Блок вызова генерирует стандартную строку вызова C++
            func_name = var_or_pin.strip() if var_or_pin.strip() else "myFunction"
            return {"global": "", "setup": "", "loop": f"  {func_name}();\n"}
        # --- КОНЕЦ ВСТАВКИ ДЛЯ ФУНКЦИЙ ---

        # --- СЕРВОПРИВОДЫ ---
        elif self.block_type == "init_servo":
            # var_or_pin — имя серво (например, myServo), val — пин подключения
            return {"global": f"#include <Servo.h>\nServo {var_or_pin};\n", "setup": f"  {var_or_pin}.attach({val});\n", "loop": ""}
        elif self.block_type == "write_servo":
            # var_or_pin — имя серво, val — угол поворота
            return {"global": "", "setup": "", "loop": f"  {var_or_pin}.write({val});\n"}
                # --- УЛЬТРАЗВУКОВОЙ ДАТЧИК HC-SR04 ---
        elif self.block_type == "sonar_init":
            # var_or_pin — пин TRIG (например, 11), val — пин ECHO (например, 12)
            # В глобальную область мы ничего не пишем, настраиваем только pinMode в setup
            return {
                "global": "",
                "setup": f"  pinMode({var_or_pin}, OUTPUT); // Trig\n  pinMode({val}, INPUT);  // Echo\n",
                "loop": ""
            }


        # var_or_pin — имя вашей переменной (например, distance)
        # Так как нам физически нужно знать, к каким пинам подключен датчик,
        # но инпуты уже заняты именем переменной, мы заставим блок "sonar_read"
        # автоматически искать по всему холсту блок "sonar_init", чтобы узнать номера пинов!
        # Это сделает интерфейс невероятно удобным для пользователя.

        elif self.block_type == "sonar_read":
            trig_pin = "11"
            echo_pin = "12"

            # Ищем блок инициализации в переданном списке all_blocks
            init_block = next((b for b in all_blocks if b.block_type == "sonar_init"), None)
            if init_block:
                trig_pin = init_block.input_value
                echo_pin = init_block.input_value2

            sonar_code = (
                f"  digitalWrite({trig_pin}, LOW);\n"
                f"  delayMicroseconds(2);\n"
                f"  digitalWrite({trig_pin}, HIGH);\n"
                f"  delayMicroseconds(10);\n"
                f"  digitalWrite({trig_pin}, LOW);\n"
                f"  {var_or_pin} = pulseIn({echo_pin}, HIGH) / 58; // Расстояние в см\n"
            )
            return {"global": "", "setup": "", "loop": sonar_code}

        # --- УМНЫЕ I2C МОТОРЫ KLIK С ЭНКОДЕРОМ ---
        elif self.block_type == "klik_motor_obj":
            motor_name = var_or_pin.strip() if var_or_pin.strip() else "mot"
            motor_addr = val.strip() if val.strip() else "0x0A"

            # Собираем блок строк, разделенных \n
            global_code = (
                "#include <Wire.h>\n"
                "#include <KLIK_I2C_Motor.h>\n"
                f"KLIK_I2C_Motor {motor_name}({motor_addr});"
            )
            return {"global": global_code, "setup": "", "loop": ""}


        elif self.block_type == "klik_motor_start":
            # var_or_pin — имя объекта мотора (например, mot)
            # val — имя объекта Serial порта (например, Serial)
            motor_name = var_or_pin.strip() if var_or_pin.strip() else "mot"
            serial_name = val.strip() if val.strip() else "Serial"

            # ГЛОБАЛЬНАЯ ОБЛАСТЬ: Генерируем чистое объявление объекта без адреса!
            global_code = (
                "#include <Wire.h>\n"
                "#include <KLIK_I2C_Motor.h>\n"
                f"KLIK_I2C_Motor {motor_name};"
            )

            # ОБЛАСТЬ SETUP: Вся логика сканирования шины I2C и вывода адреса
            setup_code = (
                f"  delay(500);\n"
                f"  if ({motor_name}.begin()) {{\n"
                f"    {serial_name}.print(\"Найден мотор 0x\");\n"
                f"    {serial_name}.println({motor_name}.getAddress(), HEX);\n"
                f"  }} else {{\n"
                f"    {serial_name}.println(\"Мотор не найден!\");\n"
                f"  }}\n"
            )

            # Благодаря вашей системе фильтрации инклудов, `#include` не продублируются,
            # даже если на холсте будут другие блоки моторов!
            return {"global": global_code, "setup": setup_code, "loop": ""}


        elif self.block_type == "klik_motor_set_addr":
            # var_or_pin — имя объекта мотора (например, mot или motLeft)
            # val — новый адрес в HEX, который ввёл пользователь (например, 0x09 или 0x0A)
            new_addr = val.strip() if val.strip() else "0x09"
            motor_name = var_or_pin.strip() if var_or_pin.strip() else "mot"

            # Автоматически создаем УНИКАЛЬНОЕ имя переменной для этого конкретного мотора
            var_name = f"{motor_name}_newAddress"

            # Находим имя объекта Serial на холсте для вывода отчета
            serial_name = "Serial"
            serial_init_block = next((b for b in all_blocks if "serial_init" in b.block_type), None)
            if serial_init_block:
                serial_name = serial_init_block.input_value

            # 1. Генерируем уникальную глобальную переменную под этот блок
            global_code = f"uint8_t {var_name} = {new_addr};\n"

            # 2. Формируем точную структуру двойного if-условия с новой переменной
            setup_code = (
                f"  if ({motor_name}.begin(&Wire)) {{\n"
                f"    if ({motor_name}.changeAddress({var_name})) {{\n"
                f"        {serial_name}.println({motor_name}.getAddress(), HEX);\n"
                f"    }} else {{\n"
                f"        {serial_name}.println(\"Адрес не изменён!\");\n"
                f"    }}\n"
                f"  }} else {{\n"
                f"    {serial_name}.println(\"Мотор не найден!\");\n"
                f"  }}\n"
            )
            return {"global": global_code, "setup": setup_code, "loop": ""}

        # иницилизация мотора
        elif self.block_type == "klik_motor_init_setup":
            # var_or_pin — имя объекта мотора (например, mot1)
            # val — радиус колеса (например, 32)
            motor_name = var_or_pin.strip() if var_or_pin.strip() else "mot"
            radius_val = val.strip() if val.strip() else "32"

            setup_code = (
                f"  {motor_name}.begin(&Wire);\n"
                f"  {motor_name}.radius = {radius_val};\n"
            )
            return {"global": "", "setup": setup_code, "loop": ""}

        elif self.block_type == "klik_motor_power_set":
            # var_or_pin — имя объекта мотора (например, mot1)
            # val — строка с параметрами (например, "100.0, MOT_PWM" или "100.0, MOT_PWM, 0.35, MOT_MET")
            motor_name = var_or_pin.strip() if var_or_pin.strip() else "mot"
            params = val.strip() if val.strip() else "100.0, MOT_PWM"

            # Генерируем исполняемый код для секции loop
            loop_code = f"  {motor_name}.setSpeed({params});\n"
            return {"global": "", "setup": "", "loop": loop_code}

        elif self.block_type == "klik_motor_speed_get":
            # var_or_pin — имя переменной (например, x)
            # val — строка вида "имя_мотора, параметр" (например, "mot1, MOT_RPM")
            target_var = var_or_pin.strip() if var_or_pin.strip() else "x"

            # Разделяем второй инпут по запятой
            parts = [p.strip() for p in val.split(",")]
            motor_name = parts[0] if len(parts) > 0 and parts[0] else "mot1"
            param_mode = parts[1] if len(parts) > 1 and parts[1] else "MOT_RPM"

            # Формируем строку кода для секции loop
            loop_code = f"  {target_var} = {motor_name}.getSpeed({param_mode});\n"
            return {"global": "", "setup": "", "loop": loop_code}

        elif self.block_type == "klik_motor_stop_set":
            # var_or_pin — имя объекта мотора (например, mot1)
            motor_name = var_or_pin.strip() if var_or_pin.strip() else "mot"

            # ИСПРАВЛЕНИЕ: берем значение напрямую из оригинального инпута self.input_value2,
            # игнорируя глобальную переменную val, которая принудительно ставит "0"
            raw_stop_params = self.input_value2.strip()

            # Если в поле реально что-то написано, вставляем параметры.
            # Если пользователь стёр всё дочиста — оставляем пустые скобки!
            if raw_stop_params:
                loop_code = f"  {motor_name}.setStop({raw_stop_params});\n"
            else:
                loop_code = f"  {motor_name}.setStop();\n"

            return {"global": "", "setup": "", "loop": loop_code}


        # --- ЛОГИКА И ЗАДЕРЖКА ---
        elif self.block_type == "delay":
            # Для задержки нужно только первое поле, так как второго у неё нет
            return {"global": "", "setup": "", "loop": f"  delay({var_or_pin});\n"}
        elif self.block_type in ("logic_if", "logic_while"):
            return {"global": "", "setup": "", "loop": f"  {self.block_type.split('_')[1]}({var_or_pin}) {{\n"}
        elif self.block_type == "logic_else_if":
            return {"global": "", "setup": "", "loop": f"  }} else if ({var_or_pin}) {{\n"}
        elif self.block_type == "logic_else":
            return {"global": "", "setup": "", "loop": "  } else {\n"}
        elif self.block_type == "end_bracket":
            return {"global": "", "setup": "", "loop": "  }\n"}
        elif self.block_type == "logic_for":
            # var_or_pin — имя переменной (например, i)
            # val — до какого значения считать (например, 180)
            return {
                "global": "",
                "setup": "",
                "loop": f"  for (int {var_or_pin} = 0; {var_or_pin} <= {val}; {var_or_pin}++) {{\n"
            }

        elif self.block_type == "logic_for_advanced":
            # var_or_pin — имя переменной (например, i)
            # val — строка параметров (например, "180, 0, -5")
            var_name = var_or_pin.strip() if var_or_pin.strip() else "i"

            # Безопасно парсим параметры, разделенные запятой
            params = [p.strip() for p in val.split(",")]

            # Если пользователь ввел меньше 3 параметров, подставляем безопасные дефолты
            start_val = params[0] if len(params) > 0 and params[0] else "0"
            end_val = params[1] if len(params) > 1 and params[1] else "10"
            step_val = params[2] if len(params) > 2 and params[2] else "1"

            # Автоматически определяем знак шага для правильного условия (<= или >=, ++ или +=)
            try:
                # Проверяем, является ли шаг отрицательным числом
                is_negative_step = float(step_val) < 0
            except ValueError:
                # Если там написана переменная или формула, ищем знак минуса в начале строки
                is_negative_step = step_val.startswith("-")

            # Формируем условие и инкремент в зависимости от направления шага
            if is_negative_step:
                condition = f"{var_name} >= {end_val}"
                # Если шаг равен -1, пишем --, иначе += -5 (или -= 5, если убрать минус)
                if step_val == "-1":
                    increment = f"{var_name}--"
                else:
                    # Если пользователь уже написал минус (например -5), делаем += -5
                    increment = f"{var_name} += {step_val}" if "-" in step_val else f"{var_name} -= {step_val}"
            else:
                condition = f"{var_name} <= {end_val}"
                if step_val == "1":
                    increment = f"{var_name}++"
                else:
                    increment = f"{var_name} += {step_val}"

            # Собираем конструкцию цикла
            # Мы также объявляем переменную как int прямо внутри цикла для безопасности
            for_code = f"  for (int {var_name} = {start_val}; {condition}; {increment}) {{\n"

            return {"global": "", "setup": "", "loop": for_code}


        # --- УПРАВЛЕНИЕ ПИНАМИ ---
        elif self.block_type == "pin_digital":
            return {"global": "", "setup": "", "loop": f"  digitalWrite({var_or_pin}, {val});\n"}
        elif self.block_type == "pin_pwm":
            return {"global": "", "setup": "", "loop": f"  analogWrite({var_or_pin}, {val});\n"}
        elif self.block_type == "pin_mode_setup":
            return {"global": "", "setup": f"  pinMode({var_or_pin}, OUTPUT);\n", "loop": ""}
                # Инициализация пина на вход (с подтягивающим резистором INPUT_PULLUP для стабильности кнопок)
        elif self.block_type == "pin_mode_input":
            return {"global": "", "setup": f"  pinMode({var_or_pin}, INPUT);\n", "loop": ""}

        # Чтение цифрового пина: var_or_pin — это номер пина, val — имя переменной
        elif self.block_type == "pin_read_digital":
            return {"global": "", "setup": "", "loop": f"  {val} = digitalRead({var_or_pin});\n"}

        # Чтение аналогового пина: var_or_pin — это номер пина (например, A0), val — имя переменной
        elif self.block_type == "pin_read_analog":
            return {"global": "", "setup": "", "loop": f"  {val} = analogRead({var_or_pin});\n"}

        # --- МАТЕМАТИКА ---
        elif self.block_type == "math_add":
            return {"global": "", "setup": "", "loop": f"  {var_or_pin} = {var_or_pin} + {val};\n"}
        elif self.block_type == "math_sub":
            return {"global": "", "setup": "", "loop": f"  {var_or_pin} = {var_or_pin} - {val};\n"}
        elif self.block_type == "math_div":
            return {"global": "", "setup": "", "loop": f"  {var_or_pin} = {var_or_pin} / {val};\n"}

        # --- НОВЫЕ МАТЕМАТИЧЕСКИЕ И СТРОКОВЫЕ БЛОКИ ---

        elif self.block_type == "math_pow_func":
            # var_or_pin — основание (например, x), val — степень (например, 2)
            expr = f"pow({var_or_pin}, {val})"
            if getattr(self, "shape_type", "command") == "value":
                return {"global": "", "setup": "", "loop": "", "expression": expr}
            else:
                return {"global": "", "setup": "", "loop": f"  {var_or_pin} = pow({var_or_pin}, {val});\n", "expression": var_or_pin}

        elif self.block_type == "math_pi":
            target_var = var_or_pin.strip() if var_or_pin.strip() else "x"
            # Для PI пишем стандартное имя, оно всегда есть в Arduino.h
            if getattr(self, "shape_type", "command") == "value":
                return {"global": "", "setup": "", "loop": "", "expression": "PI"}
            else:
                return {"global": "", "setup": "", "loop": f"  {target_var} = PI;\n", "expression": target_var}

        elif self.block_type == "math_e":
            target_var = var_or_pin.strip() if var_or_pin.strip() else "x"

            # ЗАЩИТА: Насильно объявляем макрос Экспоненты в глобальной области,
            # если компилятор платы её вдруг не знает. Ваша система фильтрации
            # инклудов в главном цикле не даст этой строчке продублироваться!
            global_e = "#ifndef M_E\n#define M_E 2.7182818284590452354\n#endif\n"

            if getattr(self, "shape_type", "command") == "value":
                return {"global": global_e, "setup": "", "loop": "", "expression": "M_E"}
            else:
                return {"global": global_e, "setup": "", "loop": f"  {target_var} = M_E;\n", "expression": target_var}



        elif self.block_type == "math_log":
            # В Arduino функция log() считается натуральным логарифмом,
            # а десятичный логарифм — это log10(). Реализуем десятичный:
            expr = f"log10({var_or_pin})"
            if getattr(self, "shape_type", "command") == "value":
                return {"global": "", "setup": "", "loop": "", "expression": expr}
            else:
                return {"global": "", "setup": "", "loop": f"  {var_or_pin} = log10({var_or_pin});\n", "expression": var_or_pin}

        elif self.block_type == "math_ln":
            # Натуральный логарифм ln() в C++ пишется как log()
            expr = f"log({var_or_pin})"
            if getattr(self, "shape_type", "command") == "value":
                return {"global": "", "setup": "", "loop": "", "expression": expr}
            else:
                return {"global": "", "setup": "", "loop": f"  {var_or_pin} = log({var_or_pin});\n", "expression": var_or_pin}

        elif self.block_type == "string_concat":
            # Класс String в Arduino поддерживает конкатенацию через оператор '+'
            # Если первый инпут текстовый и не в кавычках (из-за ручного ввода),
            # система экранирования строк (которую мы делали в Serial) сработает,
            # но здесь мы собираем безопасное С++ выражение:
            str1 = var_or_pin
            str2 = val

            # Если это сырой текст из полей, а не блоки-выражения, принудительно экранируем:
            if not getattr(self, "input_block1", None) and not str1.isdigit() and not str1.isalnum():
                if not (str1.startswith('"') and str1.endswith('"')): str1 = f'"{str1}"'
            if not getattr(self, "input_block2", None) and not str2.isdigit() and not str2.isalnum():
                if not (str2.startswith('"') and str2.endswith('"')): str2 = f'"{str2}"'

            expr = f"({str1} + {str2})"
            if getattr(self, "shape_type", "command") == "value":
                return {"global": "", "setup": "", "loop": "", "expression": expr}
            else:
                return {"global": "", "setup": "", "loop": f"  {var_or_pin} = {str1} + {str2};\n", "expression": var_or_pin}


        # --- ПЕРЕМЕННЫЕ ---
        elif self.block_type == "var_int":
            return {"global": f"int {var_or_pin} = {val};\n", "setup": "", "loop": ""}
        elif self.block_type == "var_float":
            return {"global": f"float {var_or_pin} = {val};\n", "setup": "", "loop": ""}
        elif self.block_type == "var_string":
            return {"global": f'String {var_or_pin} = "{val}";\n', "setup": "", "loop": ""}
        elif self.block_type == "var_array":
            return {"global": f"int {var_or_pin}[{val}];\n", "setup": "", "loop": ""}

        # --- РАБОТА С ИК-ПУЛЬТОМ (IRremote) ---
        elif self.block_type == "ir_init":
            # var_or_pin — номер пина (например, 11)
            # В этой версии библиотеки также создаются глобальные объекты irrecv и results
            return {
                "global": "#include <IRremote.h>\nint RECV_PIN = " + var_or_pin + ";\nIRrecv irrecv(RECV_PIN);\ndecode_results results;\n",
                "setup": "  Serial.begin(9600);\n  irrecv.enableIRIn();\n  Serial.println(\"IR Initialized\");\n",
                "loop": ""
            }

        elif self.block_type == "ir_available":
            # Блок открывает условие "if", аналогично блоку logic_if
            # Любые блоки, прикрепленные ниже, будут выполняться только при получении сигнала
            return {"global": "", "setup": "", "loop": "  if (irrecv.decode(&results)) {\n"}

        elif self.block_type == "ir_resume":
            # Команда сброса приемника, чтобы он мог слушать пульт дальше
            return {"global": "", "setup": "", "loop": "    irrecv.resume();\n"}

        elif self.block_type == "ir_read_to_var":
            # var_or_pin — имя переменной (например, cmd)
            # В этой логике нам второе поле не нужно, переменная пишется в левое поле
            return {"global": "", "setup": "", "loop": "    " + var_or_pin + " = results.value;\n"}

        elif self.block_type == "ir_hex_val":
            # var_or_pin — сам HEX код, который ввёл пользователь (например, FF30CF)
            # Автоматически подставляем "0x" перед кодом для совместимости с C++
            clean_hex = var_or_pin.strip()
            if not clean_hex.startswith("0x") and not clean_hex.startswith("0X"):
                clean_hex = "0x" + clean_hex

            # Этот блок возвращает просто строку, которую можно использовать в условиях,
            # но так как наша архитектура требует структуру, мы возвращаем её в loop.
            # Если пользователь впишет этот HEX в обычный блок условий "logic_if",
            # он сможет написать в инпуте условия: cmd == 0xFF30CF
            return {"global": "", "setup": "", "loop": clean_hex}

        # --- РАБОТА С SERIAL ПОРТОМ ---
        elif self.block_type == "serial_init":
            # var_or_pin — имя объекта (Serial), val — скорость (9600)
            return {"global": "", "setup": f"  {var_or_pin}.begin({val});\n", "loop": ""}

        elif self.block_type in ("serial_print", "serial_println"):
            # Определяем, какую функцию C++ использовать
            func_name = "print" if self.block_type == "serial_print" else "println"

            # var_or_pin — это то, что ввёл пользователь в левое поле ввода
            content = var_or_pin

            # Умная проверка: если это не число и не похоже на имя переменной (например, содержит пробелы или спецсимволы),
            # то автоматически оборачиваем в кавычки как строку C++.
            # Если это просто имя переменной (например, x, cmd, my_var) или число, оставляем без кавычек.
            if not content.isdigit() and not content.replace('.','',1).isdigit():
                # Проверим, состоит ли строка только из букв и цифр без пробелов (как классическая переменная)
                if not content.isalnum():
                    content = f'"{content}"'

            # В вашей исправленной логике игрового цикла этот код успешно попадет
            # как в секцию setup, так и в секцию loop, в зависимости от того, куда его прикрепили!
            return {"global": "", "setup": "", "loop": f"  Serial.{func_name}({content});\n"}

                # --- СЛОЖНЫЙ ВЫВОД И КОНВЕРТАЦИЯ ДАННЫХ ---
        elif self.block_type == "serial_print_format":
            # var_or_pin — имя переменной с датчика (например, x или cmd)
            # val — формат вывода (например, HEX, BIN, DEC или BYTE)
            fmt = val.strip().upper()

            if fmt == "BYTE":
                # Для вывода сырых байт или ASCII-символов в поток напрямую используется Serial.write()
                return {"global": "", "setup": "", "loop": f"  Serial.write({var_or_pin});\n"}
            else:
                # Для остальных форматов (HEX, BIN, OCT, DEC) используем стандартный модификатор
                # Защита: если пользователь ввёл что-то странное, по умолчанию сработает DEC
                if fmt not in ("HEX", "BIN", "OCT", "DEC"):
                    fmt = "DEC"
                return {"global": "", "setup": "", "loop": f"  Serial.println({var_or_pin}, {fmt});\n"}

        elif self.block_type == "type_cast":
            # var_or_pin — имя исходной переменной (например, x)
            # val — в какой тип её превратить (например, char, String, int)
            target_type = val.strip()

            # Блок возвращает выражение перезаписи переменной в саму себя с приведением типа.
            # Пример: x = (char)x; или x = String(x);
            if target_type.lower() == "string":
                return {"global": "", "setup": "", "loop": f"  {var_or_pin} = String({var_or_pin});\n"}
            else:
                # Классическое приведение типов в C++: x = (char)x;
                return {"global": "", "setup": "", "loop": f"  {var_or_pin} = ({target_type}){var_or_pin};\n"}

        #BLUETOOTH
        elif self.block_type == "bluetooth_read":
            # var_or_pin — пин активации (например, A4)
            # val — имя переменной (например, x)
            en_pin = var_or_pin.strip() if var_or_pin.strip() else "A4"
            var_name = val.strip() if val.strip() else "x"

            # 1. ГЛОБАЛЬНАЯ ОБЛАСТЬ: Объявляем переменную пина
            global_code = f"int ser_enable = {en_pin};\n"

            # 2. ОБЛАСТЬ SETUP: Управляем питанием/сбросом модуля для его инициализации
            setup_code = (
                f"  pinMode(ser_enable, OUTPUT);\n"
                f"  digitalWrite(ser_enable, LOW);\n"
                f"  delay(1);\n"
                f"  digitalWrite(ser_enable, HIGH);\n"
            )

            # 3. ОБЛАСТЬ LOOP: Проверка буфера и чтение данных
            # Код пишется в секцию "loop" — ваша программа автоматически вставит её в void loop()
            loop_code = (
                f"  if (Serial.available())\n"
                f"  {{\n"
                f"     {var_name} = Serial.read();\n"
            )

            return {"global": global_code, "setup": setup_code, "loop": loop_code}

        # --- ДАТЧИК ЦВЕТА TCS34725 по I2C ---
        elif self.block_type == "tcs_init":
            # var_or_pin — имя объекта (tcs), val — уровень усиления (например, 4X)
            gain = val.strip().upper()
            if gain not in ("1X", "4X", "16X", "60X"):
                gain = "4X"

            global_code = (
                "#include <Wire.h>\n"
                "#include \"Adafruit_TCS34725.h\"\n"
                f"Adafruit_TCS34725 {var_or_pin} = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_50MS, TCS34725_GAIN_{gain});\n"
            )
            setup_code = f"  if (!{var_or_pin}.begin()) {{ Serial.println(\"TCS34725 Error!\"); }}\n"
            return {"global": global_code, "setup": setup_code, "loop": ""}

        elif self.block_type == "tcs_read":
            channel = var_or_pin.strip().upper()
            if channel not in ("R", "G", "B", "C"):
                channel = "R"

            channel_map = {"R": "tcs_r", "G": "tcs_g", "B": "tcs_b", "C": "tcs_c"}
            target_sub_var = channel_map[channel]

            # Ищем блок инициализации в переданном списке all_blocks
            tcs_obj_name = "tcs"
            init_block = next((b for b in all_blocks if b.block_type == "tcs_init"), None)
            if init_block:
                tcs_obj_name = init_block.input_value

            tcs_code = (
                "  {\n"
                "    uint16_t tcs_r, tcs_g, tcs_b, tcs_c;\n"
                f"    {tcs_obj_name}.getRawData(&tcs_r, &tcs_g, &tcs_b, &tcs_c);\n"
                f"    {val} = {target_sub_var};\n"
                "  }\n"
            )
            return {"global": "", "setup": "", "loop": tcs_code}

        # Заглушка для неизвестных блоков
        return {"global": "", "setup": "", "loop": ""}


# --- КЛАСС КНОПКИ В ТУЛБОКСЕ (Клонатор) ---
##class ToolboxButton:
##    def __init__(self, name, x, y, block_type, default_val, color):
##        self.name = name
##        self.block_type = block_type
##        self.default_val = default_val
##        self.color = color  # Цвет категории, который кнопка передаст созданному блоку
##        self.width = 280
##        self.height = 50
##        # Используем rect как единый источник правды для координат хитбокса и отрисовки
##        self.rect = pygame.Rect(x, y, self.width, self.height)
##
##    def draw(self, surface):
##        # Рисуем подложку кнопки её цветом категории
##        pygame.draw.rect(surface, self.color, self.rect, border_radius=8)
##
##        # Выравниваем текст названия строго по центру вертикали кнопки
##        text_surf = font.render(self.name, True, COLOR_BLOCK_TEXT)
##        text_y = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
##        surface.blit(text_surf, (self.rect.x + 15, text_y))
##
##        # Рисуем фейковый серый инпут внутри шаблона кнопки для красоты
##        fake_input = pygame.Rect(self.rect.x + 180, self.rect.y + 12, 60, 26)
##        pygame.draw.rect(surface, (200, 205, 210), fake_input, border_radius=4)
##
##    def handle_event(self, event, workspace_blocks, workspace_scroll_y=0):
##        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
##            if self.rect.collidepoint(event.pos):
##                # 1. Берем чистые экранные координаты мыши
##                real_mouse_x, real_mouse_y = pygame.mouse.get_pos()
##
##                # 2. Спавним блок в чистых координатах (скролл холста НЕ прибавляем сюда!)
##                # Пусть блок сначала создается в "экранной" системе координат, как и сама кнопка тулбокса
##                new_block = Block(
##                    name=self.name,
##                    x=int(real_mouse_x),
##                    y=int(real_mouse_y),
##                    block_type=self.block_type,
##                    default_val=self.default_val,
##                    color=self.color
##                )
##
##                # 3. Активируем режим перетаскивания
##                new_block.is_dragging = False
##                new_block.update_position(new_block.x, new_block.y)
##
##                workspace_blocks.append(new_block)
##                return True
##
##        return False

class ToolboxButton:
    def __init__(self, name, x, y, block_type, default_val, color):
        self.name = name
        self.block_type = block_type
        self.default_val = default_val
        self.color = color  # Цвет категории, который кнопка передаст созданному блоку
        self.width = 280
        self.height = 50
        # Используем rect как единый источник правды для координат хитбокса и отрисовки
        self.rect = pygame.Rect(x, y, self.width, self.height)

        # --- ОПРЕДЕЛЕНИЕ ФОРМЫ ДЛЯ ШАБЛОНА КНОПКИ ---
        if "read" in self.block_type or "get" in self.block_type or "hex_val" in self.block_type or "sonar_read" in self.block_type:
            self.shape_type = "value"
        elif "logic_for" in self.block_type:
            self.shape_type = "c_shape"
        elif "end_bracket" in self.block_type:
            self.shape_type = "bracket"
        elif "setup" in self.block_type or "loop" in self.block_type or "core_" in self.block_type:
            self.shape_type = "hat"
        else:
            self.shape_type = "command"

    def draw(self, surface):
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        points = []
        border_color = [max(0, c - 40) for c in self.color]

        # Строим контур пазла для кнопки тулбокса
        if self.shape_type == "command":
            points = [
                (x, y), (x + 15, y), (x + 20, y + 6), (x + 32, y + 6), (x + 37, y), (x + w, y),
                (x + w, y + h),
                (x + 37, y + h), (x + 32, y + h + 6), (x + 20, y + h + 6), (x + 15, y + h),
                (x, y + h)
            ]
        elif self.shape_type == "hat":
            points = [
                (x, y + 10), (x + 15, y), (x + w - 15, y), (x + w, y + 10),
                (x + w, y + h),
                (x + 37, y + h), (x + 32, y + h + 6), (x + 20, y + h + 6), (x + 15, y + h),
                (x, y + h)
            ]
        elif self.shape_type == "bracket":
            points = [
                (x, y), (x + 15, y), (x + 20, y + 6), (x + 32, y + 6), (x + 37, y), (x + w, y),
                (x + w, y + h),
                (x, y + h)
            ]
        elif self.shape_type == "value":
            points = [
                (x, y), (x + w, y),
                (x + w, y + 10), (x + w + 6, y + 15), (x + w + 6, y + h - 15), (x + w, y + h - 10), (x + w, y + h),
                (x, y + h),
                (x, y + h - 10), (x + 6, y + h - 15), (x + 6, y + 15), (x, y + 10)
            ]
        elif self.shape_type == "c_shape":
            top_bar_h, bottom_bar_h, left_wall_w = 30, 15, 20
            points = [
                (x, y), (x + 15, y), (x + 20, y + 6), (x + 32, y + 6), (x + 37, y), (x + w, y),
                (x + w, y + top_bar_h),
                (x + 37, y + top_bar_h), (x + 32, y + top_bar_h + 6), (x + 20, y + top_bar_h + 6), (x + 15, y + top_bar_h), (x + left_wall_w, y + top_bar_h),
                (x + left_wall_w, y + h - bottom_bar_h),
                (x + left_wall_w + 15, y + h - bottom_bar_h), (x + left_wall_w + 20, y + h - bottom_bar_h + 6), (x + left_wall_w + 32, y + h - bottom_bar_h + 6), (x + left_wall_w + 37, y + h - bottom_bar_h), (x + w, y + h - bottom_bar_h),
                (x + w, y + h),
                (x + 37, y + h), (x + 32, y + h + 6), (x + 20, y + h + 6), (x + 15, y + h), (x, y + h)
            ]

        # Отрисовка фигуры кнопки
        if points:
            pygame.draw.polygon(surface, self.color, points)
            pygame.draw.polygon(surface, border_color, points, width=2)
        else:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=8)

        # Выравниваем текст названия строго по центру вертикали кнопки
        text_surf = font.render(self.name, True, COLOR_BLOCK_TEXT)
        text_y = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (self.rect.x + 15, text_y))

        # Рисуем фейковый серый инпут внутри шаблона кнопки для красоты
        fake_input = pygame.Rect(self.rect.x + 180, self.rect.y + 12, 60, 26)
        pygame.draw.rect(surface, (200, 205, 210), fake_input, border_radius=4)

    def handle_event(self, event, workspace_blocks, workspace_scroll_y=0):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                real_mouse_x, real_mouse_y = pygame.mouse.get_pos()

                new_block = Block(
                    name=self.name,
                    x=int(real_mouse_x),
                    y=int(real_mouse_y),
                    block_type=self.block_type,
                    default_val=self.default_val,
                    color=self.color
                )

                new_block.is_dragging = False

                # Проверяем, есть ли у класса Block метод update_position
                if hasattr(new_block, 'update_position'):
                    new_block.update_position(new_block.x, new_block.y)

                workspace_blocks.append(new_block)
                return True

        return False


# --- ИНИЦИАЛИЗАЦИЯ ---
# Инициализируем холст сразу с двумя главными функциями Arduino
# Передаем им уникальный темно-серый цвет, чтобы они выделялись
COLOR_CORE = (44, 62, 80)

# --- 5. ИНИЦИАЛИЗАЦИЯ ОБЪЕКТОВ ПЕРЕД ЦИКЛОМ WHILE ---

# Создаем список блоков на холсте и сразу помещаем туда неудаляемые функции Arduino
blocks = [
    Block("НАСТРОЙКА setup()", x=400, y=50, block_type="core_setup", default_val="", color=COLOR_CORE),
    Block("ГЛАВНЫЙ ЦИКЛ loop()", x=400, y=320, block_type="core_loop", default_val="", color=COLOR_CORE)
]

# Глобальные переменные для управления интерфейсом палитры
toolbox_buttons = []
toolbox_scroll_y = 0
selected_block = None

# Стартовая координата Y для первой кнопки (ниже заголовка "Палитра блоков")
current_y = 60

def add_toolbox_item(name, block_type, default_val, color):
    """Вспомогательная функция для автоматического расчёта координат кнопок в тулбоксе"""
    global current_y
    toolbox_buttons.append(ToolboxButton(name, 20, current_y, block_type, default_val, color))
    current_y += 60  # Высота кнопки 50 пикселей + 10 пикселей отступ между ними

# --- НАПОЛНЕНИЕ ПАЛИТРЫ ИНСТРУМЕНТОВ БЛОКАМИ ---

# 1. Фиолетовая категория (Логика, циклы и задержка)
add_toolbox_item("Если / If", "logic_if", "1", COLOR_CAT_LOGIC)
add_toolbox_item("Иначе Если / Else If", "logic_else_if", "1", COLOR_CAT_LOGIC)
add_toolbox_item("Иначе / Else", "logic_else", "", COLOR_CAT_LOGIC)
add_toolbox_item("Цикл For (Перем | До)", "logic_for", "180", COLOR_CAT_LOGIC)
add_toolbox_item("Цикл For (Имя | От, До, Шаг)", "logic_for_advanced", "0, 100, 1", COLOR_CAT_LOGIC)
add_toolbox_item("Повторять / While", "logic_while", "1", COLOR_CAT_LOGIC)
add_toolbox_item("Конец блока / }", "end_bracket", " ", COLOR_CAT_LOGIC)
add_toolbox_item("Задержка (мс)", "delay", "500", COLOR_CAT_LOGIC)

# 2. Индиго категория (Управление портами и пинами микроконтроллера)
add_toolbox_item("Цифр. Пин (Сост|Пин)", "pin_digital", "HIGH", COLOR_CAT_PINS)
add_toolbox_item("ШИМ Пин (0-255|Пин)", "pin_pwm", "255", COLOR_CAT_PINS)
add_toolbox_item("Настроить Пин на Выход", "pin_mode_setup", "", COLOR_CAT_PINS)
# Добавьте это в фиолетовую категорию пинов
add_toolbox_item("Настроить Пин на ВХОД", "pin_mode_input", "", COLOR_CAT_PINS)
add_toolbox_item("Считать Цифр. (Пин|Var)", "pin_read_digital", "x", COLOR_CAT_PINS)
add_toolbox_item("Считать Аналог. (Пин|Var)", "pin_read_analog", "x", COLOR_CAT_PINS)

# --- БЛОКИ SERIAL-ПОРТА ---
add_toolbox_item("Serial: Инициализация", "serial_init", "9600", COLOR_CAT_PINS)
add_toolbox_item("Serial: Печать (print)", "serial_print", "Hello", COLOR_CAT_PINS)
add_toolbox_item("Serial: Печать ЛН (println)", "serial_println", "Hello", COLOR_CAT_PINS)
# --- РАСШИРЕННЫЙ ВЫВОД И ПРЕОБРАЗОВАНИЕ ТИПОВ ---
add_toolbox_item("Serial: Вывод формата (Var|Тип)", "serial_print_format", "HEX", COLOR_CAT_IR)
add_toolbox_item("Преобразовать (Var|в Тип)", "type_cast", "char", COLOR_CAT_IR)

# 3. Зеленая категория (Математические вычисления и обработка строк)
add_toolbox_item("Сложение (+)", "math_add", "0", COLOR_CAT_MATH)
add_toolbox_item("Вычитание (-)", "math_sub", "0", COLOR_CAT_MATH)
add_toolbox_item("Деление ( / )", "math_div", "1", COLOR_CAT_MATH)
add_toolbox_item("Функция pow()", "math_pow_func", "2", COLOR_CAT_MATH)
add_toolbox_item("Константа PI", "math_pi", "", COLOR_CAT_MATH)
add_toolbox_item("Константа E", "math_e", "", COLOR_CAT_MATH)
add_toolbox_item("Логарифм log()", "math_log", "10", COLOR_CAT_MATH)
add_toolbox_item("Натуральный ln()", "math_ln", "2", COLOR_CAT_MATH)
add_toolbox_item("Сцепить строки", "string_concat", "abc", COLOR_CAT_MATH)

# 4. Оранжевая категория (Инициализация глобальных переменных и массивов)
add_toolbox_item("Создать int (Целое)", "var_int", "0", COLOR_CAT_VARS)
add_toolbox_item("Создать float (Дробь)", "var_float", "0.0", COLOR_CAT_VARS)
add_toolbox_item("Создать String", "var_string", "abc", COLOR_CAT_VARS)
add_toolbox_item("Создать Массив", "var_array", "5", COLOR_CAT_VARS)

# 5. Синяя категория (Управление робототехникой и сервоприводами)
add_toolbox_item("Серво: Инициализация", "init_servo", "9", COLOR_CAT_SERVO)
add_toolbox_item("Серво: Поворот", "write_servo", "90", COLOR_CAT_SERVO)

# Добавьте в конец синей категории (Сервоприводы и Робототехника)
add_toolbox_item("Дальномер: Инициализация", "sonar_init", "12", COLOR_CAT_SERVO)
add_toolbox_item("Дальномер: Считать в Var", "sonar_read", "cm", COLOR_CAT_SERVO)

# Добавьте в конец синей категории палитры
add_toolbox_item("KLIKМотор: Создать Объект", "klik_motor_obj", "0x0A", COLOR_CAT_SERVO)
add_toolbox_item("KLIKМотор: Поиск M", "klik_motor_start", "Serial", COLOR_CAT_SERVO)
add_toolbox_item("KLIKМотор: Сменить Адрес", "klik_motor_set_addr", "0x09", COLOR_CAT_SERVO)
add_toolbox_item("KLIKМотор: Инит в Setup", "klik_motor_init_setup", "32", COLOR_CAT_SERVO)
add_toolbox_item("KLIKМотор: Установить Скорость", "klik_motor_power_set", "100.0, MOT_PWM", COLOR_CAT_SERVO)
add_toolbox_item("KLIKМотор: Считать данные", "klik_motor_speed_get", "mot1, MOT_RPM", COLOR_CAT_SERVO)
add_toolbox_item("I2C Мотор: Торможение/Стоп", "klik_motor_stop_set", "0.5, MOT_MET", COLOR_CAT_SERVO)

# 6. Бирюзовая категория (Дистанционное ИК-управление)
add_toolbox_item("ИК: Инициализация", "ir_init", "", COLOR_CAT_IR)      # Левое поле станет пином (по умолчанию "11")
add_toolbox_item("ИК: Если пойман сигнал", "ir_available", "", COLOR_CAT_IR)
add_toolbox_item("ИК: Продолжить прием", "ir_resume", "", COLOR_CAT_IR)

add_toolbox_item("ИК: Прочитать в Var", "ir_read_to_var", "", COLOR_CAT_IR)
add_toolbox_item("ИК: Код кнопки (HEX)", "ir_hex_val", "", COLOR_CAT_IR)

# Добавьте в конец бирюзовой категории палитры
add_toolbox_item("Датчик цвета: Старт", "tcs_init", "tcs", COLOR_CAT_IR)
add_toolbox_item("Датчик цвета: Считать (Цвет|Var)", "tcs_read", "myVar", COLOR_CAT_IR)

# Добавляем в бирюзовую категорию палитры
add_toolbox_item("Bluetooth: Считать в Var", "bluetooth_read", "x", COLOR_CAT_IR)

# --- ДОБАВЛЕНИЕ КАТЕГОРИИ ФУНКЦИЙ В КОНЕЦ ПАЛИТРЫ ---
add_toolbox_item("Создать функцию:", "func_definition", "", COLOR_CAT_FUNC)
add_toolbox_item("Вызвать функцию:", "func_call", "", COLOR_CAT_FUNC)


# --- ПЕРЕМЕННЫЕ МОНИТОРА ПОРТА ---
serial_obj = None                 # Объект порта PySerial
serial_is_connected = False       # Флаг статуса подключения
serial_queue = queue.Queue()      # Очередь для безопасного приема данных из потока
serial_logs = []                  # Список строк, отображаемых в терминале (макс. 10-15 строк)

# Настройки подключения
current_com_port = "COM3"         # Порт по умолчанию (можно менять кликом или автопоиском)
current_baudrate = 9600           # Скорость по умолчанию (9600, 115200 и т.д.)

# Хитбоксы для элементов управления (размещаем внизу экрана)
# Кнопка подключения: X=PANEL_WIDTH+20, Y=SCREEN_HEIGHT-38, ширина 120, высота 28
btn_connect_rect = pygame.Rect(PANEL_WIDTH + 20, SCREEN_HEIGHT - 38, 120, 28)
# Текстовое поле ввода для отправки команд в робота
input_send_rect = pygame.Rect(PANEL_WIDTH + 160, SCREEN_HEIGHT - 38, 250, 28)
input_send_text = ""              # Текущий вводимый текст для отправки
input_send_active = False         # Фокус на поле ввода отправки

# Потоковая функция чтения (работает в фоне)
def serial_read_thread(ser, q, stop_flag):
    while not stop_flag.is_set():
        if ser and ser.is_open:
            try:
                if ser.in_waiting > 0:
                    # Читаем строку, декодируем из байт (с игнорированием ошибок кодировки)
                    data = ser.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        q.put(("rx", data)) # Кладем в очередь с меткой "RX" (принято)
            except Exception as e:
                q.put(("err", f"Ошибка связи: {str(e)}"))
                break
        pygame.time.wait(10) # Небольшая пауза, чтобы не перегружать процессор

serial_stop_flag = threading.Event()

# --- СПИСКИ ДЛЯ ВЫБОРА НАСТРОЕК ПОРТА ---
# Автоматически сканируем систему на наличие реальных COM-портов
available_ports = [p.device for p in serial.tools.list_ports.comports()]
if not available_ports:
    available_ports = ["COM1", "COM2", "COM3", "COM4", "COM5"] # Заглушка, если ничего не подключено

# Если текущего порта нет в списке, берем первый доступный
if current_com_port not in available_ports:
    current_com_port = available_ports[0]

# Список стандартных скоростей Arduino
available_baudrates = [300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]

# Хитбоксы для кликов выбора (будут расположены на нижней панели вместо текстовой строки)
btn_port_rect = pygame.Rect(0, 0, 0, 0)  # Рассчитаем динамически при отрисовке
btn_baud_rect = pygame.Rect(0, 0, 0, 0)  # Рассчитаем динамически при отрисовке

# --- НАСТРОЙКИ СКРОЛЛИНГА И СБРОСА МОНИТОРА ПОРТА ---
serial_logs = []                  # Ваша существующая переменная (хранит ВСЕ принятые строки)
scroll_offset = 0                 # Текущее смещение прокрутки (0 - самый низ/свежие данные)
max_visible_lines = 5             # Сколько строчек физически помещается в ваше окно
line_height = 20                  # Высота одной строки текста в пикселях

# Область (хитбокс) самого текстового монитора, куда выводятся эти 5 строк.
# Настройте координаты X, Y, Width, Height под вашу верстку нижней панели!
monitor_display_rect = pygame.Rect(PANEL_WIDTH + 20, SCREEN_HEIGHT - 150, 600, 100)

# Кнопка очистки (Сброс / Clear) монитора порта
# Разместим её, например, правее поля ввода команды (input_send_rect.right + 20)
btn_clear_rect = pygame.Rect(input_send_rect.right + 20, SCREEN_HEIGHT - 38, 90, 28)

# --- НАСТРОЙКИ СКРОЛЛИНГА И ОЧИСТКИ ---
scroll_offset = 0          # 0 - показывает самые свежие логи (автоскролл). Чем выше число, тем выше мы прокрутили историю.
max_visible_lines = 7      # Сколько строк физически помещается в окно высотой 130 пикселей (130 // 16)

# Кнопка очистки логов (разместим её правее выбора Baud)
btn_clear_rect = pygame.Rect(0, 0, 0, 0) # Рассчитаем динамически в цикле отрисовки


def flash_via_portable_ide(com_port, sketch_path, result_queue):
    """
    Прошивка платы через встроенную портативную Arduino IDE.
    Вызывается в фоновом потоке, чтобы Pygame не зависал.
    """
    try:
        result_queue.put(("sys", "Освобождение порта для CH340..."))
        # Обязательно даем Windows паузу закрыть порт, открытый в Pygame
        time.sleep(1.0)

        # Вычисляем абсолютный путь к вашему портативному arduino.exe
        # Предполагаем, что папка 'arduino_ide' лежит в корне вашего проекта
        # Замените расчет base_dir на этот умный переключатель:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Если программа запущена как скомпилированный .exe (PyInstaller)
            # Мы берем путь к папке, ГДЕ ЛЕЖИТ сам ваш запущенный .exe файл
            base_dir = os.path.dirname(sys.executable)
        else:
            # Если запускаем обычный .py файл в редакторе (разработка)
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # Теперь путь соберется правильно относительно готового приложения
        arduino_exe_path = os.path.join(base_dir, "arduino_ide", "arduino_debug.exe")

        #arduino_exe_path = os.path.join(base_dir, "arduino_ide", "arduino.exe")

        if not os.path.exists(arduino_exe_path):
            result_queue.put(("err", "Критическая ошибка: Встроенная папка arduino_ide не найдена!"))
            return

        result_queue.put(("sys", "Запуск компиляции и загрузки..."))

        # Формируем официальные CLI-команды для старой доброй Arduino IDE 1.8.x
        # --upload: скомпилировать и сразу загрузить в плату
        # --board: жестко указываем платформу Uno (разработчики Mixly делают именно так)
        # --port: COM-порт, выбранный пользователем в Pygame
        upload_cmd = [
            arduino_exe_path,
            "--upload",
            "--board", "arduino:avr:uno",
            "--port", com_port,
            sketch_path
        ]

        # Настройка скрытного запуска процессов для Windows (чтобы не прыгала черная консоль)
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Запускаем оригинальный загрузчик Arduino
        process = subprocess.Popen(
            upload_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo
        )


        # Ждем окончания процесса. communicate() соберет все логи ошибок компиляции C++
        stdout, stderr = process.communicate()

        # Проверяем код возврата программы
        if process.returncode == 0:
            result_queue.put(("sys", "🎉 СКЕТЧ УСПЕШНО ЗАГРУЖЕН В РОБОТА!"))
            result_queue.put(("sys", "status_done"))
        else:
            error_msg = stderr if stderr else stdout
            result_queue.put(("err", "❌ Ошибка сборки C++!"))

            # Разбираем простыню ошибки построчно, чтобы монитор порта корректно их принял
            if error_msg:
                for line in error_msg.splitlines():
                    clean_line = line.strip()
                    if clean_line:
                        result_queue.put(("err", clean_line))


    except Exception as e:
        result_queue.put(("err", f"Внутренняя ошибка загрузчика: {str(e)}"))

# ... (код функции add_toolbox_item) ...
def add_toolbox_item(name, block_type, default_val, color):
    global current_y
    toolbox_buttons.append(ToolboxButton(name, 20, current_y, block_type, default_val, color))
    current_y += 60

# =========================================================================
# ФУНКЦИИ СОХРАНЕНИЯ И ЗАГРУЗКИ (ДО ЦИКЛА WHILE)
# =========================================================================
def save_project_to_json(filename="pygame_project.json"):
    try:
        project_data = []
        for idx, block in enumerate(blocks):
            parent_id = blocks.index(block.parent_block) if block.parent_block in blocks else None
            child_id = blocks.index(block.child_block) if block.child_block in blocks else None

            block_dict = {
                "id": idx,
                "name": block.name,
                "x": block.x,
                "y": block.y,
                "block_type": block.block_type,
                "input_value": block.input_value,
                "input_value2": block.input_value2,
                "color": list(block.color),
                "parent_id": parent_id,
                "child_id": child_id
            }
            project_data.append(block_dict)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=4)
        print(f"🎉 Проект успешно сохранен в файл: {filename}")
    except Exception as e:
        print(f"Ошибка сохранения проекта: {e}")

def load_project_from_json(filename="pygame_project.json"):
    global blocks, selected_block
    if not os.path.exists(filename):
        print(f"Файл сохранения {filename} не найден!")
        return
    try:
        with open(filename, "r", encoding="utf-8") as f:
            project_data = json.load(f)
        new_blocks = []
        for item in project_data:
            cloned_block = Block(
                name=item["name"],
                x=item["x"],
                y=item["y"],
                block_type=item["block_type"],
                default_val=item["input_value2"],
                color=tuple(item["color"])
            )
            cloned_block.input_value = item["input_value"]
            new_blocks.append(cloned_block)

        for idx, item in enumerate(project_data):
            p_id = item["parent_id"]
            c_id = item["child_id"]
            if p_id is not None and p_id < len(new_blocks):
                new_blocks[idx].parent_block = new_blocks[p_id]
            if c_id is not None and c_id < len(new_blocks):
                new_blocks[idx].child_block = new_blocks[c_id]
        blocks = new_blocks
        selected_block = None
        print(f"📂 Проект успешно загружен из файла: {filename}")
    except Exception as e:
        print(f"Ошибка загрузки проекта: {e}")


# --- ИГРОВОЙ ЦИКЛ ПРОГРАММЫ ---
running = True
toolbox_scroll_y = 0
workspace_scroll_y = 0  # Смещение холста по вертикали

is_uploading = False  # Флаг: идет ли сейчас процесс компиляции и прошивки CH340
code_font = pygame.font.SysFont("Courier New", 14)

fon_sound_K.play()

# --- 6. ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ ---
running = True

while running:
    screen.fill(COLOR_BG)
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False

        # =========================================================================
        # --- ЩИТ СОБЫТИЙ ДЛЯ МОДАЛЬНЫХ ОКНО ---
        # =========================================================================
        if app_state == "save_dialog":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Хитбоксы кнопок внутри окна (координаты рассчитываются ниже в рендере)
                win_cx = SCREEN_WIDTH // 2
                win_cy = SCREEN_HEIGHT // 2

                # Клик по кнопке ПОДТВЕРДИТЬ СОХРАНЕНИЕ
                if pygame.Rect(win_cx - 110, win_cy + 30, 100, 35).collidepoint((mx, my)):
                    if save_filename_text.strip():
                        # Подставляем расширение, если пользователь его не написал
                        filename = save_filename_text.strip()
                        if not filename.endswith(".json"): filename += ".json"

                        # Вызываем вашу функцию сохранения, передавая имя файла
                        save_project_to_json(filename)
                        serial_logs.append(("sys", f"[Система]: Проект {filename} сохранен!"))
                    app_state = "workspace"

                # Клик по кнопке ОТМЕНА
                elif pygame.Rect(win_cx + 10, win_cy + 30, 100, 35).collidepoint((mx, my)):
                    app_state = "workspace"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    app_state = "workspace"
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if save_filename_text.strip():
                        filename = save_filename_text.strip()
                        if not filename.endswith(".json"): filename += ".json"
                        save_project_to_json(filename)
                    app_state = "workspace"
                elif event.key == pygame.K_BACKSPACE:
                    save_filename_text = save_filename_text[:-1]
                else:
                    # Разрешаем только безопасные символы для имен файлов (без пробелов и спецсимволов)
                    if event.unicode.isalnum() or event.unicode in ("_", "-"):
                        if len(save_filename_text) < 25:
                            save_filename_text += event.unicode
            continue # Блокируем проход события к холсту!

        elif app_state == "open_dialog":
            win_cx = SCREEN_WIDTH // 2
            win_cy = SCREEN_HEIGHT // 2
            list_rect = pygame.Rect(win_cx - 180, win_cy - 80, 360, 140)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:
                    # Клик по кнопке ОТМЕНА
                    if pygame.Rect(win_cx + 40, win_cy + 80, 120, 35).collidepoint((mx, my)):
                        app_state = "workspace"

                    # Клик по кнопке ЗАГРУЗИТЬ
                    elif pygame.Rect(win_cx - 160, win_cy + 80, 120, 35).collidepoint((mx, my)):
                        if selected_file_idx != -1 and selected_file_idx < len(project_files_list):
                            filename = project_files_list[selected_file_idx]
                            load_project_from_json(filename) # Передаем имя файла в загрузчик
                            serial_logs.append(("sys", f"[Система]: Проект {filename} загружен!"))
                        app_state = "workspace"

                    # Клик по элементам списка файлов
                    elif list_rect.collidepoint((mx, my)):
                        # Считаем, на какую строчку нажал пользователь с учетом скролла
                        relative_y = my - list_rect.y - open_menu_scroll_y
                        clicked_idx = relative_y // 25
                        if 0 <= clicked_idx < len(project_files_list):
                            selected_file_idx = clicked_idx

                # Скролл списка файлов колесиком мыши
                elif event.button == 4: # Вверх
                    open_menu_scroll_y = min(0, open_menu_scroll_y + 20)
                elif event.button == 5: # Вниз
                    max_scroll = -max(0, (len(project_files_list) * 25) - list_rect.height)
                    open_menu_scroll_y = max(max_scroll, open_menu_scroll_y - 20)

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                app_state = "workspace"
            continue # Блокируем проход события к холсту!


        # --- ОБРАБОТКА КЛАВИАТУРЫ ---
        elif event.type == pygame.KEYDOWN:
            # СНАЧАЛА проверяем, пишет ли пользователь в какой-то из блоков прямо сейчас
            is_typing = any(b.is_input_active or b.is_input_active2 for b in blocks)

            # Если активна строка отправки в COM-порт
            if input_send_active:
                if event.key == pygame.K_BACKSPACE:
                    input_send_text = input_send_text[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    # Отправка по нажатию Enter
                    if serial_is_connected and serial_obj and serial_obj.is_open:
                        try:
                            # Отправляем строку, добавляя перевод строки \r\n, как в Arduino IDE
                            serial_obj.write((input_send_text + "\r\n").encode('utf-8'))
                            serial_logs.append(("tx", f"-> {input_send_text}"))
                            input_send_text = "" # Очищаем поле ввода
                        except Exception as e:
                            serial_logs.append(("err", f"Ошибка отправки: {str(e)[:30]}"))
                    else:
                        serial_logs.append(("sys", "Ошибка: Нет подключения к роботу!"))
                elif len(input_send_text) < 40 and event.unicode and event.unicode.isprintable():
                    input_send_text += event.unicode
                continue # Прерываем событие, чтобы не срабатывали глобальные горячие клавиши (Space/Delete)

            # Проверяем, не пишет ли пользователь цифры/буквы в поля ввода прямо сейчас
            if not is_typing:

                # SPACE — Сборка кода Arduino (Финальная неубиваемая версия)
                # SPACE — Сборка кода Arduino (Версия с форматированием %s для PyScript)
                if event.key == pygame.K_SPACE:
                    print("\nСборка кода скетча...")

                    code_global = []
                    code_setup = []
                    code_loop = []
                    # Список для хранения тел пользовательских функций
                    code_functions = []

                    setup_root = next((b for b in blocks if b.block_type == "core_setup"), None)
                    loop_root = next((b for b in blocks if b.block_type == "core_loop"), None)

                    # 1. Собираем цепочку НАСТРОЙКИ (setup)
                    if setup_root and setup_root.child_block:
                        current = setup_root.child_block
                        while current:
                            block_data = current.get_structured_code(blocks)
                            if block_data["global"]:
                                for line in block_data["global"].split("\n"):
                                    clean_line = line.strip()
                                    if clean_line:
                                        if clean_line.startswith("#include"):
                                            if clean_line not in code_global:
                                                code_global.append(clean_line)
                                        else:
                                            code_global.append(clean_line)

                            if block_data["setup"]:
                                code_setup.append(block_data["setup"].rstrip())
                            if block_data["loop"]:
                                if block_data["loop"].rstrip():
                                    code_setup.append(block_data["loop"].rstrip())

                            current = current.child_block

                    # 2. Собираем цепочку ГЛАВНОГО ЦИКЛА (loop)
                    if loop_root and loop_root.child_block:
                        current = loop_root.child_block
                        while current:
                            block_data = current.get_structured_code(blocks)
                            if block_data["global"]:
                                clean_line = block_data["global"].strip()
                                if clean_line and clean_line not in code_global:
                                    code_global.append(clean_line)

                            if block_data["loop"]:
                                code_loop.append(block_data["loop"].rstrip())
                            elif block_data["setup"]:
                                code_loop.append(block_data["setup"].rstrip())

                            current = current.child_block

                    # --- 3. СБОРКА ПОЛЬЗОВАТЕЛЬСКИХ ФУНКЦИЙ ---
                    # Ищем все шапки функций, лежащие на холсте (у которых нет родителя)
                    func_roots = [b for b in blocks if b.block_type == "func_definition" and b.parent_block is None]

                    for f_root in func_roots:
                        func_name = f_root.input_value.strip() if f_root.input_value.strip() else "myFunction"

                        # Добавляем прототип в глобальную область, чтобы компилятор знал о функции
                        prototype = f"void {func_name}();"
                        if prototype not in code_global:
                            code_global.append(prototype)

                        # Начинаем собирать тело функции void name() {
                        code_functions.append(f"\nvoid {func_name}() {{")

                        # Обходим цепочку блоков, прикрепленных снизу к этой шапке
                        current = f_root.child_block
                        while current:
                            block_data = current.get_structured_code(blocks)

                            if block_data["global"]:
                                for line in block_data["global"].split("\n"):
                                    clean_line = line.strip()
                                    if clean_line and clean_line not in code_global:
                                        code_global.append(clean_line)

                            if block_data["setup"]:
                                code_functions.append("  " + block_data["setup"].strip())

                            if block_data["loop"]:
                                code_functions.append("  " + block_data["loop"].strip())

                            current = current.child_block

                        # Закрываем тело функции }
                        code_functions.append("}")

                    # --- 4. ОБЪЕДИНЕНИЕ СТРОК ---
                    global_content = "\n".join(code_global)

                    setup_clean_lines = []
                    for line in code_setup:
                        if line.strip():
                            setup_clean_lines.append("  " + line.strip())
                    setup_content = "\n".join(setup_clean_lines)

                    loop_clean_lines = []
                    for line in code_loop:
                        if line.strip():
                            loop_clean_lines.append("  " + line.strip())
                    loop_content = "\n".join(loop_clean_lines)

                    # Объединяем строки всех созданных функций
                    functions_content = "\n".join(code_functions)

                    # Расширенный плоский текстовый шаблон (добавлено четвертое поле %s)
                    template = (
                        "// Автоматически сгенерировано в Pygame-CE\n"
                        "%s\n\nvoid setup() {\n"
                        "%s\n}"
                        "\n\nvoid loop() {\n"
                        "%s\n}\n"
                        "%s\n"
                    )

                    # Подстановка через кортеж из 4 аргументов
                    final_sketch = template % (global_content, setup_content, loop_content, functions_content)

                    current_arduino_code_text = final_sketch  # Сохраняем для вывода на экран


                    # Сохранение в файл (с защитой от ограничений браузерной ФС)
                    try:
                        os.makedirs("pygame_sketch", exist_ok=True)
                        with open("pygame_sketch/pygame_sketch.ino", "w", encoding="utf-8") as f:
                            f.write(final_sketch)
                    except Exception as e:
                        print("Уведомление ФС:", e)

                    print("--- СГЕНЕРИРОВАННЫЙ ФАЙЛ ---\n", final_sketch)


                elif event.key == pygame.K_l and not is_uploading:
                    print("\nИнициирована портативная прошивка робота через L...")

                    # 1. Шаг проверки: сохранен ли скетч
                    sketch_dir = "pygame_sketch"
                    sketch_file = os.path.join(sketch_dir, "pygame_sketch.ino")

                    if not os.path.exists(sketch_file):
                        serial_queue.put(("err", "Скетч еще не собран! Нажмите сначала SPACE."))
                        continue

                    # 2. Шаг освобождения порта: если монитор порта активен, закрываем его
                    if serial_is_connected:
                        serial_logs.append(("sys", "[Система]: Освобождаем порт для прошивки CH340..."))
                        serial_stop_flag.set() # Сигнал фоновому потоку чтения завершиться
                        if serial_obj:
                            try:
                                serial_obj.close()
                            except Exception:
                                pass
                        serial_is_connected = False

                    # 3. Шаг блокировки интерфейса
                    is_uploading = True
                    serial_logs.append(("sys", "[Загрузка]: Подготовка компилятора Arduino..."))

                    # Получаем абсолютный путь к файлу скетча
                    abs_sketch_path = os.path.abspath(sketch_file)

                    # 4. Шаг запуска: отправляем задачу в отдельный фоновый тред
                    # Используем вашу родную serial_queue, чтобы логи летели прямо в терминал Pygame
                    uploader_thread = threading.Thread(
                        target=flash_via_portable_ide,
                        args=(current_com_port, abs_sketch_path, serial_queue),
                        daemon=True
                    )
                    uploader_thread.start()


                # DELETE — Удаление выбранного блока
                elif event.key == pygame.K_DELETE and selected_block is not None:
                    if "core_" in selected_block.block_type:
                        print("Нельзя удалить главные функции Arduino!")
                        continue

                    if selected_block.parent_block:
                        selected_block.parent_block.child_block = None

                    to_remove = []
                    current = selected_block
                    while current:
                        to_remove.append(current)
                        current = current.child_block

                    for b in to_remove:
                        if b in blocks: blocks.remove(b)
                    selected_block = None

                # КЛАВИША R — Очистить холст (кроме главных функций)
                elif event.key == pygame.K_r:
                    setup_root = next((b for b in blocks if b.block_type == "core_setup"), None)
                    loop_root = next((b for b in blocks if b.block_type == "core_loop"), None)
                    if setup_root: setup_root.child_block = None
                    if loop_root: loop_root.child_block = None

                    blocks = [setup_root, loop_root] if setup_root and loop_root else []
                    selected_block = None
                    print("Холст очищен!")


                # --- КОПИРОВАНИЕ (CTRL + C) ---
                if event.key == pygame.K_c and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    if selected_block is not None and "core_" not in selected_block.block_type:
                        print("Копирование цепочки блоков...")
                        clipboard_blocks = []

                        # Собираем всю цепочку от выбранного блока до самого низа
                        current = selected_block
                        while current:
                            clipboard_blocks.append(current)
                            current = current.child_block
                        print(f"Скопировано блоков: {len(clipboard_blocks)}")

                # --- ВСТАВКА (CTRL + V) ---
                elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    if clipboard_blocks:
                        print("Вставка цепочки блоков...")

                        # Получаем текущие координаты мыши, чтобы вставить блок ровно под курсор
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        # Учитываем скролл холста, чтобы вставить блок в правильные мировые координаты
                        world_mouse_y = mouse_y + workspace_scroll_y

                        new_chain = []
                        # 1. Создаем новые независимые клоны блоков
                        for i, old_block in enumerate(clipboard_blocks):
                            # Для первого блока берем позицию мыши, для остальных — позицию со смещением вниз
                            if i == 0:
                                new_x = mouse_x - 50 # Небольшой отступ влево, чтобы не перекрывать курсор
                                new_y = world_mouse_y
                            else:
                                new_x = mouse_x - 50
                                # Высчитываем Y на основе высоты предыдущих вставленных блоков
                                new_y = new_chain[-1].y + new_chain[-1].height + 2

                            # Создаем новый глубокий клон блока
                            cloned_block = Block(
                                name=old_block.name,
                                x=new_x,
                                y=new_y,
                                block_type=old_block.block_type,
                                default_val=old_block.input_value2,
                                color=old_block.color
                            )
                            # Переносим значение первого инпута, которое не передается через default_val
                            cloned_block.input_value = old_block.input_value

                            new_chain.append(cloned_block)

                        # 2. Восстанавливаем внутренние связи внутри ТОЛЬКО ЧТО созданной цепочки
                        for i in range(len(new_chain) - 1):
                            new_chain[i].child_block = new_chain[i+1]
                            new_chain[i+1].parent_block = new_chain[i]

                        # 3. Добавляем всю новую цепочку на холст программы
                        for cloned_block in new_chain:
                            blocks.append(cloned_block)

                        # Делаем голову новой цепочки выделенной, чтобы её можно было сразу двигать
                        selected_block = new_chain[0]
                        print("Вставка успешно завершена!")

            else:
                # ИСПРАВЛЕНО: Если пользователь СЕЙЧАС пишет текст (is_typing == True),
                # мы принудительно передаем нажатую клавишу во все блоки сцены.
                # Активный блок поймает её внутри своего метода handle_event.
                for block in blocks:
                    block.handle_event(event, blocks, workspace_scroll_y)

        elif event.type == pygame.MOUSEBUTTONDOWN:

            # --- СКРОЛЛИНГ КОЛЕСИКОМ (Кнопки 4 и 5) ---
            if event.button in (4, 5):
                # 1. Если мышка в левой части экрана — крутим ТУЛБОКС
                if event.pos[0] < PANEL_WIDTH:
                    max_scroll = max(0, total_menu_height - (SCREEN_HEIGHT - 35))
                    if event.button == 4: toolbox_scroll_y = min(0, toolbox_scroll_y + 25)
                    elif event.button == 5: toolbox_scroll_y = max(-max_scroll, toolbox_scroll_y - 25)

                # 2. Если мышка в основной или правой части экрана
                else:
                    # Ограничиваем область самого терминала логов (высота 130px от monitor_y)
                    terminal_rect = pygame.Rect(PANEL_WIDTH, SCREEN_HEIGHT - 170, code_panel_x - PANEL_WIDTH, 130)

                    if terminal_rect.collidepoint(event.pos):
                        # Скроллим монитор порта
                        if event.button == 4:  # Колесико вверх (старые логи)
                            max_log_scroll = max(0, len(serial_logs) - max_visible_lines)
                            if scroll_offset < max_log_scroll:
                                scroll_offset += 1
                        elif event.button == 5:  # Колесико вниз (новые логи)
                            if scroll_offset > 0:
                                scroll_offset -= 1

                    # --- НАЧАЛО ВСТАВКИ ДЛЯ СКРОЛЛИНГА ПАНЕЛИ КОДА ---

                    # --- ИСПРАВЛЕННЫЙ СКРОЛЛИНГ ПАНЕЛИ КОДА ---
                    elif event.pos[0] > code_panel_x:
                        # Считаем актуальное количество строк прямо из текущего текста скетча
                        lines_count = len(current_arduino_code_text.split("\n"))
                        total_text_height = lines_count * 20
                        visible_height = SCREEN_HEIGHT - 185 # Высота панели кода до терминала

                        # Расчитываем "дно" прокрутки с запасом в 80 пикселей, чтобы код не упирался впритык
                        max_code_scroll = -max(0, total_text_height - visible_height + 80)

                        if event.button == 4:    # Колесико вверх (к началу кода)
                            code_panel_scroll_y = min(0, code_panel_scroll_y + 25)
                        elif event.button == 5:  # Колесико вниз (к концу кода)
                            code_panel_scroll_y = max(max_code_scroll, code_panel_scroll_y - 25)

                    # --- КОНЕЦ ВСТАВКИ ДЛЯ СКРОЛЛИНГА ПАНЕЛИ КОДА ---

                    else:
                        # Если мышка НЕ над терминалом и НЕ над кодом, крутим ХОЛСТ
                        if event.button == 4: workspace_scroll_y = max(0, workspace_scroll_y - 25)
                        elif event.button == 5: workspace_scroll_y += 25
                continue


            # --- НАЖАТИЕ ЛЕВОЙ КНОПКИ МЫШИ (Кнопка 1) ---
            if event.button == 1:
                # Воспроизводим звук клика, если файл успешно загрузился
                if click_sound:
                    click_sound.play()

                #Клик по кнопке Подключить / Отключить
                if btn_connect_rect.collidepoint(event.pos):
                    #global serial_obj, serial_is_connected, serial_stop_flag
                    if not serial_is_connected:
                        try:
                            # Пробуем открыть порт (таймаут 1 сек, чтобы не вешать Pygame)
                            serial_obj = serial.Serial(current_com_port, current_baudrate, timeout=1)
                            serial_is_connected = True
                            serial_stop_flag.clear()
                            # Запускаем фоновый поток чтения
                            t = threading.Thread(target=serial_read_thread, args=(serial_obj, serial_queue, serial_stop_flag), daemon=True)
                            t.start()
                            serial_logs.append(("sys", f"Connected to {current_com_port} ({current_baudrate} bps)"))
                        except Exception as e:
                            serial_logs.append(("err", f"Ошибка: {str(e)[:30]}"))
                    else:
                        # Отключение
                        serial_stop_flag.set()
                        if serial_obj and serial_obj.is_open:
                            serial_obj.close()
                        serial_is_connected = False
                        serial_logs.append(("sys", "Disconnected."))
                    continue

                # Клик по кнопке выбора COM-порта
                if not serial_is_connected and btn_port_rect.collidepoint(event.pos):
                    # Обновляем список портов на случай, если робота только что воткнули в USB
                    available_ports = [p.device for p in serial.tools.list_ports.comports()]
                    if not available_ports: available_ports = ["COM1", "COM2", "COM3", "COM4", "COM5"]

                    # Циклически переключаем индекс
                    try:
                        idx = available_ports.index(current_com_port)
                        current_com_port = available_ports[(idx + 1) % len(available_ports)]
                    except ValueError:
                        current_com_port = available_ports[0]
                    serial_logs.append(("sys", f"Выбран порт: {current_com_port}"))
                    continue

                # Клик по кнопке выбора СКОРОСТИ
                if not serial_is_connected and btn_baud_rect.collidepoint(event.pos):
                    # Циклически переключаем индекс скорости
                    idx = available_baudrates.index(current_baudrate)
                    current_baudrate = available_baudrates[(idx + 1) % len(available_baudrates)]
                    serial_logs.append(("sys", f"Выбрана скорость: {current_baudrate} bps"))
                    continue

                # --- НОВАЯ КНОПКА: Клик по кнопке ОЧИСТИТЬ (CLEAR) ---
                if btn_clear_rect.collidepoint(event.pos):
                    serial_logs.clear()
                    scroll_offset = 0
                    continue

                # --- ИСПРАВЛЕННАЯ КНОПКА СОХРАНИТЬ (SAVE) ---
                if btn_save_rect.collidepoint(event.pos):
                    app_state = "save_dialog"
                    save_input_active = True
                    continue

                # --- ИСПРАВЛЕННАЯ КНОПКА ОТКРЫТЬ (OPEN) ---
                if btn_open_rect.collidepoint(event.pos):
                    app_state = "open_dialog"
                    # Сканируем текущую папку на наличие файлов проектов
                    try:
                        project_files_list = [f for f in os.listdir(".") if f.endswith(".json")]
                    except Exception:
                        project_files_list = []
                    selected_file_idx = -1
                    open_menu_scroll_y = 0
                    continue


                # Клик по полю ввода для отправки данных в робота
                if input_send_rect.collidepoint(event.pos):
                    input_send_active = True
                    selected_block = None # Снимаем выделение с блоков холста
                    # Снимаем фокус со всех инпутов блоков, чтобы клавиатура переключилась на терминал
                    for b in blocks:
                        b.is_input_active = False
                        b.is_input_active2 = False
                    continue
                else:
                    input_send_active = False

                # 1. СТРОГО ПЕРВЫМ ДЕЛОМ: Проверяем захват правой границы кода!
                # Используем погрешность в 6 пикселей для удобства клика
                if abs(event.pos[0] - code_panel_x) < 6:
                    is_resizing_code_panel = True
                    is_dragging_scrollbar = False # Защита от конфликта
                    selected_block = None
                    continue # Пропускаем остальные проверки, мы поймали границу!

                # 2. ВТОРЫМ ДЕЛОМ: Проверяем захват бегунка левой панели
                if total_menu_height > (SCREEN_HEIGHT - 35) and scrollbar_rect.collidepoint(event.pos):
                    is_dragging_scrollbar = True
                    scrollbar_drag_offset_y = event.pos[1] - scrollbar_rect.y
                    continue

                # 3. ТРЕТЬИМ ДЕЛОМ: Проверяем клик по кнопкам внутри левой панели
                if event.pos[0] < PANEL_WIDTH:
                    adjusted_pos = (event.pos[0], event.pos[1] - toolbox_scroll_y)
                    adjusted_event = pygame.event.Event(event.type, {**event.dict, 'pos': adjusted_pos})

                    button_clicked = False
                    for btn in toolbox_buttons:
                        if btn.handle_event(adjusted_event, blocks, workspace_scroll_y):
                            button_clicked = True
                            selected_block = blocks[-1]

                            # ВЗВОДИМ ГЛОБАЛЬНЫЙ ФЛАГ ПЕРЕТАСКИВАНИЯ НОВОГО БЛОКА
                            is_dragging_new_block = True
                            break
                    if button_clicked:
                        continue


                # 4. ЧЕТВЕРТЫМ ДЕЛОМ: Если кликнули на холст, сбрасываем выделение и ищем блоки
                selected_block = None
                for i, block in enumerate(reversed(blocks)):
                    if block.handle_event(event, blocks, workspace_scroll_y):
                        if block.is_dragging:
                            selected_block = block

                            # === НАШЕ ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ЗДЕСЬ ===
                            # Получаем абсолютно чистые физические координаты мыши на экране в момент клика
                            mx, my = pygame.mouse.get_pos()

                            # Вычисляем экранный Y блока строго на основе его мировой координаты
                            render_y_block = selected_block.y - workspace_scroll_y

                            # Жёстко перезаписываем офсеты в чистом экранном формате (Экран минус Экран)
                            selected_block.drag_offset_x = selected_block.x - mx
                            selected_block.drag_offset_y = render_y_block - my

                            # Реализуем Z-order (перенос на передний план)
                            real_idx = len(blocks) - 1 - i
                            moving_block = blocks.pop(real_idx)
                            blocks.append(moving_block)
                        break


        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                is_dragging_scrollbar = False  # Сброс левой панели
                is_resizing_code_panel = False   # Сброс правой панели (проверьте, чтобы эта строка была!)
                is_dragging_new_block = False

            for block in reversed(blocks):
                block.handle_event(event, blocks, workspace_scroll_y)
                break

        elif event.type == pygame.MOUSEMOTION:
            # --- ПРИОРИТЕТ №0: ЕСЛИ МЫ ТАЩИМ НОВЫЙ БЛОК ИЗ ТУЛБОКСА ---
            if is_dragging_new_block and selected_block:
                mx, my = pygame.mouse.get_pos()
                new_x = mx - selected_block.width // 2
                new_y_world = my - selected_block.height // 2 + workspace_scroll_y
                selected_block.update_position(int(new_x), int(new_y_world))
                continue

            # --- ПРИОРИТЕТ №0.5: ЕСЛИ МЫ ПОВТОРНО ТАЩИМ СУЩЕСТВУЮЩИЙ БЛОК НА ХОЛСТЕ ---
            elif selected_block and getattr(selected_block, 'is_dragging', False):
                mx, my = pygame.mouse.get_pos()

                # Используем экранные офсеты, которые блок честно посчитал при клике (MOUSEBUTTONDOWN)
                new_x = mx + selected_block.drag_offset_x
                new_y_world = my + selected_block.drag_offset_y + workspace_scroll_y

                # Двигаем блок напрямую из главного цикла строго один раз за кадр!
                selected_block.update_position(int(new_x), int(new_y_world))
                continue

            # --- 1. ЕСЛИ ТАЩИМ БЕГУНОК ЛЕВОЙ ПАНЕЛИ ---
            elif is_dragging_scrollbar:
                track_height = SCREEN_HEIGHT - 35
                max_scrollbar_travel = track_height - scrollbar_rect.height
                if max_scrollbar_travel > 0:
                    new_scrollbar_y = event.pos[1] - scrollbar_drag_offset_y
                    new_scrollbar_y = max(0, min(max_scrollbar_travel, new_scrollbar_y))
                    max_menu_travel = total_menu_height - track_height
                    toolbox_scroll_y = -int((new_scrollbar_y / max_scrollbar_travel) * max_menu_travel)
                continue

            # --- 2. ЕСЛИ ТАЩИМ РАЗДЕЛИТЕЛЬ ПРАВОЙ ПАНЕЛИ КОДА ---
            elif is_resizing_code_panel:
                new_x = event.pos[0]
                min_x = SCREEN_WIDTH - MAX_CODE_PANEL_WIDTH
                max_x = SCREEN_WIDTH - MIN_CODE_PANEL_WIDTH
                code_panel_x = max(min_x, min(max_x, new_x))
                continue

            # --- 3. ЕСЛИ ОБЕ ПАНЕЛИ НЕ АКТИВНЫ: ОТДАЕМ ДВИЖЕНИЕ БЛОКАМ НА ХОЛСТЕ ---
            else:
                for block in reversed(blocks):
                    # === ДОБАВЛЯЕМ ПРОВЕРКУ И BREAK ЗДЕСЬ ===
                    # Если блок обработал движение мыши, мы НЕМЕДЛЕННО останавливаем цикл for,
                    # чтобы событие движения не передавалось другим блокам на заднем плане!
                    if block.handle_event(event, blocks, workspace_scroll_y):
                        break


    # >>> ТОЧНОЕ МЕСТО ДЛЯ ТРЕТЬЕГО ШАГА <<<
    # Цикл перебора событий (for event in events) ЗАВЕРШИЛСЯ.
    # Но мы все еще внутри главного цикла (while running), перед отрисовкой!

    while not serial_queue.empty():
        try:
            msg_type, msg_val = serial_queue.get_nowait()

            # Логика управления автопрошивкой
            if msg_val == "status_done":
                is_uploading = False
                try:
                    serial_obj = serial.Serial(current_com_port, current_baudrate, timeout=0.1)
                    serial_stop_flag.clear()
                    threading.Thread(target=serial_read_thread, args=(serial_obj, serial_queue, serial_stop_flag), daemon=True).start()
                    serial_is_connected = True
                    serial_logs.append(("sys", "[Система]: Порт CH340 снова перехвачен."))
                except Exception as e:
                    serial_logs.append(("err", f"[Ошибка возврата порта]: {e}"))

            elif msg_type == "err":
                serial_logs.append(("err", msg_val))
                is_uploading = False

            elif msg_type == "sys":
                serial_logs.append(("sys", msg_val))

            elif msg_type == "rx":
                serial_logs.append(("rx", f"[RX]: {msg_val}"))
            elif msg_type == "tx_user":
                serial_logs.append(("tx", f"[TX]: {msg_val}"))

        except queue.Empty:
            break


    # --- 7. РЕНДЕРИНГ ИНТЕРФЕЙСА ---

    # Сначала рисуем неподвижные блоки холста (Передаем скролл!)
    for block in blocks:
        is_part_of_drag = block.is_dragging
        parent = block.parent_block
        while parent:
            if parent.is_dragging:
                is_part_of_drag = True
                break
            parent = parent.parent_block

        if not is_part_of_drag:
            # ДОПИСАЛИ scroll_y=workspace_scroll_y
            block.draw(screen, is_selected=(block == selected_block), scroll_y=workspace_scroll_y)

    # Затем рисуем перетаскиваемые блоки (они парят над холстом, для них scroll_y=0)
    for block in blocks:
        if block.is_dragging:
            block.draw(screen, is_selected=(block == selected_block), scroll_y=workspace_scroll_y)
            current = block.child_block
            while current:
                current.draw(screen, is_selected=(current == selected_block), scroll_y=workspace_scroll_y)
                current = current.child_block


    # Отрисовка левой панели тулбокса поверх блоков холста
    pygame.draw.rect(screen, COLOR_PANEL_BG, (0, 0, PANEL_WIDTH, SCREEN_HEIGHT - 35))

    # --- УМНАЯ ОТРИСОВКА КНОПОК С УЧЕТОМ СКРОЛЛА ---
    # Считаем общую высоту меню один раз на основе исходных (фиксированных) позиций кнопок
    if toolbox_buttons:
        total_menu_height = toolbox_buttons[-1].rect.bottom - toolbox_buttons[0].rect.y + 90
    else:
        total_menu_height = 0

    track_height = SCREEN_HEIGHT - 35

    # Рисуем кнопки, временно смещая их RECT только в момент отрисовки!
    for btn in toolbox_buttons:
        original_y = btn.rect.y
        btn.rect.y += toolbox_scroll_y  # Сдвигаем на скролл для отрисовки

        # Рисуем только те кнопки, которые физически видны на экране
        if btn.rect.bottom > 0 and btn.rect.y < track_height:
            btn.draw(screen)

        btn.rect.y = original_y  # Мгновенно возвращаем исходную координату обратно в память!

    # --- ДИНАМИЧЕСКИЙ РАСЧЕТ И ОТРИСОВКА БЕГУНКА ---
    if total_menu_height > track_height:
        scrollbar_height = max(30, int((track_height / total_menu_height) * track_height))
        max_scrollbar_travel = track_height - scrollbar_height
        max_menu_travel = total_menu_height - track_height

        # Вычисляем Y бегунка на основе текущего toolbox_scroll_y
        if max_menu_travel > 0:
            scrollbar_y = int((-toolbox_scroll_y / max_menu_travel) * max_scrollbar_travel)
        else:
            scrollbar_y = 0

        scrollbar_rect = pygame.Rect(PANEL_WIDTH - SCROLLBAR_WIDTH - 4, scrollbar_y, SCROLLBAR_WIDTH, scrollbar_height)

        # Рисуем дорожку трека
        pygame.draw.rect(screen, (200, 205, 210), (PANEL_WIDTH - SCROLLBAR_WIDTH - 6, 0, SCROLLBAR_WIDTH + 4, track_height))
        # Рисуем сам бегунок
        COLOR_SCROLLBAR = (100, 110, 120) if is_dragging_scrollbar else (150, 155, 160)
        pygame.draw.rect(screen, COLOR_SCROLLBAR, scrollbar_rect, border_radius=6)


    # --- ИСПРАВЛЕНО: ПЛАШКА И ПОДСКАЗКА СТРОГО ВНИЗУ ЭКРАНА ---
    # Рисуем небольшую полосу цвета фона холста, чтобы блоки не просвечивали под текстом
    pygame.draw.rect(screen, COLOR_BG, (PANEL_WIDTH + 5, SCREEN_HEIGHT - 35, SCREEN_WIDTH - PANEL_WIDTH, 35))

    # =========================================================================
    # --- ОТРИСОВКА МОНИТОРА ПОРТА (ТЕРМИНАЛА) ВНИЗУ ЭКРАНА ---
    # =========================================================================
    # Выделяем под терминал нижнюю область высотой 160 пикселей (от холста до низа)
    monitor_y = SCREEN_HEIGHT - 170
    monitor_width = code_panel_x - PANEL_WIDTH # Ширина от левого меню до правой панели кода

    # 1. Задний фон терминала логов
    pygame.draw.rect(screen, COLOR_MON_BG, (PANEL_WIDTH, monitor_y, monitor_width, 130))
    # Тонкая разделительная линия сверху терминала
    pygame.draw.line(screen, COLOR_PANEL_BORDER, (PANEL_WIDTH, monitor_y), (code_panel_x, monitor_y), width=2)

    # 2. Вывод логов (построчно снизу вверх)
    # 2. Вывод логов с поддержкой прокрутки (скролла)
    log_font = pygame.font.SysFont("Courier New", 13)

    # Создаем невидимую маску-границу, чтобы текст физически не мог вылезти за пределы серого фона терминала
    screen.set_clip(pygame.Rect(PANEL_WIDTH + 5, monitor_y + 5, monitor_width - 10, 120))

    # Вычисляем, какие строки из истории логов нам нужно показать
    total_lines = len(serial_logs)

    if total_lines <= max_visible_lines:
        # Если строк мало, отображаем их просто с начала
        visible_lines = serial_logs
        scroll_offset = 0 # Скроллить пока нечего
    else:
        # Индексы для среза списка с конца с учетом скролла
        start_idx = max(0, total_lines - max_visible_lines - scroll_offset)
        end_idx = total_lines - scroll_offset
        visible_lines = serial_logs[start_idx:end_idx]

    # Отрисовываем только видимую часть логов
    curr_log_y = monitor_y + 5
    for m_type, text in visible_lines:
        if m_type == "rx": color = COLOR_MON_TEXT      # Принято (зеленый)
        elif m_type == "tx": color = COLOR_MON_SEND    # Отправлено (синий)
        elif m_type == "err": color = (231, 76, 60)    # Ошибка (красный)
        else: color = (149, 165, 166)                  # Системное (серое)

        log_surf = log_font.render(text, True, color)
        screen.blit(log_surf, (PANEL_WIDTH + 15, curr_log_y))
        curr_log_y += 16

    # Сбрасываем маску отсечения, чтобы остальной интерфейс (меню, блоки) рисовался нормально
    screen.set_clip(None)

    # 3. Нижняя панель управления (Кнопка и Строка ввода)
    pygame.draw.rect(screen, COLOR_PANEL_BG, (PANEL_WIDTH, SCREEN_HEIGHT - 45, monitor_width, 45))
    pygame.draw.line(screen, COLOR_PANEL_BORDER, (PANEL_WIDTH, SCREEN_HEIGHT - 45), (code_panel_x, SCREEN_HEIGHT - 45), width=1)

    # Рисуем кнопку Подключить/Отключить
    btn_color = COLOR_BTN_DISC if serial_is_connected else COLOR_BTN_CONN
    btn_text = "DISCONNECT" if serial_is_connected else "CONNECT"
    pygame.draw.rect(screen, btn_color, btn_connect_rect, border_radius=4)
    btn_surf = font.render(btn_text, True, (255, 255, 255))
    screen.blit(btn_surf, (btn_connect_rect.x + (btn_connect_rect.width - btn_surf.get_width())//2, btn_connect_rect.y + 4))

    # Рисуем поле ввода текста для отправки команд
    input_border = COLOR_INPUT_ACTIVE if input_send_active else COLOR_PANEL_BORDER
    pygame.draw.rect(screen, COLOR_INPUT_BG, input_send_rect, border_radius=4)
    pygame.draw.rect(screen, input_border, input_send_rect, border_radius=4, width=2)

    # Текст внутри поля ввода отправки
    if input_send_text:
        send_surf = log_font.render(input_send_text, True, COLOR_INPUT_TEXT)
        screen.blit(send_surf, (input_send_rect.x + 6, input_send_rect.y + 5))
    elif not input_send_active:
        # Подсказка-плейсхолдер, если поле пустое
        placeholder = log_font.render("Введите команду и нажмите ENTER...", True, (170, 175, 180))
        screen.blit(placeholder, (input_send_rect.x + 6, input_send_rect.y + 5))


    # Вычисляем позиции интерактивных кнопок выбора справа от поля ввода
    start_x = input_send_rect.right + 20

    # 1. Текст и хитбокс для выбора Порта
    port_text = f"Port: {current_com_port}"
    port_surf = font.render(port_text, True, (41, 128, 185) if not serial_is_connected else (127, 140, 141))
    btn_port_rect = pygame.Rect(start_x, SCREEN_HEIGHT - 38, port_surf.get_width() + 10, 28)

    # Рисуем рамку вокруг выбора порта, если подключение закрыто (показываем, что кликабельно)
    if not serial_is_connected:
        pygame.draw.rect(screen, (220, 225, 230), btn_port_rect, border_radius=4)
        pygame.draw.rect(screen, (180, 185, 190), btn_port_rect, width=1, border_radius=4)
    screen.blit(port_surf, (btn_port_rect.x + 5, SCREEN_HEIGHT - 34))

    # 2. Текст и хитбокс для выбора Скорости
    baud_text = f"Baud: {current_baudrate}"
    baud_surf = font.render(baud_text, True, (41, 128, 185) if not serial_is_connected else (127, 140, 141))
    btn_baud_rect = pygame.Rect(btn_port_rect.right + 15, SCREEN_HEIGHT - 38, baud_surf.get_width() + 10, 28)

    # 3. Текст и хитбокс для кнопки Очистить (CLEAR)
    btn_clear_rect = pygame.Rect(btn_baud_rect.right + 15, SCREEN_HEIGHT - 38, 80, 28)
    pygame.draw.rect(screen, (231, 76, 60), btn_clear_rect, border_radius=4) # Красный цвет кнопки
    clear_surf = font.render("CLEAR", True, (255, 255, 255))
    screen.blit(clear_surf, (btn_clear_rect.x + (btn_clear_rect.width - clear_surf.get_width())//2, btn_clear_rect.y + 4))

    # Хитбоксы для новых кнопок сохранения и загрузки (объявляем перед циклом)
    btn_save_rect = pygame.Rect(0, 0, 0, 0)  # Рассчитаем динамически при рендеринге
    btn_open_rect = pygame.Rect(0, 0, 0, 0)  # Рассчитаем динамически при рендеринге

    # 4. Текст и хитбокс для кнопки СОХРАНИТЬ (SAVE)
    # Ставим её правее кнопки CLEAR на 15 пикселей. Цвет сделаем синим (или любым другим)
    btn_save_rect = pygame.Rect(btn_clear_rect.right + 15, SCREEN_HEIGHT - 38, 70, 28)
    pygame.draw.rect(screen, (41, 128, 185), btn_save_rect, border_radius=4)
    save_surf = font.render("SAVE", True, (255, 255, 255))
    screen.blit(save_surf, (btn_save_rect.x + (btn_save_rect.width - save_surf.get_width())//2, btn_save_rect.y + 4))

    # 5. Текст и хитбокс для кнопки ОТКРЫТЬ (OPEN)
    # Ставим её правее кнопки SAVE на 15 пикселей. Цвет сделаем зеленым (как у CONNECT)
    btn_open_rect = pygame.Rect(btn_save_rect.right + 15, SCREEN_HEIGHT - 38, 70, 28)
    pygame.draw.rect(screen, (39, 174, 96), btn_open_rect, border_radius=4)
    open_surf = font.render("OPEN", True, (255, 255, 255))
    screen.blit(open_surf, (btn_open_rect.x + (btn_open_rect.width - open_surf.get_width())//2, btn_open_rect.y + 4))


    # Рисуем рамку вокруг выбора скорости
    if not serial_is_connected:
        pygame.draw.rect(screen, (220, 225, 230), btn_baud_rect, border_radius=4)
        pygame.draw.rect(screen, (180, 185, 190), btn_baud_rect, width=1, border_radius=4)
    screen.blit(baud_surf, (btn_baud_rect.x + 5, SCREEN_HEIGHT - 34))


    # =========================================================================
    # --- ОТРИСОВКА ПРАВОЙ ПАНЕЛИ КОДА И РАЗДЕЛИТЕЛЯ ---
    # =========================================================================
    code_panel_width = SCREEN_WIDTH - code_panel_x

    # 1. Рисуем подложку для панели кода (тёмно-серый футуристичный цвет)
    COLOR_CODE_BG = (30, 32, 35)
    pygame.draw.rect(screen, COLOR_CODE_BG, (code_panel_x, 0, code_panel_width, SCREEN_HEIGHT - 35))

    # 2. Рисуем вертикальную интерактивную границу-разделитель
    # Если мы её тащим — подсвечиваем оранжевым, иначе серая
    COLOR_SPLITTER = (230, 126, 34) if is_resizing_code_panel else (149, 165, 166)
    pygame.draw.line(screen, COLOR_SPLITTER, (code_panel_x, 0), (code_panel_x, SCREEN_HEIGHT - 35), width=3)

    # Меняем курсор мыши на стрелочки "влево-вправо", если навели на границу
    if abs(pygame.mouse.get_pos()[0] - code_panel_x) < 5 or is_resizing_code_panel:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # 3. Вывод самого текста скетча Arduino с защитой от вылезания (Маскирование)
    # Создаем временную поверхность (Surface) строго по размеру панели кода
    # Флаг pygame.SRCALPHA позволяет тексту правильно ложиться без черных артефактов

    # =========================================================================
    # --- ИСПРАВЛЕННАЯ ОТРИСОВКА ПРАВОЙ ПАНЕЛИ КОДА СО СКРОЛЛОМ ---
    # =========================================================================
    lines = current_arduino_code_text.split("\n")

    # 1. Рассчитываем необходимую высоту контейнера под весь объем текста с запасом
    total_text_height = max(SCREEN_HEIGHT - 60, len(lines) * 20 + 40)

    # Создаем временную поверхность под полную высоту кода
    text_container = pygame.Surface((code_panel_width - 20, total_text_height), pygame.SRCALPHA)

    # Стартуем отрисовку строк внутри контейнера с фиксированного Y=15 (БЕЗ скролла!)
    line_y = 15

    for line in lines:
        clean_line = line.strip()

        # --- ВАШ РАБОТАЮЩИЙ КОД ПОДСВЕТКИ СИНТАКСИСА ---
        if clean_line.startswith("//"):
            line_surf = code_font.render(line, True, COLOR_SYNTAX_COMMENT)
            text_container.blit(line_surf, (10, line_y))
        elif clean_line.startswith("#include"):
            line_surf = code_font.render(line, True, COLOR_SYNTAX_INCLUDE)
            text_container.blit(line_surf, (10, line_y))
        else:
            leading_spaces_count = len(line) - len(line.lstrip())
            space_surf = code_font.render(" " * leading_spaces_count, True, COLOR_CODE_TEXT)
            word_x = 10 + space_surf.get_width()
            current_word = ""
            for char in clean_line:
                if char.isalnum() or char == "_":
                    current_word += char
                else:
                    if current_word:
                        w_color = COLOR_SYNTAX_KEYWORD if current_word in CPP_KEYWORDS else (COLOR_SYNTAX_TYPE if current_word in CPP_TYPES else (COLOR_SYNTAX_FUNCTION if current_word in CPP_FUNCTIONS else (COLOR_SYNTAX_NUMBER if current_word.isdigit() else COLOR_CODE_TEXT)))
                        w_surf = code_font.render(current_word, True, w_color)
                        text_container.blit(w_surf, (word_x, line_y))
                        word_x += w_surf.get_width()
                        current_word = ""
                    char_surf = code_font.render(char, True, COLOR_CODE_TEXT)
                    text_container.blit(char_surf, (word_x, line_y))
                    word_x += char_surf.get_width()
            if current_word:
                w_color = COLOR_SYNTAX_KEYWORD if current_word in CPP_KEYWORDS else (COLOR_SYNTAX_TYPE if current_word in CPP_TYPES else (COLOR_SYNTAX_FUNCTION if current_word in CPP_FUNCTIONS else (COLOR_SYNTAX_NUMBER if current_word.isdigit() else COLOR_CODE_TEXT)))
                w_surf = code_font.render(current_word, True, w_color)
                text_container.blit(w_surf, (word_x, line_y))
                word_x += w_surf.get_width()

        line_y += 20 # Переходим к следующей строке

    # 2. ПРАВИЛЬНОЕ МАСКИРОВАНИЕ С УЧЕТОМ СКРОЛЛА:
    # Ограничиваем видимую область на экране по высоте (чтобы не залезала на терминал)
    visible_height = SCREEN_HEIGHT - 185  # Высота панели кода до верхнего края терминала

    # Прямоугольник area вырезает нужную зону ИЗ контейнера.
    # Координата Y у этого прямоугольника должна двигаться вслед за скроллом!
    # Так как code_panel_scroll_y у нас отрицательный, мы ставим минус перед ним, чтобы превратить в плюс.
    visible_rect = pygame.Rect(0, -code_panel_scroll_y, code_panel_width - 20, visible_height)

    # Блитим на ФИКСИРОВАННУЮ позицию экрана (15 пикселей от верха),
    # а Pygame сам вытащит из контейнера нужную прокрученную часть кода
    screen.blit(text_container, (code_panel_x + 10, 15), area=visible_rect)


    # =========================================================================
    # --- ОТРИСОВКА ГРАФИЧЕСКИХ МОДАЛЬНЫХ ОКНО (В самом конце перед flip) ---
    # =========================================================================
    if app_state in ("save_dialog", "open_dialog"):
        # 1. Создаем эффект затемнения холста (Overlay)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 24, 30, 180)) # Темный полупрозрачный цвет
        screen.blit(overlay, (0, 0))

        # Центрируем окна относительно разрешения экрана
        win_cx = SCREEN_WIDTH // 2
        win_cy = SCREEN_HEIGHT // 2

        if app_state == "save_dialog":
            # Рисуем корпус окна окна
            pygame.draw.rect(screen, (240, 242, 245), (win_cx - 200, win_cy - 100, 400, 200), border_radius=12)
            pygame.draw.rect(screen, (149, 165, 166), (win_cx - 200, win_cy - 100, 400, 200), width=2, border_radius=12)

            # Заголовок
            title_surf = font.render("Сохранение проекта", True, (44, 62, 80))
            screen.blit(title_surf, (win_cx - 180, win_cy - 80))

            # Поле ввода текста
            input_box = pygame.Rect(win_cx - 180, win_cy - 30, 360, 35)
            pygame.draw.rect(screen, (255, 255, 255), input_box, border_radius=6)
            pygame.draw.rect(screen, COLOR_INPUT_ACTIVE, input_box, width=2, border_radius=6)

            # Рендеринг вводимого текста
            text_surf = font.render(save_filename_text, True, (0, 0, 0))
            screen.blit(text_surf, (input_box.x + 10, input_box.y + 7))

            # Мигающий курсор в поле ввода
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                cursor_x = input_box.x + 10 + text_surf.get_width() + 2
                pygame.draw.line(screen, (0, 0, 0), (cursor_x, input_box.y + 6), (cursor_x, input_box.bottom - 6), width=2)

            # Кнопка ОК
            pygame.draw.rect(screen, (39, 174, 96), (win_cx - 110, win_cy + 30, 100, 35), border_radius=6)
            ok_text = font.render("ОК", True, (255, 255, 255))
            screen.blit(ok_text, (win_cx - 110 + (100 - ok_text.get_width())//2, win_cy + 38))

            # Кнопка ОТМЕНА
            pygame.draw.rect(screen, (192, 41, 43), (win_cx + 10, win_cy + 30, 100, 35), border_radius=6)
            cancel_text = font.render("Отмена", True, (255, 255, 255))
            screen.blit(cancel_text, (win_cx + 10 + (100 - cancel_text.get_width())//2, win_cy + 38))

        elif app_state == "open_dialog":
            # Рисуем корпус окна выбора файлов
            pygame.draw.rect(screen, (240, 242, 245), (win_cx - 200, win_cy - 150, 400, 300), border_radius=12)
            pygame.draw.rect(screen, (149, 165, 166), (win_cx - 200, win_cy - 150, 400, 300), width=2, border_radius=12)

            # Заголовок
            title_surf = font.render("Открыть проект (.json)", True, (44, 62, 80))
            screen.blit(title_surf, (win_cx - 180, win_cy - 130))

            # Область списка файлов (маскируем через Surface, чтобы длинный список не вылезал)
            list_rect = pygame.Rect(win_cx - 180, win_cy - 90, 360, 150)
            pygame.draw.rect(screen, (255, 255, 255), list_rect, border_radius=6)
            pygame.draw.rect(screen, (200, 205, 210), list_rect, width=1, border_radius=6)

            file_container = pygame.Surface((list_rect.width, list_rect.height), pygame.SRCALPHA)

            # Отрисовываем доступные файлы внутри контейнера
            file_y = open_menu_scroll_y
            for idx, filename in enumerate(project_files_list):
                item_rect = pygame.Rect(0, file_y, list_rect.width, 25)

                # Подсвечиваем выбранный файл синим цветом
                if idx == selected_file_idx:
                    pygame.draw.rect(file_container, (52, 152, 219), item_rect)
                    text_color = (255, 255, 255)
                else:
                    text_color = (0, 0, 0)
                    if idx % 2 == 0: # Зебра-эффект для строк
                        pygame.draw.rect(file_container, (245, 247, 250), item_rect)

                file_surf = font.render(filename, True, text_color)
                file_container.blit(file_surf, (10, file_y + 3))
                file_y += 25

            screen.blit(file_container, (list_rect.x, list_rect.y))

            # Кнопка ЗАГРУЗИТЬ
            load_btn_color = (39, 174, 96) if selected_file_idx != -1 else (180, 185, 190)
            pygame.draw.rect(screen, load_btn_color, (win_cx - 160, win_cy + 80, 120, 35), border_radius=6)
            load_text = font.render("Загрузить", True, (255, 255, 255))
            screen.blit(load_text, (win_cx - 160 + (120 - load_text.get_width())//2, win_cy + 88))

            # Кнопка ОТМЕНА
            pygame.draw.rect(screen, (192, 41, 43), (win_cx + 40, win_cy + 80, 120, 35), border_radius=6)
            cancel_text = font.render("Отмена", True, (255, 255, 255))
            screen.blit(cancel_text, (win_cx + 40 + (120 - cancel_text.get_width())//2, win_cy + 88))


    pygame.display.flip()
    clock.tick(60)

# --- ЗА ПРЕДЕЛАМИ ЦИКЛА WHILE ---
serial_stop_flag.set()
if serial_obj and serial_obj.is_open:
    serial_obj.close()

pygame.quit()
sys.exit()
