import os
import subprocess
import sys
import pygame

# Инициализация Pygame
pygame.init()

# НАСТРОЙКА ОКНА: Общая ширина 1200 (500 под меню + 700 под видео)
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Главное Меню")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

# Настройки шрифта для подписи (можно сделать чуть меньше основного)
info_font = pygame.font.SysFont(None, 35)

# Текст, разбитый на строки
text_line1 = "Выберите модуль для начала работы."
text_line2 = "Редактор с открытым исходным кодом"
text_line3 = ""

# Координаты для текста (размещаем в левой зоне под кнопками)
# Вторая кнопка заканчивается на Y = 210, поэтому текст пустим с Y = 235
text_pos_1 = (20, 335)
text_pos_2 = (20, 455)
text_pos_3 = (20, 485)

# Цвет текста (например, светло-серый)
COLOR_INFO_TEXT = (200, 200, 200)

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


# 1. ЗАГРУЗКА И СЖАТИЕ КАДРОВ ПОД РАЗМЕР ПРАВОЙ ПАНЕЛИ (700x300)
frames = []
frames_dir = "m"

if os.path.exists(frames_dir):
    for i in range(1, 900):
        file_name = f"klik{i:04d}.png"
        frame_path = os.path.join(frames_dir, file_name)
        if os.path.exists(frame_path):
            if 478<=i<=498:
                pass
            else:
                img = pygame.image.load(frame_path).convert()  # .convert() ускоряет работу
                # Жестко задаем размер кадра 700 на 300
                img = pygame.transform.scale(img, (700, 600))
                frames.append(img)

current_frame = 0
has_animation = len(frames) > 0

# 2. ЗАГРУЗКА ИКОНОК ДЛЯ КНОПОК
IMAGE_SIZE = (80, 80)
try:
    img_klik = pygame.transform.scale(
        pygame.image.load("NikiESP32.png"), IMAGE_SIZE
    ).convert_alpha()
    img_blockly = pygame.transform.scale(
        pygame.image.load("Niki.png"), IMAGE_SIZE
    ).convert_alpha()
except pygame.error:
    img_klik = pygame.Surface(IMAGE_SIZE)
    img_klik.fill((0, 255, 0))
    img_blockly = pygame.Surface(IMAGE_SIZE)
    img_blockly.fill((0, 0, 255))

# 3. КООРДИНАТЫ КНОПОК И ИКОНОК (ВСЁ СЛЕВА)
# Иконки распределяем по левому краю
img_klik_pos = (30, 55)
img_blockly_pos = (30, 145)

# Кнопки ставим правее иконок, но в пределах левой зоны (до 500 пикселей)
btn_klik = pygame.Rect(140, 70, 220, 50)
btn_blockly = pygame.Rect(140, 160, 220, 50)

running = True
while running:
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

##        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
##            if btn_klik.collidepoint(event.pos):
##                subprocess.Popen([sys.executable, "Test_Editor.py"])
##                pygame.quit()
##                sys.exit()
##            elif btn_blockly.collidepoint(event.pos):
##                subprocess.Popen([sys.executable, "BlocklyKlik2_Visual.py"])
##                pygame.quit()
##                sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Определяем путь к текущей папке приложения, где лежат все модули
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            if btn_klik.collidepoint(event.pos):
                if getattr(sys, 'frozen', False):
                    # На Windows ищем .exe, на Linux/macOS запускаем файл без расширения
                    exe_ext = ".exe" if sys.platform == "win32" else ""
                    target_path = os.path.join(base_dir, f"Test_Editor{exe_ext}")

                    # Для Linux/macOS перед путем добавляем явное указание на запуск
                    if sys.platform != "win32":
                        subprocess.Popen([target_path], cwd=base_dir)
                    else:
                        subprocess.Popen([target_path], cwd=base_dir)
                else:
                    subprocess.Popen([sys.executable, "Test_Editor.py"], cwd=base_dir)
                pygame.quit()
                sys.exit()

            elif btn_blockly.collidepoint(event.pos):
                if getattr(sys, 'frozen', False):
                    exe_ext = ".exe" if sys.platform == "win32" else ""
                    target_path = os.path.join(base_dir, f"BlocklyKlik2_Visual{exe_ext}")

                    if sys.platform != "win32":
                        subprocess.Popen([target_path], cwd=base_dir)
                    else:
                        subprocess.Popen([target_path], cwd=base_dir)
                else:
                    subprocess.Popen([sys.executable, "BlocklyKlik2_Visual.py"], cwd=base_dir)
                pygame.quit()
                sys.exit()


    # Очищаем весь экран базовым цветом меню
    screen.fill((30, 30, 30))

    # 4. ОТРИСОВКА ВИДЕО С КОРРЕКТНЫМ СМЕЩЕНИЕМ
    if has_animation:
        # Сдвигаем видео ровно на 500 пикселей вправо, освобождая левую часть под кнопки
        shift_x = 500
        shift_y = 0

        screen.blit(frames[current_frame], (shift_x, shift_y))

        # Переключение кадров
        current_frame += 1
        if current_frame >= len(frames):
            current_frame = 0

    # 5. ОТРИСОВКА ИНТЕРФЕЙСА (ПОВЕРХ ЗАКРАШЕННОГО ФОНА СЛЕВА)
    # Рисуем иконки устройств
    screen.blit(img_klik, img_klik_pos)
    screen.blit(img_blockly, img_blockly_pos)

    # Логика подсветки кнопок при наведении
    color_1 = (160, 160, 160) if btn_klik.collidepoint(mouse_pos) else (100, 100, 100)
    color_2 = (
        (160, 160, 160) if btn_blockly.collidepoint(mouse_pos) else (100, 100, 100)
    )

    pygame.draw.rect(screen, color_1, btn_klik)
    pygame.draw.rect(screen, color_2, btn_blockly)

    # Текст на кнопках (сдвинут под новые координаты)
    screen.blit(font.render("Открыть KLIK_ESP32", True, (255, 255, 255)), (160, 85))
    screen.blit(
        font.render("Открыть BlocklyKlik", True, (255, 255, 255)), (160, 175)
    )

    # НАШ НОВЫЙ ТЕКСТ ПОД КНОПКАМИ:
    rendered_line1 = info_font.render(text_line1, True, COLOR_INFO_TEXT)
    rendered_line2 = info_font.render(text_line2, True, COLOR_INFO_TEXT)
    rendered_line3 = info_font.render(text_line3, True, COLOR_INFO_TEXT)

    screen.blit(rendered_line1, text_pos_1)
    screen.blit(rendered_line2, text_pos_2)
    screen.blit(rendered_line3, text_pos_3)

    pygame.display.flip()
    clock.tick(30)  # Стабильные 30 FPS для плавной анимации

pygame.quit()
