# -*- coding: utf-8 -*-
"""Страница «Контакты / О программе» с проверкой и копированием данных.

Данные AUTHOR — это ФИО, группа и телефон владельца проекта. Помимо текста
на странице есть интерактивные действия: копирование в буфер, проверка
формата телефона через security.require_phone и обновление статистики БД.
"""

import tkinter as tk

import db
import security
import theme
from theme import font
from widgets import AnimatedButton, Card, show_toast

AUTHOR = {
    "full_name": "Логинов Егор Андреевич",
    "group": "22о",
    "phone": "+375298313240",
}

ABOUT_TEXT = (
    "«Трекер привычек и целей» — настольное приложение для ежедневного контроля "
    "привычек и долгосрочных целей. Данные хранятся локально в SQLite: 8 связанных "
    "таблиц с первичными и внешними ключами. Реализованы две роли (пользователь и "
    "администратор), сквозной поиск, фильтры, сортировка, отчёты в CSV и резервное "
    "копирование базы. Интерфейс и логика написаны вручную на Python + Tkinter."
)


class ContactsPage(tk.Frame):
    """Контакты владельца проекта и сведения о программе."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self._build()
        self.refresh()

    def _build(self):
        container = tk.Frame(self, bg=theme.BG)
        container.pack(fill="both", expand=True, padx=26, pady=(22, 18))

        tk.Label(
            container, text="Контакты и о программе", bg=theme.BG,
            fg=theme.TEXT_PRIMARY, font=font(20, bold=True),
        ).pack(anchor="w")
        tk.Label(
            container, text="Автор проекта и краткая информация о системе",
            bg=theme.BG, fg=theme.TEXT_SECONDARY, font=font(10),
        ).pack(anchor="w", pady=(4, 14))

        columns = tk.Frame(container, bg=theme.BG)
        columns.pack(fill="both", expand=True)

        author_card = Card(columns, padx=20, pady=18)
        author_card.pack(side="left", fill="both", expand=True)
        tk.Label(
            author_card.body, text="Автор проекта", bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(13, bold=True),
        ).pack(anchor="w", pady=(0, 14))

        for title, value, key in (
            ("ФИО", AUTHOR["full_name"], "full_name"),
            ("Группа", AUTHOR["group"], "group"),
            ("Телефон", AUTHOR["phone"], "phone"),
        ):
            row = tk.Frame(author_card.body, bg=theme.CARD_BG)
            row.pack(fill="x", pady=6)
            tk.Label(
                row, text=title, bg=theme.CARD_BG,
                fg=theme.TEXT_SECONDARY, font=font(9), width=10, anchor="w",
            ).pack(side="left")
            display_font = font(11, mono=True) if key == "phone" else font(11, bold=True)
            tk.Label(
                row, text=value, bg=theme.CARD_BG,
                fg=theme.TEXT_PRIMARY, font=display_font, anchor="w",
            ).pack(side="left", fill="x", expand=True)
            AnimatedButton(
                row, text="Копировать", size=8,
                command=lambda v=value: self._copy(v),
                color=theme.TEXT_SECONDARY, hover=theme.SIDEBAR_HOVER,
                press=theme.SIDEBAR_BG,
            ).pack(side="right")

        check_row = tk.Frame(author_card.body, bg=theme.CARD_BG)
        check_row.pack(fill="x", pady=(18, 0))
        AnimatedButton(
            check_row, text="Проверить телефон", command=self._check_phone, size=9,
            color=theme.SUCCESS, hover=theme.SUCCESS_HOVER, press="#047857",
        ).pack(side="left")
        self._check_label = tk.Label(
            check_row, text="", bg=theme.CARD_BG,
            fg=theme.TEXT_SECONDARY, font=font(9),
        )
        self._check_label.pack(side="left", padx=12)

        about_card = Card(columns, padx=20, pady=18)
        about_card.pack(side="right", fill="both", expand=True, padx=(14, 0))
        tk.Label(
            about_card.body, text="О программе", bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(13, bold=True),
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            about_card.body, text=ABOUT_TEXT, bg=theme.CARD_BG,
            fg=theme.TEXT_SECONDARY, font=font(10), wraplength=430, justify="left",
        ).pack(anchor="w")

        tk.Label(
            about_card.body, text="Состав базы данных", bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(11, bold=True),
        ).pack(anchor="w", pady=(16, 8))
        self._db_info = tk.Label(
            about_card.body, text="", bg=theme.CARD_BG,
            fg=theme.TEXT_SECONDARY, font=font(9, mono=True), justify="left", anchor="w",
        )
        self._db_info.pack(anchor="w", fill="x")

        refresh_row = tk.Frame(about_card.body, bg=theme.CARD_BG)
        refresh_row.pack(fill="x", pady=(14, 0))
        AnimatedButton(
            refresh_row, text="Обновить статистику БД", command=self.refresh, size=9,
        ).pack(side="left")

    def _copy(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        show_toast(self, "Скопировано в буфер обмена")

    def _check_phone(self):
        try:
            normalized = security.require_phone(AUTHOR["phone"])
        except ValueError as exc:
            self._check_label.configure(text=str(exc), fg=theme.DANGER)
            return
        self._check_label.configure(
            text=f"Формат корректен: {normalized}", fg=theme.SUCCESS,
        )

    def refresh(self):
        counts = db.table_counts()
        names = {
            "roles": "Роли", "users": "Пользователи", "categories": "Категории",
            "habits": "Привычки", "goals": "Цели", "habit_logs": "История привычек",
            "goal_progress": "Прогресс целей", "action_logs": "Журнал действий",
        }
        lines = [f"{names[key]:<20} {counts[key]:>4}" for key in names]
        self._db_info.configure(text="\n".join(lines))
