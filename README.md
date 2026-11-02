# BlocklyKlik
Визуальный редактор кода для Arduino и ESP32

На сегодняшний момент вышло обновление графического редактора кода BlocklyKlik 2.0

Его задача - это упростить процесс написания программ и помочь учителям и ученикам освоить текстовый язык программирования.

Сейчас доступны сборки под:
# [Windows](https://drive.google.com/file/d/1lr3Im4tx_ayapyEh6G6a5_uJfwAASHVU/view?usp=drive_link) 
# [Linux Debian 64 bit](https://drive.google.com/file/d/1h4Jpe2KMlRzJR2LbmZcA8e3vleMd6cTx/view?usp=sharing)
# [Linux Red OS 64 bit](https://drive.google.com/file/d/1s_yVA87ClNtz6kL2Q2ShZPq_OrMWovxA/view) (старая сборка)

Так же доступен для всех желающих исходный код редактора, см. репозиторий: BlocklyKlik2_Visual.py, BloklyEngine2.py, Test_Editor.py 

Для полноценной работы с исходным кодом вам понадобится установить python 3.11 или выше и библиотеки pyserial и pygame-ce

Исходный файл должен лежать рядом с папкой компилятора arduino : 
Для  Windows  - это папка с именем arduino_ide
Для Linux  - это папка с именем arduino_klik
Данные папки вы можете найти в архивах собранного проекта в папке dist.

Чтобы собрать свой проект в исполняемый файл используйте библиотеку pyinstaller - она компилирует файл под ту операционную систему, в которой работает.
