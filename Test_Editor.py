import os
import sys
import time
import subprocess
import serial.tools.list_ports
import pygame

# Инициализация Pygame
pygame.init()
pygame.font.init()

# Константы интерфейса
WIDTH, HEIGHT = 750, 500
FPS = 60
FONT_MAIN = pygame.font.SysFont("Arial", 14)
FONT_BOLD = pygame.font.SysFont("Arial", 14, bold=True)
FONT_TITLE = pygame.font.SysFont("Arial", 18, bold=True)
FONT_CODE = pygame.font.SysFont("Courier New", 14)  # Моноширинный для кода

# Цвета
COLOR_BG = (135, 206, 235)       # Скайблю
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (200, 200, 200)
COLOR_DARK_GRAY = (100, 100, 100)
COLOR_BTN = (240, 240, 240)
COLOR_BTN_HOVER = (220, 220, 220)
COLOR_ORANGE = (255, 140, 0)
COLOR_RED = (220, 20, 60)

# Цвета подсветки синтаксиса Python
COLOR_SYN_KEYWORD = (0, 0, 255)      # Синий
COLOR_SYN_NUMBER = (128, 0, 128)     # Фиолетовый
COLOR_SYN_BUILTIN = (0, 128, 128)    # Бирюзовый
COLOR_SYN_TEXT = (0, 0, 0)           # Черный

# Глобальные переменные состояния
current_screen = "main" # "main" или "editor"
current_port = "Нет портов"
ports_list = []
dropdown_open = False
device_files = []
selected_device_file = None
scroll_offset = 0

# Переменные кастомного всплывающего окна (модального диалога)
modal_open = False
modal_title = ""
modal_items = []
modal_purpose = "" # "upload", "run", "flash", "open_file"
modal_scroll = 0

# Состояние редактора кода
code_lines = [""]            # Список строк в редакторе
cursor_row = 0              # Индекс текущей строки
cursor_col = 0              # Позиция курсора в строке
editor_scroll = 0           # Прокрутка по вертикали (уже есть)
editor_scroll_x = 0         # Прокрутка по горизонтали (уже есть)
dragging_v_bar = False      # Зажат ли вертикальный ползунок
dragging_h_bar = False      # Зажат ли горизонтальный ползунок



screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("KLIK EDITOR MICROPYTHON (Pure Pygame)")
clock = pygame.time.Clock()

# Ключевые слова для подсветки синтаксиса
PYTHON_KEYWORDS = {"import", "from", "def", "return", "if", "elif", "else", "while", "for", "in", "is", "not", "and", "or", "try", "except", "class", "pass", "break", "continue"}
PYTHON_BUILTINS = {"print", "len", "range", "str", "int", "float", "list", "dict", "set", "type"}

# Переменные для окна сохранения файла
save_dialog_open = False
save_filename_text = "untitled.py"
save_cursor_col = len(save_filename_text)  # ДОБАВЛЕНО: позиция курсора в имени файла


class Button:
    def __init__(self, x, y, w, h, text, callback, color=COLOR_BTN, text_color=COLOR_BLACK):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.color = color
        self.text_color = text_color
        self.visible = True

    def draw(self, surf, mouse_pos):
        if not self.visible: return
        color = COLOR_BTN_HOVER if (self.rect.collidepoint(mouse_pos) and self.color == COLOR_BTN) else self.color
        pygame.draw.rect(surf, color, self.rect, border_radius=4)
        pygame.draw.rect(surf, COLOR_DARK_GRAY, self.rect, width=1, border_radius=4)
        txt_surf = FONT_MAIN.render(self.text, True, self.text_color)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surf.blit(txt_surf, txt_rect)

    def handle_event(self, event, mouse_pos):
        if not self.visible: return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mouse_pos):
                self.callback()
                return True
        return False

# --- Взаимодействие с процессами ---
def get_com_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def run_universal_cmd(cmd_list):
    try:
        process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None: break
            if output: print(output.strip())
        return process.poll() == 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def refresh_ports():
    global current_port, ports_list
    ports_list = get_com_ports()
    current_port = ports_list[0] if ports_list else "Нет портов"

def list_device_files():
    global current_port, device_files, selected_device_file, scroll_offset
    if current_port == "Нет портов": return
    selected_device_file = None
    btn_download.visible = btn_delete.visible = False
    try:
        output = subprocess.check_output(["ampy", "--port", current_port, "ls"], stderr=subprocess.STDOUT, text=True)
        device_files = [line.strip() for line in output.split('\n') if line.strip()]
        scroll_offset = 0
    except Exception as e:
        print(f"Ошибка чтения ls: {e}")
        device_files = ["Ошибка чтения"]

