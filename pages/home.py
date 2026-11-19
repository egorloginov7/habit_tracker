# -*- coding: utf-8 -*-
"""Главный экран: статистика, быстрые действия и журнал действий.

Верхний баннер — AnimatedBackground: фон двигается сам, без пользователя.
"""

import datetime
import tkinter as tk

import db
import services
import theme
from theme import font
from widgets import AnimatedBackground, AnimatedButton, Card, StatCard, show_toast


class Hero(AnimatedBackground):
    """Анимированный баннер с текстом поверх движущегося градиента."""

    def __init__(self, master, title, subtitle, **kwargs):
        self._title = title
        self._subtitle = subtitle
        super().__init__(master, base=theme.BG, interval=70, **kwargs)

    def _draw(self):
        super()._draw()  # градиент и пятна
        if self.winfo_width() < 200:
            return
        self.create_text(
            28, 44, text=self._title, anchor="w",
            font=font(21, bold=True), fill=theme.TEXT_PRIMARY,
        )
        self.create_text(
            28, 82, text=self._subtitle, anchor="w",
            font=font(10), fill=theme.TEXT_SECONDARY,
        )
        self.create_text(
            28, 116,
            text="Статистика обновляется при каждом открытии раздела",
            anchor="w", font=font(9), fill=theme.TEXT_MUTED,
        )


class HomePage(tk.Frame):
    """Главная страница приложения."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app

        hour = datetime.datetime.now().hour
        greeting = (
            "Доброй ночи" if hour < 6 else
            "Доброе утро" if hour < 12 else
            "Добрый день" if hour < 18 else "Добрый вечер"
        )
        self._hero = Hero(
            self,
            f"{greeting}, {app.user['full_name'].split()[0]}!",
            "Трекер привычек и целей — настольное приложение",
            height=160,
        )
        self._build()
        self._hero.pack(fill="x", pady=(0, 14))
        self._hero.start()
        self.refresh()

    def _build(self):
        container = tk.Frame(self, bg=theme.BG)
        container.pack(fill="both", expand=True, padx=24, pady=(18, 20))

        # Статистика
        stats = tk.Frame(container, bg=theme.BG)
        stats.pack(fill="x")
        self.card_habits = StatCard(stats, "Привычек всего", subtitle="в базе данных")
        self.card_habits.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.card_done = StatCard(
            stats, "Выполнено сегодня", subtitle="отметок за день", accent=theme.SUCCESS,
        )
        self.card_done.pack(side="left", fill="both", expand=True, padx=10)
        self.card_goals = StatCard(stats, "Активных целей", subtitle="целей в работе")
        self.card_goals.pack(side="left", fill="both", expand=True, padx=10)
        self.card_progress = StatCard(
            stats, "Средний прогресс", subtitle="по всем целям", accent=theme.WARNING,
        )
        self.card_progress.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # Быстрые действия
        actions = Card(container)
        actions.pack(fill="x", pady=(14, 0))
        tk.Label(
            actions.body, text="Быстрые действия", bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(12, bold=True),
        ).pack(anchor="w")
        tk.Label(
            actions.body,
            text="Выберите раздел: отметить привычки, скорректировать цели "
                 "или посчитать прогресс за период.",
            bg=theme.CARD_BG, fg=theme.TEXT_SECONDARY, font=font(10),
        ).pack(anchor="w", pady=(5, 13))

        buttons = tk.Frame(actions.body, bg=theme.CARD_BG)
        buttons.pack(anchor="w")
        for text, page in (
            ("Мои привычки", "Привычки"),
            ("Мои цели", "Цели"),
            ("График прогресса", "Прогресс"),
        ):
            AnimatedButton(
                buttons, text=text, command=lambda p=page: self.app.navigate(p),
            ).pack(side="left", padx=(0, 10))

        # Последние действия
        activity = Card(container)
        activity.pack(fill="both", expand=True, pady=(14, 0))
        header = tk.Frame(activity.body, bg=theme.CARD_BG)
        header.pack(fill="x", pady=(0, 6))
        tk.Label(
            header, text="Последние действия", bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(12, bold=True),
        ).pack(side="left")
        AnimatedButton(
            header, text="Обновить", size=9, command=self.refresh,
        ).pack(side="right")

        self._activity = tk.Frame(activity.body, bg=theme.CARD_BG)
        self._activity.pack(fill="both", expand=True)

    def refresh(self):
        """Пересчитать показатели и список действий из БД."""
        stats = services.dashboard_stats(
            self.app.user["id"], self.app.is_admin,
        )
        self.card_habits.set_value(str(stats["habits"]))
        self.card_done.set_value(str(stats["done_today"]))
        self.card_goals.set_value(str(stats["goals"]))
        self.card_progress.set_value(f"{stats['avg_progress']}%")

        for child in self._activity.winfo_children():
            child.destroy()

        rows = services.recent_actions(
            limit=6, user_id=self.app.user["id"], is_admin=self.app.is_admin,
        )
        if not rows:
            tk.Label(
                self._activity, text="Действий пока нет",
                bg=theme.CARD_BG, fg=theme.TEXT_SECONDARY, font=font(10),
            ).pack(anchor="w", pady=8)
            return
        for row in rows:
            line = tk.Frame(self._activity, bg=theme.CARD_BG)
            line.pack(fill="x", pady=3)
            tk.Label(
                line, text=row["created_at"][:16], bg=theme.CARD_BG,
                fg=theme.TEXT_MUTED, font=font(9, mono=True), width=17, anchor="w",
            ).pack(side="left")
            tk.Label(
                line, text=row["action"], bg=theme.CARD_BG,
                fg=theme.TEXT_PRIMARY, font=font(10, bold=True), width=24, anchor="w",
            ).pack(side="left")
            tk.Label(
                line, text=row["details"], bg=theme.CARD_BG,
                fg=theme.TEXT_SECONDARY, font=font(9), anchor="w",
            ).pack(side="left", fill="x", expand=True)
