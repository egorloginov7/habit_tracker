# -*- coding: utf-8 -*-
"""Окно №2: главное окно приложения.

Содержит обязательные элементы: header (шапка), footer (подвал),
хлебные крошки, сквозной поиск, боковую навигацию и 5 рабочих разделов.
Анимации: скользящий индикатор меню, вспышка перехода между экранами,
плавная смена цвета «хлебных крошек», бегущая строка в подвале.
"""

import datetime
import tkinter as tk
from tkinter import messagebox

import db
import services
import theme
from theme import font, mix
from widgets import AnimatedButton, SidebarButton

from pages.home import HomePage
from pages.habits import HabitsPage
from pages.goals import GoalsPage
from pages.progress import ProgressPage
from pages.contacts import ContactsPage
from windows.admin_window import AdminWindow
from windows.dialogs import SearchResults

PAGES = [
    ("Главная", "●  Главная", HomePage),
    ("Привычки", "▪  Привычки", HabitsPage),
    ("Цели", "○  Цели", GoalsPage),
    ("Прогресс", "▲  Прогресс", ProgressPage),
    ("Контакты", "♦  Контакты", ContactsPage),
]

TICKER_TEXT = (
    "  Трекер привычек и целей  •  версия 1.0  •  SQLite + Tkinter  "
    "•  Логинов Егор Андреевич, группа 22о  •  "
)