##def start_upload():
##    open_modal("Выберите файл .py для загрузки", [f for f in os.listdir('.') if f.endswith('.py')], "upload")
##
##def start_run():
##    open_modal("Выберите файл .py для запуска", [f for f in os.listdir('.') if f.endswith('.py')], "run")

##def start_flash():
##    global current_port
##    if current_port == "Нет портов": return
##    print("Очистка Flash памяти...")
##    if run_universal_cmd([sys.executable, "-m", "esptool", "--port", current_port, "erase_flash"]):
##        open_modal("Выберите файл прошивки .bin", [f for f in os.listdir('.') if f.endswith('.bin')], "flash")

def start_upload():
    # 1. Формируем абсолютный путь к папке downloads
##    script_dir = os.path.dirname(os.path.abspath(__file__))
    # --- УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ ДЛЯ СБОРКИ ---
    if getattr(sys, 'frozen', False):
        # Если запущен скомпилированный EXE, берем путь к этому EXE
        script_dir = os.path.dirname(sys.executable)
    else:
        # Если запускаем обычный .py скрипт во время разработки
        script_dir = os.path.dirname(os.path.abspath(__file__))

    # Папка downloads теперь всегда будет жестко привязана к месту, где лежит сам EXE
    downloads_dir = os.path.abspath(os.path.join(script_dir, "downloads"))
    os.makedirs(downloads_dir, exist_ok=True) # Создаем, если её нет

    # 2. Передаем в модальное окно файлы из этой папки
    files = [f for f in os.listdir(downloads_dir) if f.endswith('.py')]
    open_modal("Выберите файл .py из downloads для загрузки", files, "upload")

def start_run():
    # 1. Формируем абсолютный путь к папке downloads
##    script_dir = os.path.dirname(os.path.abspath(__file__))
    # --- УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ ДЛЯ СБОРКИ ---
    if getattr(sys, 'frozen', False):
        # Если запущен скомпилированный EXE, берем путь к этому EXE
        script_dir = os.path.dirname(sys.executable)
    else:
        # Если запускаем обычный .py скрипт во время разработки
        script_dir = os.path.dirname(os.path.abspath(__file__))

    # Папка downloads теперь всегда будет жестко привязана к месту, где лежит сам EXE
    downloads_dir = os.path.abspath(os.path.join(script_dir, "downloads"))
    os.makedirs(downloads_dir, exist_ok=True) # Создаем, если её нет

    # 2. Передаем в модальное окно файлы из этой папки
    files = [f for f in os.listdir(downloads_dir) if f.endswith('.py')]
    open_modal("Выберите файл .py из downloads для запуска", files, "run")


def start_flash():
    global current_port
    if current_port == "Нет портов":
        print("Ошибка: Порт не выбран!")
        return
    # СРАЗУ открываем кустарное окно выбора локальных файлов прошивки в папке скрипта
    open_modal("Выберите файл прошивки .bin", [f for f in os.listdir('.') if f.endswith('.bin')], "flash")

def handle_modal_selection(item):
    global current_port, modal_purpose, code_lines, cursor_row, cursor_col
    if item.startswith("("):
        close_modal()
        return

    # Путь к папке downloads для ampy
    #script_dir = os.path.dirname(os.path.abspath(__file__))
    # --- УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ ДЛЯ СБОРКИ ---
    if getattr(sys, 'frozen', False):
        # Если запущен скомпилированный EXE, берем путь к этому EXE
        script_dir = os.path.dirname(sys.executable)
    else:
        # Если запускаем обычный .py скрипт во время разработки
        script_dir = os.path.dirname(os.path.abspath(__file__))


    downloads_dir = os.path.abspath(os.path.join(script_dir, "downloads"))
    full_item_path = os.path.join(downloads_dir, item)

    if modal_purpose == "upload":
        # Используем полный путь к файлу в downloads
        if run_universal_cmd(["ampy", "--port", current_port, "put", full_item_path]):
            list_device_files()

    elif modal_purpose == "run":
        # Используем полный путь к файлу в downloads
        run_universal_cmd(["ampy", "--port", current_port, "run", full_item_path])

    elif modal_purpose == "flash":
        run_universal_cmd([sys.executable, "-m", "esptool", "--port", current_port, "--baud", "460800", "write_flash", "0x1000", item])

    elif modal_purpose == "open_file":
        try:
            with open(item, "r", encoding="utf-8") as f: content = f.read()
            code_lines = content.splitlines() if content.splitlines() else [""]
            cursor_row = cursor_col = 0
        except Exception as e: print(f"Ошибка открытия: {e}")
    close_modal()


