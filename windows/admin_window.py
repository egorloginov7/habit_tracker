# -*- coding: utf-8 -*-
"""Окно №3: панель администратора.

Четыре вкладки: пользователи, справочники, данные, журнал действий.
Все изменения подтверждаются и пишутся в журнал; удаление защищено
проверкой внешних ключей и диалогом подтверждения.
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

import db
import reports
import services
import theme
from theme import font
from widgets import AnimatedButton
from windows.dialogs import CategoryDialog, HabitDialog, GoalDialog, UserDialog

TABS = ["Пользователи", "Справочники", "Данные", "Журнал действий"]


class AdminWindow(tk.Toplevel):
    """Отдельное окно управления пользователями и данными."""

    def __init__(self, master, admin_user, initial_tab=None, on_close=None):
        super().__init__(master)
        self._admin = admin_user
        self._on_close = on_close
        self.title("Администрирование — Трекер привычек и целей")
        self.configure(bg=theme.BG)
        self.geometry("440x300")  # финальный размер задаётся анимацией открытия
        self._final_size = (960, 640)

        self._build()
        self.select_tab(initial_tab or TABS[0])
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._animate_open()

    # --- Каркас окна ---

    def _build(self):
        header = tk.Frame(self, bg=theme.HEADER_BG, padx=18, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text="АДМИНИСТРИРОВАНИЕ", bg=theme.HEADER_BG,
            fg="#FFFFFF", font=font(15, bold=True),
        ).pack(anchor="w")
        tk.Label(
            header, text=f"Вошёл: {self._admin['full_name']} · права администратора",
            bg=theme.HEADER_BG, fg=theme.TEXT_ON_DARK_MUTED, font=font(9),
        ).pack(anchor="w")

        tab_bar = tk.Frame(self, bg=theme.BG)
        tab_bar.pack(fill="x", padx=16, pady=(12, 4))
        self._tab_buttons = {}
        for name in TABS:
            button = AnimatedButton(
                tab_bar, text=name, command=lambda n=name: self.select_tab(n),
                color=theme.TEXT_SECONDARY,
                hover=theme.SIDEBAR_HOVER,
                press=theme.SIDEBAR_BG,
                size=9,
            )
            button.pack(side="left", padx=(0, 8))
            self._tab_buttons[name] = button

        self._tab_frames = {}
        body = tk.Frame(self, bg=theme.BG)
        body.pack(fill="both", expand=True, padx=16, pady=8)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        for name in TABS:
            frame = tk.Frame(body, bg=theme.BG)
            frame.grid(row=0, column=0, sticky="nsew")
            self._tab_frames[name] = frame

        self._build_users_tab(self._tab_frames[TABS[0]])
        self._build_categories_tab(self._tab_frames[TABS[1]])
        self._build_data_tab(self._tab_frames[TABS[2]])
        self._build_logs_tab(self._tab_frames[TABS[3]])
        self._build_reports_footer()

    def _build_reports_footer(self):
        footer = tk.Frame(self, bg=theme.CARD_BG, pady=8, padx=16)
        footer.pack(fill="x")
        AnimatedButton(
            footer, text="Отчёт: привычки", size=9,
            command=lambda: reports.export_habits_report(self, self._admin["id"], True),
        ).pack(side="left")
        AnimatedButton(
            footer, text="Отчёт: цели", size=9,
            command=lambda: reports.export_goals_report(self, self._admin["id"], True),
        ).pack(side="left", padx=8)
        AnimatedButton(
            footer, text="Резервная копия БД", size=9,
            command=lambda: reports.create_backup(self, self._admin["id"]),
            color=theme.SUCCESS, hover=theme.SUCCESS_HOVER, press="#047857",
        ).pack(side="left")
        AnimatedButton(
            footer, text="Закрыть", size=9,
            command=self._close, color=theme.TEXT_SECONDARY,
            hover=theme.SIDEBAR_HOVER, press=theme.SIDEBAR_BG,
        ).pack(side="right")

    def _toolbar(self, parent):
        bar = tk.Frame(parent, bg=theme.BG)
        bar.pack(fill="x", pady=(4, 10))
        return bar

    def _search_entry(self, bar, width=26):
        entry = tk.Entry(
            bar, width=width, font=font(10), bg=theme.INPUT_BG,
            relief="flat", highlightthickness=1,
            highlightbackground=theme.CARD_BORDER,
            highlightcolor=theme.ACCENT,
        )
        entry.pack(side="left", ipady=4, padx=(0, 8))
        return entry

    def _make_tree(self, parent, columns, heights=13):
        """Treeview с полосой прокрутки; iid строк — id записи в БД."""
        frame = tk.Frame(parent, bg=theme.CARD_BG)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(
            frame, columns=list(columns),
            show="headings", height=heights,
        )
        for key, (title, width) in columns.items():
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    # --- Вкладка «Пользователи» ---

    def _build_users_tab(self, parent):
        bar = self._toolbar(parent)
        self._user_search = self._search_entry(bar)
        AnimatedButton(bar, text="Найти", command=self._load_users, size=9).pack(side="left")
        AnimatedButton(bar, text="Добавить", command=self._add_user, size=9).pack(
            side="left", padx=(12, 0))
        AnimatedButton(bar, text="Изменить", command=self._edit_user, size=9).pack(
            side="left", padx=(8, 0))
        AnimatedButton(
            bar, text="Удалить", command=self._delete_user, size=9,
            color=theme.DANGER, hover=theme.DANGER_HOVER, press="#991B1B",
        ).pack(side="left", padx=(8, 0))
        self._user_tree = self._make_tree(parent, {
            "id": ("ID", 50), "username": ("Логин", 130),
            "full_name": ("ФИО", 280), "role": ("Роль", 120),
            "created": ("Создан", 140),
        })
        self._user_tree.bind("<Double-1>", lambda _e: self._edit_user())

    def _load_users(self):
        text = self._user_search.get().strip().lower()
        self._user_tree.delete(*self._user_tree.get_children())
        for row in services.users_list():
            if text and text not in row["full_name"].lower() and text not in row["username"].lower():
                continue
            self._user_tree.insert("", "end", iid=str(row["id"]), values=(
                row["id"], row["username"], row["full_name"],
                row["role_name"], row["created_at"][:10],
            ))

    def _add_user(self):
        dialog = UserDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            data = dialog.result
            services.add_user(
                data["username"], data["password"], data["role_id"], data["full_name"]
            )
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Такой логин уже существует", parent=self)
            return
        db.log_action(
            self._admin["id"], "Создание пользователя", data["username"]
        )
        self._load_users()

    def _edit_user(self):
        selected = self._user_tree.selection()
        if not selected:
            messagebox.showinfo("Пользователи", "Выберите пользователя", parent=self)
            return
        user_id = int(selected[0])
        dialog = UserDialog(self, services.get_user(user_id))
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        try:
            services.update_user(
                user_id, data["username"], data["role_id"],
                data["full_name"], data["password"],
            )
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Такой логин уже существует", parent=self)
            return
        db.log_action(
            self._admin["id"], "Изменение пользователя", data["username"]
        )
        self._load_users()

    def _delete_user(self):
        selected = self._user_tree.selection()
        if not selected:
            messagebox.showinfo("Пользователи", "Выберите пользователя", parent=self)
            return
        user_id = int(selected[0])
        if user_id == self._admin["id"]:
            messagebox.showwarning("Удаление", "Нельзя удалить самого себя", parent=self)
            return
        user = services.get_user(user_id)
        if not messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить пользователя «{user['full_name']}»?\n"
            "Связанные привычки и цели также будут удалены.",
            parent=self,
        ):
            return
        try:
            services.delete_user(user_id)
        except sqlite3.IntegrityError as exc:
            messagebox.showerror("Ошибка", f"Есть связанные записи:\n{exc}", parent=self)
            return
        db.log_action(self._admin["id"], "Удаление пользователя", user["full_name"])
        self._load_users()

    # --- Вкладка «Справочники» ---

    def _build_categories_tab(self, parent):
        bar = self._toolbar(parent)
        self._category_search = self._search_entry(bar)
        AnimatedButton(bar, text="Найти", command=self._load_categories, size=9).pack(side="left")
        AnimatedButton(bar, text="Добавить", command=self._add_category, size=9).pack(
            side="left", padx=(12, 0))
        AnimatedButton(bar, text="Изменить", command=self._edit_category, size=9).pack(
            side="left", padx=(8, 0))
        AnimatedButton(
            bar, text="Удалить", command=self._delete_category, size=9,
            color=theme.DANGER, hover=theme.DANGER_HOVER, press="#991B1B",
        ).pack(side="left", padx=(8, 0))
        self._category_tree = self._make_tree(parent, {
            "id": ("ID", 60), "name": ("Название", 260), "color": ("Цвет (HEX)", 160),
        })
        self._category_tree.bind("<Double-1>", lambda _e: self._edit_category())

    def _load_categories(self):
        text = self._category_search.get().strip().lower()
        self._category_tree.delete(*self._category_tree.get_children())
        for row in services.categories_list():
            if text and text not in row["name"].lower():
                continue
            self._category_tree.insert(
                "", "end", iid=str(row["id"]),
                values=(row["id"], row["name"], row["color"]),
            )

    def _add_category(self):
        dialog = CategoryDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            services.add_category(**dialog.result)
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Такая категория уже есть", parent=self)
            return
        db.log_action(self._admin["id"], "Добавление категории", dialog.result["name"])
        self._load_categories()

    def _edit_category(self):
        selected = self._category_tree.selection()
        if not selected:
            messagebox.showinfo("Справочники", "Выберите категорию", parent=self)
            return
        category_id = int(selected[0])
        current = db.query("SELECT * FROM categories WHERE id = ?", (category_id,), one=True)
        dialog = CategoryDialog(self, current)
        self.wait_window(dialog)
        if not dialog.result:
            return
        services.update_category(category_id, **dialog.result)
        db.log_action(self._admin["id"], "Изменение категории", dialog.result["name"])
        self._load_categories()

    def _delete_category(self):
        selected = self._category_tree.selection()
        if not selected:
            messagebox.showinfo("Справочники", "Выберите категорию", parent=self)
            return
        category_id = int(selected[0])
        name = self._category_tree.item(selected[0])["values"][1]
        if not messagebox.askyesno(
            "Подтверждение удаления", f"Удалить категорию «{name}»?", parent=self,
        ):
            return
        try:
            services.delete_category(category_id)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Ошибка",
                "Категория используется в привычках или целях — удаление запрещено",
                parent=self,
            )
            return
        db.log_action(self._admin["id"], "Удаление категории", name)
        self._load_categories()

    # --- Вкладка «Данные» ---

    def _build_data_tab(self, parent):
        bar = self._toolbar(parent)
        self._data_type = tk.StringVar(value="Привычки")
        type_combo = ttk.Combobox(
            bar, textvariable=self._data_type, values=["Привычки", "Цели"],
            state="readonly", width=11, font=font(10),
        )
        type_combo.pack(side="left", padx=(0, 8))
        type_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_data())

        users = services.users_list()
        self._data_user = tk.StringVar(value="Все пользователи")
        self._data_user_map = {"Все пользователи": 0}
        self._data_user_map.update({u["full_name"]: u["id"] for u in users})
        user_combo = ttk.Combobox(
            bar, textvariable=self._data_user,
            values=list(self._data_user_map), state="readonly",
            width=22, font=font(10),
        )
        user_combo.pack(side="left", padx=(0, 8))
        user_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_data())

        self._data_search = self._search_entry(bar, width=16)
        AnimatedButton(bar, text="Найти", command=self._load_data, size=9).pack(side="left")
        AnimatedButton(bar, text="Добавить", command=self._add_data, size=9).pack(
            side="left", padx=(12, 0))
        AnimatedButton(bar, text="Изменить", command=self._edit_data, size=9).pack(
            side="left", padx=(8, 0))
        AnimatedButton(
            bar, text="Удалить", command=self._delete_data, size=9,
            color=theme.DANGER, hover=theme.DANGER_HOVER, press="#991B1B",
        ).pack(side="left", padx=(8, 0))

        self._data_tree = self._make_tree(parent, {
            "id": ("ID", 50), "owner": ("Владелец", 180),
            "name": ("Название", 260), "category": ("Категория", 130),
            "extra": ("Доп. информация", 150),
        })
        self._data_tree.bind("<Double-1>", lambda _e: self._edit_data())

    def _load_data(self):
        text = self._data_search.get().strip().lower()
        user_id = self._data_user_map.get(self._data_user.get(), 0)
        self._data_tree.delete(*self._data_tree.get_children())
        if self._data_type.get() == "Привычки":
            rows = services.habits_list(0, search=text, all_users=True)
            for row in rows:
                if user_id and row["user_id"] != user_id:
                    continue
                self._data_tree.insert("", "end", iid=f"h{row['id']}", values=(
                    row["id"], row["username"], row["name"],
                    row["category_name"], f"выполнено: {row['done_days']}",
                ))
        else:
            rows = services.goals_list(0, search=text, all_users=True)
            for row in rows:
                if user_id and row["user_id"] != user_id:
                    continue
                self._data_tree.insert("", "end", iid=f"g{row['id']}", values=(
                    row["id"], row["username"], row["title"],
                    row["category_name"], f"{row['progress']}% · {row['deadline']}",
                ))

    def _add_data(self):
        """Создать привычку или цель для выбранного пользователя.

        Раньше во вкладке «Данные» можно было только редактировать и удалять
        существующие записи — добавить цель пользователю было невозможно.
        """
        owner_id = self._data_user_map.get(self._data_user.get(), 0)
        if not owner_id:
            messagebox.showinfo(
                "Данные",
                "Выберите владельца (пользователя) в фильтре выше, "
                "затем нажмите «Добавить»",
                parent=self,
            )
            return

        is_habit = self._data_type.get() == "Привычки"
        dialog = HabitDialog(self) if is_habit else GoalDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        if is_habit:
            services.add_habit(
                owner_id, data["category_id"], data["name"], data["description"]
            )
            name = data["name"]
            action = "Добавление привычки (админ)"
        else:
            services.add_goal(
                owner_id, data["category_id"], data["title"],
                data["description"], data["target_value"], data["deadline"],
            )
            name = data["title"]
            action = "Добавление цели (админ)"
        db.log_action(self._admin["id"], action, f"{name} · пользователь №{owner_id}")
        self._load_data()

    def _edit_data(self):
        selected = self._data_tree.selection()
        if not selected:
            messagebox.showinfo("Данные", "Выберите запись", parent=self)
            return
        key = selected[0]
        record_id = int(key[1:])
        if key.startswith("h"):
            record = services.get_habit(record_id)
            dialog = HabitDialog(self, record)
        else:
            record = services.get_goal(record_id)
            dialog = GoalDialog(self, record)
        self.wait_window(dialog)
        if not dialog.result:
            return
        data = dialog.result
        if key.startswith("h"):
            services.update_habit(
                record_id, data["category_id"], data["name"], data["description"]
            )
            db.log_action(self._admin["id"], "Изменение привычки (админ)", data["name"])
        else:
            services.update_goal(
                record_id, data["category_id"], data["title"],
                data["description"], data["target_value"], data["deadline"],
            )
            db.log_action(self._admin["id"], "Изменение цели (админ)", data["title"])
        self._load_data()

    def _delete_data(self):
        selected = self._data_tree.selection()
        if not selected:
            messagebox.showinfo("Данные", "Выберите запись", parent=self)
            return
        key = selected[0]
        record_id = int(key[1:])
        name = self._data_tree.item(key)["values"][2]
        if not messagebox.askyesno(
            "Подтверждение удаления", f"Удалить запись «{name}»?", parent=self,
        ):
            return
        if key.startswith("h"):
            services.delete_habit(record_id)
            db.log_action(self._admin["id"], "Удаление привычки (админ)", name)
        else:
            services.delete_goal(record_id)
            db.log_action(self._admin["id"], "Удаление цели (админ)", name)
        self._load_data()

    # --- Вкладка «Журнал действий» ---

    def _build_logs_tab(self, parent):
        bar = self._toolbar(parent)
        self._log_search = self._search_entry(bar, width=30)
        AnimatedButton(bar, text="Найти", command=self._load_logs, size=9).pack(side="left")

        users = services.users_list()
        self._log_user = tk.StringVar(value="Все пользователи")
        self._log_user_map = {"Все пользователи": 0}
        self._log_user_map.update({u["full_name"]: u["id"] for u in users})
        user_combo = ttk.Combobox(
            bar, textvariable=self._log_user,
            values=list(self._log_user_map), state="readonly",
            width=22, font=font(10),
        )
        user_combo.pack(side="left", padx=(0, 8))
        user_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_logs())

        AnimatedButton(bar, text="Обновить", command=self._load_logs, size=9).pack(side="left")
        self._log_tree = self._make_tree(parent, {
            "id": ("ID", 50), "date": ("Дата и время", 150),
            "user": ("Пользователь", 200), "action": ("Действие", 180),
            "details": ("Подробности", 320),
        })

    def _load_logs(self):
        text = self._log_search.get().strip()
        user_id = self._log_user_map.get(self._log_user.get(), 0)
        self._log_tree.delete(*self._log_tree.get_children())
        for row in services.action_logs_list(text, user_id):
            self._log_tree.insert("", "end", iid=str(row["id"]), values=(
                row["id"], row["created_at"], row["full_name"],
                row["action"], row["details"],
            ))

    # --- Управление вкладками ---

    def select_tab(self, name):
        if name not in TABS:
            name = TABS[0]
        for frame in self._tab_frames.values():
            frame.grid_remove()
        self._tab_frames[name].grid()
        for tab_name, button in self._tab_buttons.items():
            if tab_name == name:
                button.set_colors(theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESS)
            else:
                button.set_colors(
                    theme.TEXT_SECONDARY, theme.SIDEBAR_HOVER, theme.SIDEBAR_BG
                )
        self._active_tab = name
        {
            TABS[0]: self._load_users,
            TABS[1]: self._load_categories,
            TABS[2]: self._load_data,
            TABS[3]: self._load_logs,
        }[name]()
        db.log_action(self._admin["id"], "Открыта вкладка админки", name)

    def focus_record(self, record_id, page=None):
        """Перейти к записи из сквозного поиска.

        Таблицы неактивных вкладок изначально пусты, поэтому их нужно
        сначала загрузить — иначе переход из поиска никогда не срабатывал.
        """
        self._load_users()
        self._load_categories()
        self._load_logs()
        candidates = [
            (TABS[0], self._user_tree),
            (TABS[1], self._category_tree),
            (TABS[3], self._log_tree),
        ]
        if page == "Журнал действий":
            candidates = [(TABS[3], self._log_tree)]
        elif page == "Администрирование":
            candidates = [(TABS[0], self._user_tree), (TABS[1], self._category_tree)]

        key = str(record_id)
        target, tree = candidates[0]
        for tab, candidate in candidates:
            if candidate.exists(key):
                target, tree = tab, candidate
                break
        self.select_tab(target)
        if tree.exists(key):
            tree.selection_set(key)
            tree.focus(key)
            tree.see(key)

    def _animate_open(self):
        """Окно «вырастает» до полного размера — анимация появления."""
        width, height = 440, 300
        target_w, target_h = self._final_size
        steps = 10
        self._open_jobs = []
        for step in range(1, steps + 1):
            t = step / steps
            w = round(width + (target_w - width) * t)
            h = round(height + (target_h - height) * t)
            job = self.after(step * 22, lambda w=w, h=h: self._apply_open_size(w, h))
            self._open_jobs.append(job)

    def _apply_open_size(self, width, height):
        if not self.winfo_exists():
            return
        self.geometry(f"{width}x{height}")

    def _close(self):
        for job in getattr(self, "_open_jobs", []):
            try:
                self.after_cancel(job)
            except (ValueError, tk.TclError):
                pass
        if self._on_close:
            self._on_close()
        self.destroy()