class MainWindow(tk.Tk):
    """Главное рабочее окно (root после успешной авторизации)."""

    def __init__(self, user, on_logout):
        super().__init__()
        self.user = user
        self.is_admin = user["role_id"] == 1
        self._on_logout = on_logout
        self._admin_window = None
        self.current_page = "Главная"
        self._indicator_y = 90
        self._alive = True

        self.title("Трекер привычек и целей")
        self.geometry("1180x720")
        self.minsize(1040, 660)
        self.configure(bg=theme.BG)

        self._build_header()
        self._build_body()
        self._build_footer()
        self.protocol("WM_DELETE_WINDOW", self.logout)

        self.navigate("Главная")
        self._tick_clock()
        self._tick_ticker()

    # --- Шапка ---

    def _build_header(self):
        header = tk.Frame(self, bg=theme.HEADER_BG)
        header.pack(fill="x")
        header.grid_columnconfigure(1, weight=1)

        brand = tk.Frame(header, bg=theme.HEADER_BG, padx=18, pady=10)
        tk.Label(
            brand, text="ТРЕКЕР", bg=theme.HEADER_BG,
            fg="#FFFFFF", font=font(15, bold=True),
        ).pack(anchor="w")
        tk.Label(
            brand, text="привычек и целей", bg=theme.HEADER_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(9),
        ).pack(anchor="w")
        brand.grid(row=0, column=0, sticky="w")

        crumb_frame = tk.Frame(header, bg=theme.HEADER_BG)
        tk.Label(
            crumb_frame, text="Навигация", bg=theme.HEADER_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(8),
        ).pack(anchor="w")
        self._crumb = tk.Label(
            crumb_frame, text="Главная", bg=theme.HEADER_BG,
            fg=theme.ACCENT_SOFT, font=font(11, bold=True),
        )
        self._crumb.pack(anchor="w")
        crumb_frame.grid(row=0, column=1, sticky="w", padx=(12, 0))

        search_frame = tk.Frame(header, bg=theme.HEADER_BG)
        self.search_entry = tk.Entry(
            search_frame, width=22, font=font(10), bg="#FFFFFF",
            relief="flat", highlightthickness=1,
            highlightbackground=theme.SIDEBAR_HOVER,
            highlightcolor=theme.ACCENT,
        )
        self.search_entry.pack(side="left", ipady=4)
        self.search_entry.bind("<Return>", lambda _e: self._search())
        AnimatedButton(
            search_frame, text="Найти", command=self._search, size=9,
        ).pack(side="left", padx=6)
        search_frame.grid(row=0, column=2, padx=14)

        role = "Администратор" if self.is_admin else "Пользователь"
        user_frame = tk.Frame(header, bg=theme.HEADER_BG, padx=8)
        tk.Label(
            user_frame, text=self.user["full_name"], bg=theme.HEADER_BG,
            fg="#FFFFFF", font=font(10, bold=True),
        ).pack(anchor="e")
        tk.Label(
            user_frame, text=f"@{self.user['username']} · {role}",
            bg=theme.HEADER_BG, fg=theme.TEXT_ON_DARK_MUTED, font=font(8),
        ).pack(anchor="e")
        user_frame.grid(row=0, column=3, sticky="e")

        actions = tk.Frame(header, bg=theme.HEADER_BG, padx=12)
        if self.is_admin:
            AnimatedButton(
                actions, text="Админка", command=self.open_admin, size=9,
            ).pack(side="left", padx=(0, 8))
        AnimatedButton(
            actions, text="Выход", command=self.logout, size=9,
            color=theme.DANGER, hover=theme.DANGER_HOVER,
            press="#991B1B",
        ).pack(side="left")
        actions.grid(row=0, column=4, sticky="e")

    # --- Боковое меню и страницы ---

    def _build_body(self):
        body = tk.Frame(self, bg=theme.BG)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=theme.SIDEBAR_BG, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="РАЗДЕЛЫ", bg=theme.SIDEBAR_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(9, bold=True),
        ).pack(anchor="w", padx=18, pady=(22, 10))

        self._nav_buttons = {}
        self._nav_buttons_list = []
        for name, label, page_class in PAGES:
            button = SidebarButton(
                sidebar, text=label, command=lambda n=name: self.navigate(n)
            )
            button.pack(fill="x")
            self._nav_buttons[name] = button
            self._nav_buttons_list.append(button)

        # Движущийся индикатор активного раздела (анимация объекта)
        self._indicator = tk.Frame(sidebar, bg=theme.ACCENT, width=3, height=44)
        self._indicator.place(x=0, y=self._indicator_y)

        info = (
            "Права: " + ("администратор" if self.is_admin else "пользователь")
        )
        tk.Label(
            sidebar, text=info, bg=theme.SIDEBAR_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(9),
        ).pack(side="bottom", anchor="w", padx=18, pady=(0, 4))
        tk.Label(
            sidebar, text="v1.0 · SQLite", bg=theme.SIDEBAR_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(9),
        ).pack(side="bottom", anchor="w", padx=18, pady=(4, 14))

        self.content = tk.Frame(body, bg=theme.BG)
        self.content.pack(side="right", fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._pages = {}
        for name, _label, page_class in PAGES:
            page = page_class(self.content, app=self)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[name] = page

        # Линия анимации перехода между экранами
        self._transition = tk.Frame(self.content, bg=theme.ACCENT, height=3)
        self._transition.place(x=0, y=0, width=0, height=3)

    # --- Подвал ---

    def _build_footer(self):
        footer = tk.Frame(self, bg=theme.HEADER_BG)
        footer.pack(fill="x", side="bottom")

        self._status = tk.Label(
            footer, text="Готово", bg=theme.HEADER_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(9),
        )
        self._status.pack(side="left", padx=16, pady=7)

        self._ticker_text = TICKER_TEXT
        self._ticker = tk.Label(
            footer, text=TICKER_TEXT[:70], bg=theme.HEADER_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(9, mono=True),
        )
        self._ticker.pack(side="left", padx=20)

        self._clock = tk.Label(
            footer, text="", bg=theme.HEADER_BG,
            fg="#FFFFFF", font=font(9, mono=True),
        )
        self._clock.pack(side="right", padx=16)

    def _tick_clock(self):
        if not self._alive:
            return
        self._clock.configure(text=datetime.datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))
        self.after(1000, self._tick_clock)

    def _tick_ticker(self):
        if not self._alive:
            return
        # AUTOMATIC background-like animation in the main window footer
        self._ticker_text = self._ticker_text[1:] + self._ticker_text[0]
        self._ticker.configure(text=self._ticker_text[:70])
        self.after(220, self._tick_ticker)

    # --- Навигация и анимации ---

    def navigate(self, name, extra=""):
        """Открыть раздел, обновить хлебные крошки и анимировать переход."""
        if name not in self._pages:
            return
        page = self._pages[name]
        page.tkraise()
        page.refresh()

        self.current_page = name
        text = f"Главная  ›  {name}" + (f"  ›  {extra}" if extra else "")
        self._crumb.configure(text=text)
        self._status.configure(text=f"Открыт раздел: {name}")
        for page_name, button in self._nav_buttons.items():
            button.set_active(page_name == name)

        self._animate_indicator(name)
        self._animate_crumb()
        self._animate_transition()

    def _animate_indicator(self, name):
        """Индикатор плавно скользит к активному пункту меню."""
        index = [item[0] for item in PAGES].index(name)
        button = self._nav_buttons_list[index]

        def move():
            target_y = button.winfo_y()
            target_h = max(30, button.winfo_height())
            start_y = self._indicator_y
            steps = 9
            for step in range(1, steps + 1):
                t = step / steps
                y = round(start_y + (target_y - start_y) * t)
                height = round(44 + (target_h - 44) * t)
                self.after(
                    step * 18,
                    lambda y=y, h=height: self._indicator.place_configure(y=y, height=h),
                )
            self._indicator_y = target_y

        self.after(60, move)

    def _animate_crumb(self):
        """Цвет «хлебных крошек» плавно возвращается от акцента к белому."""
        steps = 8
        for step in range(steps + 1):
            color = mix(theme.ACCENT_SOFT, "#FFFFFF", step / steps)
            self.after(
                step * 22, lambda c=color: self._crumb.configure(fg=c)
            )

    def _animate_transition(self):
        """Тонкая полоса пробегает по верху рабочей области."""
        self.update_idletasks()
        width = max(100, self.content.winfo_width())
        steps = 12
        for step in range(steps + 1):
            progress = step / steps
            w = round(width * progress)
            color = mix(theme.ACCENT, theme.BG, progress)
            self.after(
                step * 16,
                lambda w=w, c=color, s=step: (
                    (self._transition.configure(bg=c),
                     self._transition.place_configure(width=w))
                    if s < steps else self._transition.place_forget()
                ),
            )

    # --- Сквозной поиск ---

    def _search(self):
        text = self.search_entry.get().strip()
        if len(text) < 2:
            messagebox.showinfo(
                "Поиск", "Введите минимум 2 символа для сквозного поиска", parent=self,
            )
            return
        results = services.global_search(text, self.is_admin, self.user["id"])
        db.log_action(self.user["id"], "Поиск", f"Запрос: {text}; найдено: {len(results)}")
        SearchResults(
            self, text, results,
            on_open=self._open_search_result,
        )

    def _open_search_result(self, item):
        target = item["page"]
        if target in ("Администрирование", "Журнал действий"):
            tab = "Журнал действий" if target == "Журнал действий" else None
            self.open_admin(tab, record_id=item["id"], page=target)
            return
        self.navigate(target, item["title"][:28])
        page = self._pages.get(target)
        if page is not None and hasattr(page, "focus_record"):
            self.after(150, lambda: page.focus_record(item["id"]))

    # --- Администрирование ---

    def open_admin(self, tab=None, record_id=None, page=None):
        """Открыть окно №3 или вывести уже открытое на передний план."""
        if not self.is_admin:
            messagebox.showwarning("Права доступа", "Только для администратора", parent=self)
            return
        if self._admin_window is not None and self._admin_window.winfo_exists():
            self._admin_window.lift()
            if record_id is not None:
                self._admin_window.focus_record(record_id, page=page)
            elif tab:
                self._admin_window.select_tab(tab)
            return

        def on_close():
            self._admin_window = None
            self._pages[self.current_page].refresh()

        self._admin_window = AdminWindow(
            self, self.user, initial_tab=tab, on_close=on_close,
        )
        if record_id is not None:
            # Окно ещё анимирует открытие — перейти к записи после анимации.
            self.after(300, lambda: (
                self._admin_window.focus_record(record_id, page=page)
                if self._admin_window is not None
                and self._admin_window.winfo_exists() else None
            ))

    # --- Выход ---

    def logout(self):
        if not messagebox.askyesno(
            "Выход", "Завершить работу и вернуться к экрану входа?", parent=self,
        ):
            return
        db.log_action(self.user["id"], "Выход из системы", "Завершение сеанса")
        self._alive = False
        for page in self._pages.values():
            hero = getattr(page, "_hero", None)
            if hero is not None:
                hero.stop()
        if self._admin_window is not None and self._admin_window.winfo_exists():
            self._admin_window.destroy()
        self.destroy()
        self._on_logout()
