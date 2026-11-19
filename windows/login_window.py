# -*- coding: utf-8 -*-
"""Окно №1: авторизация по логину и паролю.

Фон окна анимируется автоматически (AnimatedBackground),
пароль проверяется по PBKDF2-хэшу из базы данных.
"""

import tkinter as tk
from tkinter import messagebox

import db
import services
import theme
from security import require_text
from theme import font
from widgets import AnimatedBackground, AnimatedButton, Card


class LoginWindow(tk.Tk):
    """Отдельное окно входа (root-окно приложения до авторизации)."""

    def __init__(self, on_success):
        super().__init__()
        self._on_success = on_success

        self.title("Вход — Трекер привычек и целей")
        self.geometry("900x600")
        self.minsize(760, 540)
        self.configure(bg=theme.BG)
        self.resizable(True, True)

        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self):
        # Анимированный фон: работает сам, без участия пользователя
        self._background = AnimatedBackground(self, base=theme.BG)
        self._background.pack(fill="both", expand=True)

        card = Card(self, padx=34, pady=32)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Логотип
        logo = tk.Canvas(card.body, width=54, height=54, bg=theme.ACCENT,
                         highlightthickness=0)
        logo.create_oval(9, 9, 45, 45, outline="#FFFFFF", width=2)
        logo.create_oval(22, 22, 32, 32, fill="#FFFFFF", outline="")
        logo.pack(anchor="center")

        tk.Label(
            card.body, text="Трекер привычек и целей",
            bg=theme.CARD_BG, fg=theme.TEXT_PRIMARY, font=font(19, bold=True),
        ).pack(anchor="center", pady=(14, 2))
        tk.Label(
            card.body, text="Вход в систему",
            bg=theme.CARD_BG, fg=theme.TEXT_SECONDARY, font=font(10),
        ).pack(anchor="center", pady=(0, 18))

        self.username = self._entry(card.body, "Логин", 0)
        self.password = self._entry(card.body, "Пароль", 2, show="*")

        show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            card.body, text="Показать пароль", variable=show_var,
            bg=theme.CARD_BG, fg=theme.TEXT_SECONDARY, font=font(9),
            activebackground=theme.CARD_BG, selectcolor=theme.CARD_BG,
            command=lambda: self.password.configure(show="" if show_var.get() else "*"),
        ).pack(anchor="w", pady=(8, 0))

        AnimatedButton(
            card.body, text="ВОЙТИ", command=self._login, width=24,
        ).pack(anchor="center", pady=(20, 12))

        tk.Label(
            card.body,
            text="Демо-доступы:  admin / admin123   •   user / user123",
            bg=theme.CARD_BG, fg=theme.TEXT_SECONDARY,
            font=font(9, mono=True),
        ).pack(anchor="center")
        tk.Label(
            card.body, text="Логинов Егор Андреевич · группа 22о",
            bg=theme.CARD_BG, fg=theme.TEXT_MUTED, font=font(9),
        ).pack(anchor="center", pady=(10, 0))

        self.bind("<Return>", lambda _event: self._login())
        self._background.start()

    def _entry(self, parent, label, row, show=""):
        tk.Label(
            parent, text=label, bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(10, bold=True),
        ).pack(anchor="w", pady=(8, 4))
        entry = tk.Entry(
            parent, font=font(11), bg=theme.INPUT_BG, fg=theme.TEXT_PRIMARY,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.CARD_BORDER,
            highlightcolor=theme.ACCENT, show=show, width=30,
        )
        entry.pack(anchor="w", ipady=6, fill="x")
        return entry

    def _login(self):
        try:
            username = require_text(self.username.get(), "Логин", 3, 20)
            password = require_text(self.password.get(), "Пароль", 6, 100)
        except ValueError as exc:
            messagebox.showerror("Проверка ввода", str(exc), parent=self)
            return

        user = services.authenticate(username, password)
        if user is None:
            db.log_action(None, "Неудачная попытка входа", f"Логин: {username}")
            messagebox.showerror(
                "Ошибка входа", "Неверный логин или пароль", parent=self,
            )
            self.password.delete(0, "end")
            self.password.focus_set()
            return

        db.log_action(user["id"], "Вход в систему", "Успешная авторизация")
        self._background.stop()
        self.destroy()
        self._on_success(user)
