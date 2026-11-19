# -*- coding: utf-8 -*-
"""Модальные окна добавления/редактирования и результаты поиска."""

import datetime
import os
import re
import tkinter as tk
from tkinter import messagebox, ttk

import services
import theme
from security import (
    require_date, require_int, require_password, require_text, require_username,
)
from theme import font
from widgets import AnimatedButton, Card

COLOR_PRESETS = [
    ("Синий", theme.ACCENT), ("Зелёный", theme.SUCCESS),
    ("Оранжевый", theme.WARNING), ("Фиолетовый", "#8B5CF6"),
    ("Розовый", "#EC4899"), ("Серый", "#64748B"),
]


class BaseDialog(tk.Toplevel):
    """Базовое модальное окно с кнопками «Сохранить» / «Отмена»."""

    def __init__(self, master, title, width=460, height=380):
        super().__init__(master)
        self.title(title)
        self.configure(bg=theme.BG)
        self.resizable(False, False)
        self.transient(master)
        self.result = None
        self._width, self._height = width, height
        self._center()

        self._content = tk.Frame(self, bg=theme.BG)
        self._content.pack(fill="both", expand=True, padx=22, pady=18)
        self._build()
        self.grab_set()
        self.focus_set()

    def _center(self):
        self.update_idletasks()
        x = self.master.winfo_rootx() + self.master.winfo_width() // 2 - self._width // 2
        y = self.master.winfo_rooty() + self.master.winfo_height() // 2 - self._height // 2
        self.geometry(f"{self._width}x{self._height}+{max(0, x)}+{max(0, y)}")

    def _label_entry(self, label, value="", show=None, row=0):
        tk.Label(
            self._content, text=label, bg=theme.BG,
            fg=theme.TEXT_PRIMARY, font=font(10, bold=True),
        ).grid(row=row, column=0, sticky="w", pady=(10, 4))
        entry = tk.Entry(
            self._content, font=font(11), bg=theme.INPUT_BG,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.CARD_BORDER,
            highlightcolor=theme.ACCENT, show=show or "",
        )
        entry.grid(row=row + 1, column=0, sticky="ew", ipady=5)
        if value:
            entry.insert(0, value)
        return entry

    def _label_combo(self, label, values, current=None, row=0, readonly=True):
        tk.Label(
            self._content, text=label, bg=theme.BG,
            fg=theme.TEXT_PRIMARY, font=font(10, bold=True),
        ).grid(row=row, column=0, sticky="w", pady=(10, 4))
        variable = tk.StringVar(value=current or (values[0] if values else ""))
        combo = ttk.Combobox(
            self._content, textvariable=variable, values=values,
            state="readonly" if readonly else "normal", font=font(11),
        )
        combo.grid(row=row + 1, column=0, sticky="ew", ipady=4)
        return variable, combo

    def _buttons(self, save_command):
        row = tk.Frame(self._content, bg=theme.BG)
        row.grid(row=20, column=0, sticky="ew", pady=(22, 0))
        AnimatedButton(row, text="Сохранить", command=save_command).pack(side="right")
        AnimatedButton(
            row, text="Отмена", command=self.destroy,
            color=theme.TEXT_SECONDARY, hover=theme.SIDEBAR_HOVER,
            press=theme.SIDEBAR_BG,
        ).pack(side="right", padx=(0, 10))

    def _fail(self, exc):
        messagebox.showerror("Проверка ввода", str(exc), parent=self)

    def _build(self):
        raise NotImplementedError


class HabitDialog(BaseDialog):
    """Добавление / редактирование привычки."""

    def __init__(self, master, habit=None):
        self.habit = habit
        super().__init__(master, "Привычка" if not habit else "Редактирование привычки")

    def _build(self):
        self._content.columnconfigure(0, weight=1)
        categories = services.categories_list()
        self._cat_map = {item["name"]: item["id"] for item in categories}
        current = next(
            (c["name"] for c in categories if c["id"] == self.habit["category_id"]),
            None,
        ) if self.habit else None

        self.name = self._label_entry(
            "Название", self.habit["name"] if self.habit else "", row=0,
        )
        self.description = self._label_entry(
            "Описание", self.habit["description"] if self.habit else "", row=2,
        )
        self.category, _ = self._label_combo(
            "Категория", list(self._cat_map), current, row=4,
        )
        self._buttons(self._save)

    def _save(self):
        try:
            name = require_text(self.name.get(), "Название", 2, 80)
            description = require_text(
                self.description.get(), "Описание", 0, 200
            ) if self.description.get().strip() else ""
            if self.category.get() not in self._cat_map:
                raise ValueError("Выберите категорию из списка")
            self.result = {
                "name": name,
                "description": description,
                "category_id": self._cat_map[self.category.get()],
            }
            self.destroy()
        except ValueError as exc:
            self._fail(exc)