##def handle_modal_selection(item):
##    global current_port, modal_purpose, code_lines, cursor_row, cursor_col
##    if item.startswith("("):
##        close_modal()
##        return
##
##    if modal_purpose == "upload":
##        if run_universal_cmd(["ampy", "--port", current_port, "put", item]):
##            list_device_files()
##    elif modal_purpose == "run":
##        run_universal_cmd(["ampy", "--port", current_port, "run", item])
##
##    elif modal_purpose == "flash":
##        # Сначала очищаем память локально
##        print(f"--- Очистка Flash памяти на порту {current_port} ---")
##        erase_ok = run_universal_cmd([sys.executable, "-m", "esptool", "--port", current_port, "erase_flash"])
##
##        # Если очистка прошла успешно, шьем выбранный локальный .bin файл строго по адресу 0x1000
##        if erase_ok:
##            print(f"--- Запись прошивки {item} ---")
##            run_universal_cmd([
##                sys.executable, "-m", "esptool",
##                "--port", current_port,
##                "write_flash",
##                "--flash_size=detect",
##                "0x1000", item  # Исправлено: 0x1000 вместо 0 для ESP32
##            ])
##        else:
##            print("Ошибка: Не удалось очистить флэш-память. Прошивка отменена.")
##
##
##    elif modal_purpose == "open_file":
##        try:
##            with open(item, "r", encoding="utf-8") as f:
##                code_lines = [line.replace('\r', '').replace('\n', '') for line in f.readlines()]
##            if not code_lines: code_lines = [""]
##            cursor_row, cursor_col = 0, 0
##        except Exception as e:
##            print(f"Ошибка чтения локального файла: {e}")
##
##    close_modal()


##def download_file():
##    global current_port, selected_device_file
##    if not selected_device_file or current_port == "Нет портов": return
##    os.makedirs("downloads", exist_ok=True)
##    out_path = os.path.normpath(os.path.join("downloads", selected_device_file))
##    try:
##        output = subprocess.check_output(["ampy", "--port", current_port, "get", selected_device_file])
##        with open(out_path, "wb") as f: f.write(output)
##        print(f"Успешно сохранено: {out_path}")
##    except Exception as e: print(f"Ошибка скачивания: {e}")

def download_file():
    global current_port, selected_device_file
    if not selected_device_file or current_port == "Нет портов": return

    try:
        # 1. Берем папку, где лежит сам запускаемый скрипт
        #script_dir = os.path.dirname(os.path.abspath(__file__))
        # --- УМНОЕ ОПРЕДЕЛЕНИЕ ПУТИ ДЛЯ СБОРКИ ---
        if getattr(sys, 'frozen', False):
            # Если запущен скомпилированный EXE, берем путь к этому EXE
            script_dir = os.path.dirname(sys.executable)
        else:
            # Если запускаем обычный .py скрипт во время разработки
            script_dir = os.path.dirname(os.path.abspath(__file__))

        # 2. Создаем полный абсолютный путь к папке downloads
        downloads_dir = os.path.abspath(os.path.join(script_dir, "downloads"))
        os.makedirs(downloads_dir, exist_ok=True)

        # ОЧИСТКА: Убираем ведущие слэши из имени файла, чтобы os.path.join не сбрасывал путь к корню диска
        clean_filename = selected_device_file.lstrip('/\\')

        # 3. Полный абсолютный путь к итоговому файлу
        out_path = os.path.abspath(os.path.join(downloads_dir, clean_filename))

        # Вызываем ampy и забираем чистые байты
        cmd = ["ampy", "--port", current_port, "get", selected_device_file]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)

        # Записываем байты строго по абсолютному адресу
        with open(out_path, "wb") as f:
            f.write(output)

        print(f"Успешно сохранено: {out_path}")
    except Exception as e:
        print(f"Ошибка скачивания: {e}")





def delete_file():
    global current_port, selected_device_file
    if not selected_device_file or current_port == "Нет портов": return
    if run_universal_cmd(["ampy", "--port", current_port, "rm", selected_device_file]): list_device_files()

# --- Логика Редактора Кода ---
def switch_to_editor():
    global current_screen
    current_screen = "editor"
    pygame.key.start_text_input()

def switch_to_main():
    global current_screen
    current_screen = "main"
    pygame.key.stop_text_input()

def open_local_file_dialog():
    open_modal("Открыть файл Python в редактор", [f for f in os.listdir('.') if f.endswith('.py')], "open_file")

# ИСПРАВЛЕННАЯ ФУНКЦИЯ — СТАВИТЬ СЮДА:
def start_save_dialog():
    global save_dialog_open, save_cursor_col
    save_dialog_open = True
    save_cursor_col = len(save_filename_text)  # Выставляем курсор в конец строки

# ... Дальше идет функция draw_highlighted_code ...


