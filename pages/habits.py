# -*- coding: utf-8 -*-
"""Страница «Привычки»: таблица, поиск, фильтры, сортировка и отметки.

Все данные берутся из SQLite через services. Пользователь видит только
свои привычки; администратор управляет всеми записями в отдельном окне.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import db
import services
import theme
from theme import font
from widgets import AnimatedButton, Card, show_toast
from windows.dialogs import HabitDialog


class HabitsPage(tk.Frame):
    """Рабочий список привычек с отметкой выполнения за сегодня."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self._cat_map = {}
        self._build()
        self.refresh()

    # --- Интерфейс -------------------------------------------------------

    def _build(self):
        container = tk.Frame(self, bg=theme.BG)
        container.pack(fill="both", expand=True, padx=26, pady=(22, 18))

        tk.Label(
            container, text="Мои привычки", bg=theme.BG,
            fg=theme.TEXT_PRIMARY, font=font(20, bold=True),
        ).pack(anchor="w")
        tk.Label(
            container,
            text="Поиск, фильтрация по категории, сортировка и отметка выполнения за сегодня",
            bg=theme.BG, fg=theme.TEXT_SECONDARY, font=font(10),
        ).pack(anchor="w", pady=(4, 14))

        filters = Card(container, padx=16, pady=12)
        filters.pack(fill="x")
        bar = tk.Frame(filters.body, bg=theme.CARD_BG)
        bar.pack(fill="x")

        tk.Label(bar, text="Поиск:", bg=theme.CARD_BG,
                 fg=theme.TEXT_SECONDARY, font=font(9)).pack(side="left")
        self._search = tk.Entry(
            bar, width=20, font=font(10), bg=theme.INPUT_BG,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.CARD_BORDER, highlightcolor=theme.ACCENT,
        )
        self._search.pack(side="left", ipady=4, padx=(6, 12))
        self._search.bind("<Return>", lambda _e: self.refresh())

        tk.Label(bar, text="Категория:", bg=theme.CARD_BG,
                 fg=theme.TEXT_SECONDARY, font=font(9)).pack(side="left")
        self._category = tk.StringVar(value="Все категории")
        self._category_combo = ttk.Combobox(
            bar, textvariable=self._category, values=["Все категории"],
            state="readonly", width=15, font=font(10),
        )
        self._category_combo.pack(side="left", padx=(6, 12))
        self._category_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        tk.Label(bar, text="Сортировка:", bg=theme.CARD_BG,
                 fg=theme.TEXT_SECONDARY, font=font(9)).pack(side="left")
        self._sort = tk.StringVar(value="name")
        sort_combo = ttk.Combobox(
            bar, textvariable=self._sort,
            values=["name", "category", "done"],
            state="readonly", width=12, font=font(10),
        )
        sort_combo.pack(side="left", padx=(6, 12))
        sort_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        AnimatedButton(bar, text="Применить", command=self.refresh, size=9).pack(side="left")

        actions = tk.Frame(filters.body, bg=theme.CARD_BG)
        actions.pack(fill="x", pady=(12, 0))
        for text, command in (
            ("Добавить", self._add_habit),
            ("Изменить", self._edit_habit),
            ("Отметить / снять", self._toggle_done),
        ):
            AnimatedButton(actions, text=text, command=command, size=9).pack(
                side="left", padx=(0, 8),
            )
        AnimatedButton(
            actions, text="Удалить", command=self._delete_habit, size=9,
            color=theme.DANGER, hover=theme.DANGER_HOVER, press="#991B1B",
        ).pack(side="left")
        AnimatedButton(
            actions, text="Сбросить фильтры", command=self._reset_filters, size=9,
            color=theme.TEXT_SECONDARY, hover=theme.SIDEBAR_HOVER,
            press=theme.SIDEBAR_BG,
        ).pack(side="right")

        table_card = Card(container, padx=14, pady=12)
        table_card.pack(fill="both", expand=True, pady=(14, 0))
        self._build_table(table_card.body)

    def _build_table(self, parent):
        frame = tk.Frame(parent, bg=theme.CARD_BG)
        frame.pack(fill="both", expand=True)
        columns = {
            "id": ("ID", 50), "name": ("Привычка", 230),
            "category": ("Категория", 130), "streak": ("Серия, дней", 100),
            "today": ("Сегодня", 120), "done": ("Выполнено", 100),
            "created": ("Создана", 110),
        }
        self._tree = ttk.Treeview(
            frame, columns=list(columns), show="headings", height=12,
        )
        for key, (title, width) in columns.items():
            self._tree.heading(key, text=title)
            self._tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._tree.bind("<Double-1>", lambda _e: self._toggle_done())

        self._hint = tk.Label(
            parent, text="Двойной клик по строке — переключить отметку за сегодня",
            bg=theme.CARD_BG, fg=theme.TEXT_MUTED, font=font(9),
        )
        self._hint.pack(anchor="w", pady=(8, 0))

    # --- Данные ----------------------------------------------------------

    def refresh(self):
        """Перечитать категории и строки из базы данных."""
        categories = services.categories_list()
        self._cat_map = {item["name"]: item["id"] for item in categories}
        values = ["Все категории"] + list(self._cat_map)
        self._category_combo.configure(values=values)
        if self._category.get() not in values:
            self._category.set("Все категории")

        category_id = self._cat_map.get(self._category.get(), 0)
        rows = services.habits_list(
            self.app.user["id"],
            search=self._search.get().strip(),
            category_id=category_id,
            sort=self._sort.get(),
        )
        self._rows = {row["id"]: row for row in rows}
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            self._tree.insert("", "end", iid=str(row["id"]), values=(
                row["id"], row["name"], row["category_name"],
                services.habit_streak(row["id"]),
                "✓ выполнено" if row["today_done"] else "○ не выполнено",
                row["done_days"], row["created_at"],
            ))
        self._hint.configure(
            text=f"Показано: {len(rows)}  •  двойной клик по строке — переключить отметку за сегодня"
        )

    def focus_record(self, record_id):
        key = str(record_id)
        if self._tree.exists(key):
            self._tree.selection_set(key)
            self._tree.focus(key)
            self._tree.see(key)

    def _selected_id(self):
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo("Привычки", "Выберите привычку в таблице", parent=self)
            return None
        return int(selection[0])

    def _reset_filters(self):
        self._search.delete(0, "end")
        self._category.set("Все категории")
        self._sort.set("name")
        self.refresh()

    # --- CRUD ------------------------------------------------------------

    def _add_habit(self):
        dialog = HabitDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        services.add_habit(
            self.app.user["id"], data["category_id"], data["name"], data["description"],
        )
        db.log_action(self.app.user["id"], "Добавлена привычка", data["name"])
        show_toast(self, "Привычка добавлена")
        self.refresh()

    def _edit_habit(self):
        habit_id = self._selected_id()
        if habit_id is None:
            return
        dialog = HabitDialog(self, services.get_habit(habit_id))
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        services.update_habit(
            habit_id, data["category_id"], data["name"], data["description"],
        )
        db.log_action(self.app.user["id"], "Изменена привычка", data["name"])
        show_toast(self, "Изменения сохранены")
        self.refresh()

    def _delete_habit(self):
        habit_id = self._selected_id()
        if habit_id is None:
            return
        name = self._rows[habit_id]["name"]
        if not messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить привычку «{name}»?\nИстория выполнений также будет удалена.",
            parent=self,
        ):
            return
        services.delete_habit(habit_id)
        db.log_action(self.app.user["id"], "Удалена привычка", name)
        show_toast(self, "Привычка удалена", theme.DANGER)
        self.refresh()

    def _toggle_done(self):
        habit_id = self._selected_id()
        if habit_id is None:
            return
        row = self._rows[habit_id]
        new_value = not bool(row["today_done"])
        services.mark_habit(habit_id, new_value)
        db.log_action(
            self.app.user["id"],
            "Отметка выполнения" if new_value else "Снятие отметки",
            row["name"],
        )
        show_toast(self, "Отметка обновлена" if new_value else "Отметка снята")
        self.refresh()