class GoalDialog(BaseDialog):
    """Добавление / редактирование цели."""

    def __init__(self, master, goal=None):
        self.goal = goal
        super().__init__(master, "Новая цель" if not goal else "Редактирование цели", 460, 470)

    def _build(self):
        self._content.columnconfigure(0, weight=1)
        categories = services.categories_list()
        self._cat_map = {item["name"]: item["id"] for item in categories}
        current = next(
            (c["name"] for c in categories if c["id"] == self.goal["category_id"]),
            None,
        ) if self.goal else None

        self.title_entry = self._label_entry(
            "Название цели", self.goal["title"] if self.goal else "", row=0,
        )
        self.description = self._label_entry(
            "Описание", self.goal["description"] if self.goal else "", row=2,
        )
        self.target = self._label_entry(
            "Целевое значение", str(self.goal["target_value"]) if self.goal else "100", row=4,
        )
        default_deadline = self.goal["deadline"] if self.goal else (
            datetime.date.today() + datetime.timedelta(days=30)
        ).isoformat()
        self.deadline = self._label_entry("Дедлайн (ГГГГ-ММ-ДД)", default_deadline, row=6)
        self.category, _ = self._label_combo(
            "Категория", list(self._cat_map), current, row=8,
        )
        self._buttons(self._save)

    def _save(self):
        try:
            self.result = {
                "title": require_text(self.title_entry.get(), "Название", 2, 120),
                "description": self.description.get().strip()[:200],
                "target_value": require_int(self.target.get(), "Целевое значение", 1, 10_000_000),
                "deadline": require_date(self.deadline.get(), "Дедлайн"),
                "category_id": self._cat_map[self.category.get()],
            }
            self.destroy()
        except (ValueError, KeyError) as exc:
            self._fail(exc)


class UserDialog(BaseDialog):
    """Добавление / редактирование пользователя (только администратор)."""

    def __init__(self, master, user=None):
        self.user = user
        super().__init__(master, "Пользователь" if not user else "Редактирование пользователя", 460, 500)

    def _build(self):
        self._content.columnconfigure(0, weight=1)
        self.username = self._label_entry(
            "Логин", self.user["username"] if self.user else "", row=0,
        )
        self.full_name = self._label_entry(
            "ФИО", self.user["full_name"] if self.user else "", row=2,
        )
        self.password = self._label_entry("Пароль", show="*", row=4)
        self.password_label = tk.Label(
            self._content, text="При редактировании оставьте пустым — пароль не изменится",
            bg=theme.BG, fg=theme.TEXT_SECONDARY, font=font(9),
        )
        self.password_label.grid(row=5, column=0, sticky="w")

        show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self._content, text="Показать пароль", variable=show_var,
            bg=theme.BG, fg=theme.TEXT_SECONDARY, font=font(9),
            activebackground=theme.BG, selectcolor=theme.CARD_BG,
            command=lambda: self.password.configure(show="" if show_var.get() else "*"),
        ).grid(row=6, column=0, sticky="w", pady=(6, 0))

        roles = {r["name"]: r["id"] for r in services.query("SELECT * FROM roles ORDER BY id")}
        self._roles = roles
        current = next(
            (name for name, rid in roles.items() if rid == self.user["role_id"]), None
        ) if self.user else "user"
        self.role, _ = self._label_combo("Роль", list(roles), current, row=7)
        self._buttons(self._save)

    def _save(self):
        try:
            password = self.password.get().strip()
            if not self.user or password:
                password = require_password(password)
            self.result = {
                "username": require_username(self.username.get()),
                "full_name": require_text(self.full_name.get(), "ФИО", 2, 120),
                "password": password,
                "role_id": self._roles[self.role.get()],
            }
            self.destroy()
        except (ValueError, KeyError) as exc:
            self._fail(exc)


class CategoryDialog(BaseDialog):
    """Справочник категорий с выбором цвета."""

    def __init__(self, master, category=None):
        self.category = category
        super().__init__(master, "Категория" if not category else "Редактирование категории", 460, 380)

    def _build(self):
        self._content.columnconfigure(0, weight=1)
        self.name = self._label_entry(
            "Название", self.category["name"] if self.category else "", row=0,
        )
        self.color = self._label_entry(
            "Цвет (HEX)", self.category["color"] if self.category else theme.ACCENT, row=2,
        )
        tk.Label(
            self._content, text="Быстрый выбор цвета:", bg=theme.BG,
            fg=theme.TEXT_SECONDARY, font=font(9),
        ).grid(row=4, column=0, sticky="w", pady=(12, 6))
        swatches = tk.Frame(self._content, bg=theme.BG)
        swatches.grid(row=5, column=0, sticky="w")
        for index, (name, color) in enumerate(COLOR_PRESETS):
            button = tk.Button(
                swatches, text=name, bg=color, fg="#FFFFFF", font=font(9, bold=True),
                relief="flat", bd=0, cursor="hand2", padx=8, pady=4,
                command=lambda c=color: self.color.delete(0, "end") or self.color.insert(0, c),
            )
            button.grid(row=0, column=index % 3, padx=3, pady=3, sticky="ew")
        self._buttons(self._save)

    def _save(self):
        try:
            color = require_text(self.color.get(), "Цвет", 7, 7)
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                raise ValueError("Цвет задаётся в формате #RRGGBB")
            self.result = {
                "name": require_text(self.name.get(), "Название", 2, 60),
                "color": color.upper(),
            }
            self.destroy()
        except ValueError as exc:
            self._fail(exc)