def draw_highlighted_code(surf, text, x, y):
    words = []
    current_word = ""
    for char in text:
        if char.isalnum() or char == '_': current_word += char
        else:
            if current_word:
                words.append((current_word, True))
                current_word = ""
            words.append((char, False))
    if current_word: words.append((current_word, True))

    current_x = x
    for token, is_word in words:
        color = COLOR_SYN_TEXT
        if is_word:
            if token in PYTHON_KEYWORDS: color = COLOR_SYN_KEYWORD
            elif token in PYTHON_BUILTINS: color = COLOR_SYN_BUILTIN
            elif token.isdigit(): color = COLOR_SYN_NUMBER
        t_surf = FONT_CODE.render(token, True, color)
        surf.blit(t_surf, (current_x, y))
        current_x += t_surf.get_width()

def open_modal(title, items, purpose):
    global modal_open, modal_title, modal_items, modal_purpose, modal_scroll
    modal_open = True
    modal_title = title
    modal_items = items if items else ["(Нет подходящих файлов в папке скрипта)"]
    modal_purpose = purpose
    modal_scroll = 0

def close_modal():
    global modal_open
    modal_open = False

def handle_modal_selection(item):
    global current_port, modal_purpose, code_lines, cursor_row, cursor_col
    if item.startswith("("):
        close_modal()
        return
    if modal_purpose == "upload":
        if run_universal_cmd(["ampy", "--port", current_port, "put", item]): list_device_files()
    elif modal_purpose == "run":
        run_universal_cmd(["ampy", "--port", current_port, "run", item])
    elif modal_purpose == "flash":
        run_universal_cmd([sys.executable, "-m", "esptool", "--port", current_port, "--baud", "460800", "write_flash", "0x1000", item])
    elif modal_purpose == "open_file":
        try:
            with open(item, "r", encoding="utf-8") as f: content = f.read()
            code_lines = content.splitlines() if content.splitlines() else [""]
            cursor_row = cursor_col = 0
        except Exception as e: print(f"Ошибка открытия: {e}")
    close_modal()

# Инициализация Кнопок экрана Меню
btn_ref = Button(180, 55, 100, 30, "Обновить", refresh_ports)
btn_ls = Button(240, 150, 180, 35, "Получить список", list_device_files)
btn_up = Button(440, 150, 220, 35, "Загрузить в ESP (.py)", start_upload)
btn_rn = Button(440, 200, 220, 35, "Запустить (.py)", start_run)
btn_fl = Button(440, 250, 220, 35, "ПРОШИВКА (.bin)", start_flash, color=COLOR_ORANGE)
btn_download = Button(240, 250, 180, 35, "Скачать в /downloads", download_file)
btn_delete = Button(240, 300, 180, 35, "Удалить файл", delete_file, color=COLOR_RED, text_color=COLOR_WHITE)
btn_go_editor = Button(440, 350, 220, 45, "ОТКРЫТЬ РЕДАКТОР КОДА", switch_to_editor, color=(60, 179, 113), text_color=COLOR_WHITE)
btn_download.visible = btn_delete.visible = False
buttons_main = [btn_ref, btn_ls, btn_up, btn_rn, btn_fl, btn_download, btn_delete, btn_go_editor]

# Инициализация Кнопок экрана Редактора
btn_ed_open = Button(15, 15, 120, 30, "Открыть файл", open_local_file_dialog)
btn_ed_save = Button(145, 15, 120, 30, "Сохранить как", start_save_dialog)
btn_ed_back = Button(615, 15, 120, 30, "Назад в меню", switch_to_main, color=COLOR_RED, text_color=COLOR_WHITE)
buttons_editor = [btn_ed_open, btn_ed_save, btn_ed_back]

refresh_ports()

