# -*- coding: utf-8 -*-
"""Точка входа приложения «Трекер привычек и целей».

Запуск из папки проекта:
    python main.py
(если команда python не работает — попробуйте: py main.py)

После запуска открывается окно входа; после авторизации — главное окно,
а для администратора дополнительно доступно окно администрирования.
"""

import sys
import tkinter as tk
from tkinter import ttk

import db
import theme
from theme import font
from windows.login_window import LoginWindow
from windows.main_window import MainWindow


def make_dpi_aware():
    """Сделать текст чётким на экранах с высоким разрешением (Windows)."""
    if sys.platform == "win32":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            # На старых версиях Windows вызов недоступен — просто пропускаем
            pass


def configure_styles():
    """Единый стиль ttk-элементов (таблицы и выпадающие списки)."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "Treeview",
        background=theme.CARD_BG,
        fieldbackground=theme.CARD_BG,
        foreground=theme.TEXT_PRIMARY,
        rowheight=28,
        borderwidth=0,
        font=font(10),
    )
    style.configure(
        "Treeview.Heading",
        background=theme.BG_DEEP,
        foreground=theme.TEXT_PRIMARY,
        font=font(9, bold=True),
        relief="flat",
        padding=6,
    )
    style.map(
        "Treeview",
        background=[("selected", theme.ACCENT_SOFT)],
        foreground=[("selected", theme.TEXT_PRIMARY)],
    )
    style.configure(
        "TCombobox",
        fieldbackground=theme.INPUT_BG,
        background=theme.INPUT_BG,
        foreground=theme.TEXT_PRIMARY,
        arrowcolor=theme.ACCENT,
        borderwidth=1,
        padding=4,
        font=font(10),
    )


def start_main_window(user):
    """Открыть главное окно после успешной авторизации."""
    app = MainWindow(user, on_logout=show_login)
    app.mainloop()


def show_login():
    """Показать экран входа (также используется после выхода из системы)."""
    login = LoginWindow(on_success=start_main_window)
    login.mainloop()


def main():
    make_dpi_aware()
    db.init_db()
    configure_styles()
    show_login()


if __name__ == "__main__":
    main()