class ProgressDialog(BaseDialog):
    """Обновление прогресса цели: ползунок + описание + история."""

    def __init__(self, master, goal):
        self.goal = goal
        super().__init__(master, "Обновить прогресс", 480, 500)

    def _build(self):
        self._content.columnconfigure(0, weight=1)
        tk.Label(
            self._content, text=self.goal["title"], bg=theme.BG,
            fg=theme.TEXT_PRIMARY, font=font(12, bold=True), wraplength=420,
        ).grid(row=0, column=0, sticky="w", pady=(6, 12))

        self.value = tk.IntVar(value=self.goal["progress"])
        self.scale = tk.Scale(
            self._content, from_=0, to=100, orient="horizontal",
            variable=self.value, bg=theme.BG, fg=theme.TEXT_PRIMARY,
            activebackground=theme.ACCENT, troughcolor=theme.TRACK_BG,
            highlightthickness=0, length=410,
            command=self._on_scale,
        )
        self.scale.grid(row=1, column=0, sticky="ew")

        self.percent = tk.Label(
            self._content, text=f"Новое значение: {self.value.get()}%",
            bg=theme.BG, fg=theme.ACCENT, font=font(12, bold=True),
        )
        self.percent.grid(row=2, column=0, sticky="w", pady=(4, 10))

        self.note = self._label_entry("Комментарий", row=3)

        tk.Label(
            self._content, text="История изменений", bg=theme.BG,
            fg=theme.TEXT_SECONDARY, font=font(9, bold=True),
        ).grid(row=5, column=0, sticky="w", pady=(12, 4))
        history = services.goal_history(self.goal["id"])[:4]
        text = "\n".join(
            f"{row['updated_at'][:10]}  {row['progress']}%  {row['note']}"
            for row in history
        ) or "Изменений пока нет"
        tk.Label(
            self._content, text=text, bg=theme.CARD_BG, fg=theme.TEXT_SECONDARY,
            font=font(9, mono=True), justify="left", anchor="w", padx=10, pady=8,
        ).grid(row=6, column=0, sticky="ew")

        self._buttons(self._save)

    def _on_scale(self, _value):
        self.percent.configure(text=f"Новое значение: {self.value.get()}%")

    def _save(self):
        try:
            self.result = {
                "progress": require_int(self.value.get(), "Прогресс", 0, 100),
                "note": require_text(self.note.get(), "Комментарий", 3, 150),
            }
            self.destroy()
        except ValueError as exc:
            self._fail(exc)


class SearchResults(tk.Toplevel):
    """Окно результатов сквозного поиска с переходом к найденной записи."""

    def __init__(self, master, query_text, results, on_open):
        super().__init__(master)
        self.title(f"Результаты поиска: «{query_text}»")
        self.configure(bg=theme.BG)
        self.geometry("720x400")
        self.transient(master)
        self._on_open = on_open
        self._results = results
        self._center()

        header = tk.Frame(self, bg=theme.HEADER_BG, padx=18, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text=f"Найдено: {len(results)}",
            bg=theme.HEADER_BG, fg="#FFFFFF", font=font(12, bold=True),
        ).pack(anchor="w")

        table_frame = tk.Frame(self, bg=theme.BG)
        table_frame.pack(fill="both", expand=True, padx=16, pady=14)

        columns = ("type", "title", "subtitle")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=12,
        )
        for key, text, width in (
            ("type", "Тип", 120), ("title", "Название", 250), ("subtitle", "Подробности", 300),
        ):
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, anchor="w")
        for index, item in enumerate(results):
            self.tree.insert(
                "", "end", iid=str(index),
                values=(item["type"], item["title"], item["subtitle"]),
            )
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _e: self._open())

        footer = tk.Frame(self, bg=theme.BG)
        footer.pack(fill="x", padx=16, pady=(0, 14))
        AnimatedButton(footer, text="Перейти", command=self._open).pack(side="right")
        AnimatedButton(
            footer, text="Закрыть", command=self.destroy,
            color=theme.TEXT_SECONDARY, hover=theme.SIDEBAR_HOVER,
            press=theme.SIDEBAR_BG,
        ).pack(side="right", padx=(0, 10))

    def _center(self):
        self.update_idletasks()
        x = self.master.winfo_rootx() + self.master.winfo_width() // 2 - 360
        y = self.master.winfo_rooty() + self.master.winfo_height() // 2 - 200
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _open(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Поиск", "Выберите запись из списка", parent=self)
            return
        item = self._results[int(selection[0])]
        self.destroy()
        self._on_open(item)