# --- Главный цикл программы ---
running = True
while running:
    mouse_p = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 1. ОБРАБОТКА ДИАЛОГА СОХРАНЕНИЯ ФАЙЛА
        if save_dialog_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Клик по кнопке сохранения
                if pygame.Rect(450, 250, 90, 30).collidepoint(mouse_p):
                    if save_filename_text.strip():
                        try:
                            with open(save_filename_text, "w", encoding="utf-8") as f:
                                f.write("\n".join(code_lines))
                            print(f"Сохранено: {save_filename_text}")
                        except Exception as e: print(f"Ошибка сохранения: {e}")
                    save_dialog_open = False
                # Клик по кнопке отмены
                elif pygame.Rect(350, 250, 90, 30).collidepoint(mouse_p):
                    save_dialog_open = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    if save_cursor_col > 0:
                        save_filename_text = save_filename_text[:save_cursor_col-1] + save_filename_text[save_cursor_col:]
                        save_cursor_col -= 1
                elif event.key == pygame.K_DELETE:
                    if save_cursor_col < len(save_filename_text):
                        save_filename_text = save_filename_text[:save_cursor_col] + save_filename_text[save_cursor_col+1:]
                elif event.key == pygame.K_LEFT:
                    if save_cursor_col > 0: save_cursor_col -= 1
                elif event.key == pygame.K_RIGHT:
                    if save_cursor_col < len(save_filename_text): save_cursor_col += 1
                elif event.key == pygame.K_RETURN:
                    if save_filename_text.strip():
                        try:
                            with open(save_filename_text, "w", encoding="utf-8") as f:
                                f.write("\n".join(code_lines))
                        except Exception as e: print(f"Ошибка: {e}")
                    save_dialog_open = False

            elif event.type == pygame.TEXTINPUT:
                # Вставка текста строго в позицию курсора, а не в конец строки
                save_filename_text = save_filename_text[:save_cursor_col] + event.text + save_filename_text[save_cursor_col:]
                save_cursor_col += len(event.text)
            continue


        # 2. ОБРАБОТКА МОДАЛЬНЫХ ОКНО ВЫБОРА ФАЙЛОВ
        if modal_open:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if not pygame.Rect(150, 100, 450, 300).collidepoint(mouse_p): close_modal()
                    else:
                        for i, item in enumerate(modal_items):
                            item_y = 150 + i * 25 - modal_scroll
                            if 145 < item_y < 370 and pygame.Rect(170, item_y, 410, 22).collidepoint(mouse_p):
                                handle_modal_selection(item)
                                break
                elif event.button == 4: modal_scroll = max(0, modal_scroll - 20)
                elif event.button == 5: modal_scroll = min(max(0, len(modal_items)*25 - 220), modal_scroll + 20)
            continue

        # 3. ЛОГИКА СОБЫТИЙ ЭКРАНА РЕДАКТОРА
        if current_screen == "editor":
            for btn in buttons_editor: btn.handle_event(event, mouse_p)
            if event.type == pygame.TEXTINPUT:
                line = code_lines[cursor_row]
                code_lines[cursor_row] = line[:cursor_col] + event.text + line[cursor_col:]
                cursor_col += len(event.text)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    if cursor_col > 0:
                        line = code_lines[cursor_row]
                        code_lines[cursor_row] = line[:cursor_col-1] + line[cursor_col:]
                        cursor_col -= 1
                    elif cursor_row > 0:
                        cursor_col = len(code_lines[cursor_row-1])
                        code_lines[cursor_row-1] += code_lines[cursor_row]
                        code_lines.pop(cursor_row)
                        cursor_row -= 1
                # --- ДОБАВЛЕНО: ОБРАБОТКА КЛАВИШИ DELETE ---
                elif event.key == pygame.K_DELETE:
                    line = code_lines[cursor_row]
                    # Если курсор не в самом конце строки, удаляем символ справа
                    if cursor_col < len(line):
                        code_lines[cursor_row] = line[:cursor_col] + line[cursor_col+1:]
                    # Если курсор в конце строки и ниже есть еще строки, подтягиваем нижнюю строку вверх
                    elif cursor_row < len(code_lines) - 1:
                        code_lines[cursor_row] += code_lines[cursor_row+1]
                        code_lines.pop(cursor_row+1)

                elif event.key == pygame.K_RETURN:
                    line = code_lines[cursor_row]
                    code_lines.insert(cursor_row + 1, line[cursor_col:])
                    code_lines[cursor_row] = line[:cursor_col]
                    cursor_row += 1
                    cursor_col = 0
                elif event.key == pygame.K_UP and cursor_row > 0:
                    cursor_row -= 1
                    cursor_col = min(cursor_col, len(code_lines[cursor_row]))
                elif event.key == pygame.K_DOWN and cursor_row < len(code_lines) - 1:
                    cursor_row += 1
                    cursor_col = min(cursor_col, len(code_lines[cursor_row]))
                elif event.key == pygame.K_LEFT:
                    if cursor_col > 0: cursor_col -= 1
                    elif cursor_row > 0:
                        cursor_row -= 1
                        cursor_col = len(code_lines[cursor_row])
                elif event.key == pygame.K_RIGHT:
                    if cursor_col < len(code_lines[cursor_row]): cursor_col += 1
                    elif cursor_row < len(code_lines) - 1:
                        cursor_row += 1
                        cursor_col = 0
                # --- ДОБАВЛЕНО: Обработка клавиши Tab (вставка 4 пробелов) ---
                elif event.key == pygame.K_TAB:
                    line = code_lines[cursor_row]
                    code_lines[cursor_row] = line[:cursor_col] + "    " + line[cursor_col:]
                    cursor_col += 4

                # --- ОБНОВЛЕНО: Клавиша Enter с автоотступом после ":" ---
                elif event.key == pygame.K_RETURN:
                    line = code_lines[cursor_row]

                    # Считаем текущий отступ (количество пробелов в начале строки)
                    leading_spaces = len(line) - len(line.lstrip(' '))
                    indent = " " * leading_spaces

                    # Если строка заканчивается на двоеточие, добавляем еще 4 пробела
                    if line[:cursor_col].rstrip().endswith(':'):
                        indent += "    "

                    code_lines.insert(cursor_row + 1, indent + line[cursor_col:])
                    code_lines[cursor_row] = line[:cursor_col]
                    cursor_row += 1
                    cursor_col = len(indent)

