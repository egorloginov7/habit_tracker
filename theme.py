# -*- coding: utf-8 -*-
"""Единая цветовая схема, шрифты и утилиты для анимаций.

ОБОСНОВАНИЕ ПАЛИТРЫ (для защиты):
  * #0F172A «тёмный сланец» — основной якорь (шапка, боковое меню).
    Холодный тёмный тон читается как «профессиональный», даёт высокий
    контраст с белым текстом (контрастное отношение > 14:1).
  * #F1F5F9 «светлый сланец» — фон рабочей области. Это тот же оттенок,
    что и шапка, но осветлённый: получается монохромная база без «пестроты».
  * #FFFFFF — карточки. Принцип 60/30/10: 60% тёмная/светлая нейтральная
    база, 30% белые поверхности, 10% акценты.
  * #2563EB «синий» — единственный акцент действия (кнопки, активный пункт,
    график). Синий традиционно ассоциируется с доверием и историей успеха.
  * #10B981 «изумруд» — семантический зелёный для успеха/выполнения.
  * #F59E0B «янтарь» — семантический жёлтый для предупреждений.
  * #EF4444 «красный» — только удаление и ошибки.
  Цвета подобраны по принципу «аналогичной» сине-зелёной гаммы: акцент
  и успех соседствуют в цветовом круге, поэтому не конфликтуют.

ОБОСНОВАНИЕ ШРИФТОВОЙ ПАРЫ (для защиты):
  * Segoe UI — основной интерфейсный гуманистический гротеск. Крупный
    x-height и нейтральные формы хорошо читаются на экране, шрифт встроен
    в Windows и не требует установки.
  * Consolas — моноширинный шрифт для чисел, дат, логов и кодовых значений.
    У него фиксированная ширина и табличные цифры: столбцы выравниваются,
    а пара «Segoe UI + Consolas» даёт классический контраст sans / mono
    при похожей геометрии и высоте цифр.
"""

FONT_UI = "Segoe UI"
FONT_MONO = "Consolas"

# Нейтральная база
BG = "#F1F5F9"
BG_DEEP = "#E2E8F0"
SIDEBAR_BG = "#0F172A"
HEADER_BG = "#0F172A"
SIDEBAR_HOVER = "#1E293B"
SIDEBAR_ACTIVE = "#2563EB"

# Поверхности
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E2E8F0"
INPUT_BG = "#FFFFFF"

# Акценты
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
ACCENT_PRESS = "#1E40AF"
ACCENT_SOFT = "#DBEAFE"
SUCCESS = "#10B981"
SUCCESS_HOVER = "#059669"
SUCCESS_SOFT = "#D1FAE5"
WARNING = "#F59E0B"
WARNING_SOFT = "#FEF3C7"
DANGER = "#EF4444"
DANGER_HOVER = "#DC2626"
DANGER_SOFT = "#FEE2E2"

# Текст
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#64748B"
TEXT_MUTED = "#94A3B8"
TEXT_ON_DARK = "#F1F5F9"
TEXT_ON_DARK_MUTED = "#94A3B8"

# Графика
TRACK_BG = "#E2E8F0"
GRID = "#E2E8F0"
SHADOW = "#CBD5E1"


def font(size=10, bold=False, mono=False):
    """Вернуть кортеж шрифта tkinter."""
    family = FONT_MONO if mono else FONT_UI
    return (family, size, "bold" if bold else "normal")


def rgb(color):
    """HEX-цвет -> кортеж (r, g, b)."""
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def hex_color(values):
    """Кортеж (r, g, b) -> HEX-цвет."""
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, round(v))) for v in values])


def mix(color_a, color_b, t):
    """Плавный переход между двумя цветами: t от 0 до 1."""
    a, b = rgb(color_a), rgb(color_b)
    return hex_color([a[i] + (b[i] - a[i]) * t for i in range(3)])
