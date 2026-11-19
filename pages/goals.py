# -*- coding: utf-8 -*-
"""Страница «Цели»: таблица целей, фильтры, CRUD и обновление прогресса."""

import tkinter as tk
from tkinter import messagebox, ttk

import db
import services
import theme
from theme import font
from widgets import AnimatedButton, Card, ProgressBar, show_toast
from windows.dialogs import GoalDialog, ProgressDialog

STATUS_MAP = {
    "Все статусы": "all",
    "В работе (< 70%)": "active",
    "Почти готово / завершено": "done",
}


class GoalsPage(tk.Frame):
    """Рабочий список целей с анимированным индикатором прогресса."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self._cat_map = {}
        self._rows = {}
        self._build()
        self.refresh()

    # --- Интерфейс -------------------------------------------------------

    def _build(self):
        container = tk.Frame(self, bg=theme.BG)
        container.pack(fill="both", expand=True, padx=26, pady=(22, 18))

        tk.Label(
            container, text="Мои цели", bg=theme.BG,
            fg=theme.TEXT_PRIMARY, font=font(20, bold=True),
        ).pack(anchor="w")
        tk.Label(
            container,
            text="Поиск, фильтры, сортировка, расчёт статуса и обновление прогресса",
            bg=theme.BG, fg=theme.TEXT_SECONDARY, font=font(10),
        ).pack(anchor="w", pady=(4, 14))

        filters = Card(container, padx=16, pady=12)
        filters.pack(fill="x")
        bar = tk.Frame(filters.body, bg=theme.CARD_BG)
        bar.pack(fill="x")

        tk.Label(bar, text="Поиск:", bg=theme.CARD_BG,
                 fg=theme.TEXT_SECONDARY, font=font(9)).pack(side="left")
        self._search = tk.Entry(
            bar, width=18, font=font(10), bg=theme.INPUT_BG, relief="flat",
            highlightthickness=1, highlightbackground=theme.CARD_BORDER,
            highlightcolor=theme.ACCENT,
        )
        self._search.pack(side="left", ipady=4, padx=(6, 10))
        self._search.bind("<Return>", lambda _e: self.refresh())

        self._category = tk.StringVar(value="Все категории")
        self._category_combo = ttk.Combobox(
            bar, textvariable=self._category, values=["Все категории"],
            state="readonly", width=14, font=font(10),
        )
        self._category_combo.pack(side="left", padx=(0, 10))
        self._category_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self._status = tk.StringVar(value="Все статусы")
        status_combo = ttk.Combobox(
            bar, textvariable=self._status, values=list(STATUS_MAP),
            state="readonly", width=20, font=font(10),
        )
        status_combo.pack(side="left", padx=(0, 10))
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self._sort = tk.StringVar(value="name")
        sort_combo = ttk.Combobox(
            bar, textvariable=self._sort, values=["name", "progress", "deadline"],
            state="readonly", width=10, font=font(10),
        )
        sort_combo.pack(side="left", padx=(0, 10))
        sort_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        AnimatedButton(bar, text="Применить", command=self.refresh, size=9).pack(side="left")

        actions = tk.Frame(filters.body, bg=theme.CARD_BG)
        actions.pack(fill="x", pady=(12, 0))
        for text, command in (
            ("Добавить", self._add_goal),
            ("Изменить", self._edit_goal),
            ("Обновить прогресс", self._update_progress),
        ):
            AnimatedButton(actions, text=text, command=command, size=9).pack(
                side="left", padx=(0, 8),
            )
        AnimatedButton(
            actions, text="Удалить", command=self._delete_goal, size=9,
            color=theme.DANGER, hover=theme.DANGER_HOVER, press="#991B1B",
        ).pack(side="left")
        AnimatedButton(
            actions, text="Сбросить", command=self._reset_filters, size=9,
            color=theme.TEXT_SECONDARY, hover=theme.SIDEBAR_HOVER,
            press=theme.SIDEBAR_BG,
        ).pack(side="right")

        table_card = Card(container, padx=14, pady=12)
        table_card.pack(fill="both", expand=True, pady=(14, 0))
        self._build_table(table_card.body)

        progress_card = Card(container, padx=16, pady=12)
        progress_card.pack(fill="x", pady=(12, 0))
        info = tk.Frame(progress_card.body, bg=theme.CARD_BG)
        info.pack(fill="x", pady=(0, 8))
        tk.Label(
            info, text="Прогресс выбранной цели", bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(11, bold=True),
        ).pack(side="left")
        self._progress_label = tk.Label(
            info, text="—", bg=theme.CARD_BG, fg=theme.ACCENT,
            font=font(11, bold=True),
        )
        self._progress_label.pack(side="right")
        self._progress_bar = ProgressBar(progress_card.body, height=14)
        self._progress_bar.pack(fill="x")

    def _build_table(self, parent):
        frame = tk.Frame(parent, bg=theme.CARD_BG)
        frame.pack(fill="both", expand=True)
        columns = {
            "id": ("ID", 48), "title": ("Цель", 245),
            "category": ("Категория", 115), "progress": ("Прогресс", 85),
            "target": ("Цель (знач.)", 95), "deadline": ("Дедлайн", 110),
            "updates": ("Обновлений", 90), "status": ("Статус", 120),
        }
        self._tree = ttk.Treeview(
            frame, columns=list(columns), show="headings", height=11,
        )
        for key, (title, width) in columns.items():
            self._tree.heading(key, text=title)
            self._tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._show_selected_progress())
        self._tree.bind("<Double-1>", lambda _e: self._update_progress())

    # --- Данные ----------------------------------------------------------

    def refresh(self):
        categories = services.categories_list()
        self._cat_map = {item["name"]: item["id"] for item in categories}
        values = ["Все категории"] + list(self._cat_map)
        self._category_combo.configure(values=values)
        if self._category.get() not in values:
            self._category.set("Все категории")

        rows = services.goals_list(
            self.app.user["id"],
            search=self._search.get().strip(),
            category_id=self._cat_map.get(self._category.get(), 0),
            sort=self._sort.get(),
            status=STATUS_MAP.get(self._status.get(), "all"),
        )
        self._rows = {row["id"]: row for row in rows}
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            progress = row["progress"]
            status = (
                "Завершено" if progress >= 100 else
                "Почти готово" if progress >= 70 else "В работе"
            )
            self._tree.insert("", "end", iid=str(row["id"]), values=(
                row["id"], row["title"], row["category_name"], f"{progress}%",
                row["target_value"], row["deadline"], row["updates_count"], status,
            ))
        self._show_selected_progress()

    def focus_record(self, record_id):
        key = str(record_id)
        if self._tree.exists(key):
            self._tree.selection_set(key)
            self._tree.focus(key)
            self._tree.see(key)
            self._show_selected_progress()

    def _show_selected_progress(self):
        selection = self._tree.selection()
        if not selection:
            self._progress_label.configure(text="Выберите цель")
            self._progress_bar.set(0)
            return
        row = self._rows.get(int(selection[0]))
        if row is None:
            return
        percent = row["progress"]
        self._progress_label.configure(text=f"{row['title'][:34]} — {percent}%")
        self._progress_bar.set(percent)

    def _selected_id(self):
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo("Цели", "Выберите цель в таблице", parent=self)
            return None
        return int(selection[0])

    def _reset_filters(self):
        self._search.delete(0, "end")
        self._category.set("Все категории")
        self._status.set("Все статусы")
        self._sort.set("name")
        self.refresh()

    # --- CRUD ------------------------------------------------------------

    def _add_goal(self):
        dialog = GoalDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        services.add_goal(
            self.app.user["id"], data["category_id"], data["title"],
            data["description"], data["target_value"], data["deadline"],
        )
        db.log_action(self.app.user["id"], "Добавлена цель", data["title"])
        show_toast(self, "Цель добавлена")
        self.refresh()

    def _edit_goal(self):
        goal_id = self._selected_id()
        if goal_id is None:
            return
        dialog = GoalDialog(self, services.get_goal(goal_id))
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        services.update_goal(
            goal_id, data["category_id"], data["title"], data["description"],
            data["target_value"], data["deadline"],
        )
        db.log_action(self.app.user["id"], "Изменена цель", data["title"])
        show_toast(self, "Изменения сохранены")
        self.refresh()

    def _delete_goal(self):
        goal_id = self._selected_id()
        if goal_id is None:
            return
        name = self._rows[goal_id]["title"]
        if not messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить цель «{name}»?\nИстория прогресса также будет удалена.",
            parent=self,
        ):
            return
        services.delete_goal(goal_id)
        db.log_action(self.app.user["id"], "Удалена цель", name)
        show_toast(self, "Цель удалена", theme.DANGER)
        self.refresh()

    def _update_progress(self):
        goal_id = self._selected_id()
        if goal_id is None:
            return
        record = dict(self._rows[goal_id])
        record.update(services.get_goal(goal_id))
        dialog = ProgressDialog(self, record)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        services.set_goal_progress(goal_id, data["progress"], data["note"])
        db.log_action(
            self.app.user["id"], "Обновление прогресса",
            f"{record['title']}: {data['progress']}%",
        )
        show_toast(self, "Прогресс обновлён")
        self.refresh()