##            elif event.type == pygame.MOUSEBUTTONDOWN:
##                if event.button == 4: editor_scroll = max(0, editor_scroll - 20)
##                elif event.button == 5: editor_scroll = min(max(0, len(code_lines)*20 - 380), editor_scroll + 20)
##            continue
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Размеры рабочей области редактора
                    ed_x, ed_y, ed_w, ed_h = 15, 75, WIDTH - 30, HEIGHT - 90

                    # Координаты ползунков (рассчитываются так же, как в отрисовке)
                    v_track_rect = pygame.Rect(ed_x + ed_w - 15, ed_y, 15, ed_h - 15)
                    h_track_rect = pygame.Rect(ed_x + 40, ed_y + ed_h - 15, ed_w - 55, 15)

                    # Проверяем клик по вертикальному скроллбару
                    if v_track_rect.collidepoint(mouse_p):
                        dragging_v_bar = True
                    # Проверяем клик по горизонтальному скроллбару
                    elif h_track_rect.collidepoint(mouse_p):
                        dragging_h_bar = True
                    # Обычный клик по тексту для перемещения курсора
                    elif pygame.Rect(56, 75, ed_w - 71, ed_h - 15).collidepoint(mouse_p):
                        relative_y = mouse_p[1] - 85 + editor_scroll
                        clicked_row = relative_y // 20
                        if clicked_row < 0: clicked_row = 0
                        elif clicked_row >= len(code_lines): clicked_row = len(code_lines) - 1
                        cursor_row = clicked_row

                        char_width = FONT_CODE.size(" ")[0]
                        relative_x = mouse_p[0] - 65 + editor_scroll_x
                        if relative_x <= 0: cursor_col = 0
                        else:
                            clicked_col = round(relative_x / char_width)
                            cursor_col = min(clicked_col, len(code_lines[cursor_row]))

                # Обычный скроллинг колесиком (только вертикальный, без Shift)
                elif event.button == 4: editor_scroll = max(0, editor_scroll - 20)
                elif event.button == 5: editor_scroll = min(max(0, len(code_lines)*20 - 350), editor_scroll + 20)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging_v_bar = False
                    dragging_h_bar = False




        # 4. ЛОГИКА СОБЫТИЙ ИСХОДНОГО ГЛАВНОГО ЭКРАНА
        for btn in buttons_main: btn.handle_event(event, mouse_p)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(20, 55, 150, 30).collidepoint(mouse_p): dropdown_open = not dropdown_open
            elif dropdown_open:
                for i, p in enumerate(ports_list):
                    if pygame.Rect(20, 85 + i * 30, 150, 30).collidepoint(mouse_p):
                        current_port = p
                        break
                dropdown_open = False
            if pygame.Rect(20, 150, 200, 300).collidepoint(mouse_p):
                for i, file in enumerate(device_files):
                    file_y = 155 + i * 25 - scroll_offset
                    if 150 < file_y < 440 and pygame.Rect(25, file_y, 190, 22).collidepoint(mouse_p) and file != "Ошибка чтения":
                        selected_device_file = file
                        btn_download.visible = btn_delete.visible = True
                        break
        if event.type == pygame.MOUSEBUTTONDOWN and not dropdown_open:
            if pygame.Rect(20, 150, 200, 300).collidepoint(mouse_p):
                if event.button == 4: scroll_offset = max(0, scroll_offset - 20)
                elif event.button == 5: scroll_offset = min(max(0, len(device_files) * 25 - 280), scroll_offset + 20)

    # Логика перетаскивания скроллбаров (выполняется каждый кадр, если кнопка зажата)
    if current_screen == "editor":
        ed_x, ed_y, ed_w, ed_h = 15, 75, WIDTH - 30, HEIGHT - 90

        if dragging_v_bar:
            # Вычисляем положение мыши относительно высоты трека
            track_h = ed_h - 15
            relative_y = mouse_p[1] - ed_y
            percentage = max(0.0, min(1.0, relative_y / track_h))
            # Максимальный скролл вниз
            max_scroll_y = max(0, len(code_lines) * 20 - (ed_h - 20))
            editor_scroll = int(percentage * max_scroll_y)

        if dragging_h_bar:
            # Вычисляем положение мыши относительно ширины трека
            track_w = ed_w - 55
            relative_x = mouse_p[0] - (ed_x + 40)

            # Находим процентное положение мыши на дорожке
            percentage = max(0.0, min(1.0, relative_x / track_w))

            # Рассчитываем реальный сдвиг текста
            editor_scroll_x = int(percentage * max_scroll_x)



    # --- ОТРИСОВКА ЭКРАНОВ ---
    screen.fill(COLOR_BG)

    if current_screen == "main":
        screen.blit(FONT_TITLE.render("Подключиться к КЛИК", True, COLOR_BLACK), (20, 25))
        screen.blit(FONT_BOLD.render(f"Выбран: {current_port}", True, COLOR_BLACK), (20, 100))
        pygame.draw.rect(screen, COLOR_WHITE, (20, 150, 200, 300))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (20, 150, 200, 300), width=1)

        for i, file in enumerate(device_files):
            file_y = 155 + i * 25 - scroll_offset
            if 150 < file_y < 440:
                if file == selected_device_file: pygame.draw.rect(screen, COLOR_GRAY, (22, file_y, 196, 22))
                screen.blit(FONT_MAIN.render(file, True, COLOR_BLACK), (25, file_y + 2))

        for btn in buttons_main: btn.draw(screen, mouse_p)
        pygame.draw.rect(screen, COLOR_WHITE, (20, 55, 150, 30))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (20, 55, 150, 30), width=1)
        screen.blit(FONT_MAIN.render(current_port, True, COLOR_BLACK), (25, 62))

        if dropdown_open:
            for i, p in enumerate(ports_list):
                item_r = pygame.Rect(20, 85 + i * 30, 150, 30)
                pygame.draw.rect(screen, COLOR_WHITE, item_r)
                pygame.draw.rect(screen, COLOR_GRAY, item_r, width=1)
                screen.blit(FONT_MAIN.render(p, True, COLOR_BLACK), (25, 92 + i * 30))

    elif current_screen == "editor":
        pygame.draw.rect(screen, COLOR_WHITE, (0, 0, WIDTH, 60))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (0, 0, WIDTH, 60), width=1)
        for btn in buttons_editor: btn.draw(screen, mouse_p)

        pygame.draw.rect(screen, COLOR_WHITE, (15, 75, WIDTH - 30, HEIGHT - 90))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (15, 75, WIDTH - 30, HEIGHT - 90), width=1)

        # Обрезаем текст так, чтобы он не залезал на область скроллбаров
        screen.set_clip(pygame.Rect(16, 76, WIDTH - 47, HEIGHT - 107))


        # Задний фон для панели номеров строк (серая полоса слева)
        pygame.draw.rect(screen, (245, 245, 245), (16, 76, 40, HEIGHT - 92))
        pygame.draw.line(screen, COLOR_GRAY, (56, 76), (56, HEIGHT - 16), 1)

        for i, line in enumerate(code_lines):
            line_y = 85 + i * 20 - editor_scroll
            if 60 < line_y < HEIGHT - 20:
                # --- ДОБАВЛЕНО: Отрисовка номера строки ---
                num_surf = FONT_CODE.render(str(i + 1), True, COLOR_DARK_GRAY)
                # Выравнивание номеров по правому краю серой полосы
                screen.blit(num_surf, (50 - num_surf.get_width(), line_y))

##                # --- ОБНОВЛЕНО: Отрисовка кода (сдвинута на X=65, чтобы не налезать на номера) ---
##                draw_highlighted_code(screen, line, 65, line_y)
##
##                if i == cursor_row and (int(time.time() * 2) % 2 == 0):
##                    cursor_x = 65 + FONT_CODE.size(line[:cursor_col])[0]
##                    pygame.draw.line(screen, COLOR_BLACK, (cursor_x, line_y), (cursor_x, line_y + 16), 2)

                # --- ИСПРАВЛЕНО: Добавляем вычитание editor_scroll_x ---
                draw_highlighted_code(screen, line, 65 - editor_scroll_x, line_y)

                # --- ИСПРАВЛЕНО: Учитываем сдвиг и для отрисовки мигающего курсора ---
                if i == cursor_row and (int(time.time() * 2) % 2 == 0):
                    cursor_x = 65 - editor_scroll_x + FONT_CODE.size(line[:cursor_col])[0]
                    # Рисуем курсор только если он не заехал под серую панель номеров строк (X > 56)
                    if cursor_x > 56:
                        pygame.draw.line(screen, COLOR_BLACK, (cursor_x, line_y), (cursor_x, line_y + 16), 2)


        screen.set_clip(None)
        # Размеры рабочей области для скроллбаров

        ed_x, ed_y, ed_w, ed_h = 15, 75, WIDTH - 30, HEIGHT - 90
        # 1. ВЕРТИКАЛЬНЫЙ СКРОЛЛБАР (справа)
        v_track = pygame.Rect(ed_x + ed_w - 15, ed_y, 15, ed_h - 15)
        pygame.draw.rect(screen, (230, 230, 230), v_track) # Дорожка
        pygame.draw.rect(screen, COLOR_GRAY, v_track, width=1)

        max_scroll_y = max(1, len(code_lines) * 20 - (ed_h - 20))
        v_bar_h = max(20, int((ed_h - 15) * (ed_h - 15) / max(ed_h - 15, len(code_lines) * 20)))
        v_bar_y = ed_y + int((editor_scroll / max_scroll_y) * (ed_h - 15 - v_bar_h))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (v_track.x + 2, v_bar_y, 11, v_bar_h), border_radius=3)

        # 2. ГОРИЗОНТАЛЬНЫЙ СКРОЛЛБАР (снизу, начинается после серой панели номеров)
        h_track = pygame.Rect(ed_x + 40, ed_y + ed_h - 15, ed_w - 55, 15)
        pygame.draw.rect(screen, (230, 230, 230), h_track) # Дорожка
        pygame.draw.rect(screen, COLOR_GRAY, h_track, width=1)

        max_scroll_x = 1000
        h_bar_w = max(20, int((ed_w - 55) * (ed_w - 55) / (ed_w - 55 + max_scroll_x)))
        h_bar_x = (ed_x + 40) + int((editor_scroll_x / max_scroll_x) * (ed_w - 55 - h_bar_w))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (h_bar_x, h_track.y + 2, h_bar_w, 11), border_radius=3)

        # Уголок на стыке двух скроллбаров
        pygame.draw.rect(screen, (240, 240, 240), (ed_x + ed_w - 15, ed_y + ed_h - 15, 15, 15))

    # 5. ОТРИСОВКА ВСПЛЫВАЮЩИХ ДИЛОГОВЫХ ОКОН (ПОВЕРХ ВСЕГО)
    if modal_open:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))
        modal_rect = pygame.Rect(150, 100, 450, 300)
        pygame.draw.rect(screen, COLOR_BTN, modal_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_BLACK, modal_rect, width=2, border_radius=8)
        screen.blit(FONT_BOLD.render(modal_title, True, COLOR_BLACK), (170, 115))
        pygame.draw.rect(screen, COLOR_WHITE, (165, 145, 420, 235))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (165, 145, 420, 235), width=1)
        for i, item in enumerate(modal_items):
            item_y = 150 + i * 25 - modal_scroll
            if 145 < item_y < 370:
                if pygame.Rect(170, item_y, 410, 22).collidepoint(mouse_p):
                    pygame.draw.rect(screen, COLOR_BTN_HOVER, (170, item_y, 410, 22))
                screen.blit(FONT_MAIN.render(item, True, COLOR_BLACK), (175, item_y + 2))

    if save_dialog_open:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        dialog_r = pygame.Rect(200, 180, 350, 130)
        pygame.draw.rect(screen, COLOR_BTN, dialog_r, border_radius=6)
        pygame.draw.rect(screen, COLOR_BLACK, dialog_r, width=2, border_radius=6)
        screen.blit(FONT_BOLD.render("Введите имя файла:", True, COLOR_BLACK), (220, 195))

        # Белое поле ввода
        pygame.draw.rect(screen, COLOR_WHITE, (220, 215, 310, 26))
        pygame.draw.rect(screen, COLOR_DARK_GRAY, (220, 215, 310, 26), width=1)

        # Отрисовка названия файла
        screen.blit(FONT_MAIN.render(save_filename_text, True, COLOR_BLACK), (225, 220))

        # --- ДОБАВЛЕНО: Мигающий курсор в поле ввода имени файла ---
        if int(time.time() * 2) % 2 == 0:
            text_before_save_cursor = save_filename_text[:save_cursor_col]
            # Используем FONT_MAIN, так как имя файла пишется им
            save_cursor_x = 225 + FONT_MAIN.size(text_before_save_cursor)[0]
            pygame.draw.line(screen, COLOR_BLACK, (save_cursor_x, 220), (save_cursor_x, 236), 2)

        pygame.draw.rect(screen, COLOR_GRAY, (350, 250, 90, 30), border_radius=4)
        screen.blit(FONT_MAIN.render("Отмена", True, COLOR_BLACK), (372, 256))
        pygame.draw.rect(screen, (60, 179, 113), (450, 250, 90, 30), border_radius=4)
        screen.blit(FONT_MAIN.render("Сохранить", True, COLOR_WHITE), (465, 256))

    pygame.display.flip()
    clock.tick(FPS)
pygame.quit()
