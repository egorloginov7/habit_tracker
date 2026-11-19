# -*- coding: utf-8 -*-
"""Страница «Прогресс»: расчёт за период, анимированный график и отчёты."""

import datetime
import tkinter as tk
from tkinter import ttk

import db
import reports
import services
import theme
from theme import font, mix
from widgets import AnimatedButton, Card, StatCard


class ProgressPage(tk.Frame):
    """График выполнения привычек и выгрузка отчётов."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self._data = []
        self._days = 7
        self._anim_job = None
        self._build()
        self.refresh()

    # --- Интерфейс -------------------------------------------------------

    def _build(self):
        container = tk.Frame(self, bg=theme.BG)
        container.pack(fill="both", expand=True, padx=26, pady=(22, 18))

        header = tk.Frame(container, bg=theme.BG)
        header.pack(fill="x")
        tk.Label(
            header, text="Прогресс и отчёты", bg=theme.BG,
            fg=theme.TEXT_PRIMARY, font=font(20, bold=True),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Расчёт процента выполнения привычек за период и выгрузка данных в файл",
            bg=theme.BG, fg=theme.TEXT_SECONDARY, font=font(10),
        ).pack(anchor="w", pady=(4, 0))

        toolbar = tk.Frame(header, bg=theme.BG)
        toolbar.pack(anchor="w", pady=(14, 0))
        tk.Label(toolbar, text="Период:", bg=theme.BG,
                 fg=theme.TEXT_SECONDARY, font=font(10)).pack(side="left")
        self._period = tk.StringVar(value="7 дней")
        period_combo = ttk.Combobox(
            toolbar, textvariable=self._period,
            values=["7 дней", "14 дней", "30 дней"],
            state="readonly", width=10, font=font(10),
        )
        period_combo.pack(side="left", padx=(8, 10))
        period_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        AnimatedButton(toolbar, text="Пересчитать", command=self.refresh, size=9).pack(
            side="left", padx=(0, 8),
        )
        AnimatedButton(
            toolbar, text="Отчёт: привычки (CSV)", size=9,
            command=lambda: reports.export_habits_report(
                self, self.app.user["id"], self.app.is_admin,
            ),
        ).pack(side="left", padx=(0, 8))
        AnimatedButton(
            toolbar, text="Отчёт: цели (CSV)", size=9,
            command=lambda: reports.export_goals_report(
                self, self.app.user["id"], self.app.is_admin,
            ),
        ).pack(side="left", padx=(0, 8))
        AnimatedButton(
            toolbar, text="Копия БД", size=9,
            command=lambda: reports.create_backup(self, self.app.user["id"]),
            color=theme.SUCCESS, hover=theme.SUCCESS_HOVER, press="#047857",
        ).pack(side="left")

        stats = tk.Frame(container, bg=theme.BG)
        stats.pack(fill="x", pady=(16, 14))
        self._card_avg = StatCard(
            stats, "Средний результат", subtitle=f"за выбранный период",
        )
        self._card_avg.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._card_best = StatCard(
            stats, "Лучший день", subtitle="максимум за период", accent=theme.SUCCESS,
        )
        self._card_best.pack(side="left", fill="both", expand=True, padx=8)
        self._card_total = StatCard(
            stats, "Отметок всего", subtitle="выполнено за период",
        )
        self._card_total.pack(side="left", fill="both", expand=True, padx=8)
        self._card_forecast = StatCard(
            stats, "Прогноз на 7 дней", subtitle="при текущем темпе", accent=theme.WARNING,
        )
        self._card_forecast.pack(side="left", fill="both", expand=True, padx=(8, 0))

        chart_card = Card(container, padx=18, pady=16)
        chart_card.pack(fill="both", expand=True)
        title_row = tk.Frame(chart_card.body, bg=theme.CARD_BG)
        title_row.pack(fill="x", pady=(0, 8))
        tk.Label(
            title_row, text="Выполнение привычек по дням, %", bg=theme.CARD_BG,
            fg=theme.TEXT_PRIMARY, font=font(12, bold=True),
        ).pack(side="left")
        self._chart_subtitle = tk.Label(
            title_row, text="", bg=theme.CARD_BG,
            fg=theme.TEXT_SECONDARY, font=font(9),
        )
        self._chart_subtitle.pack(side="right")

        self._chart = tk.Canvas(
            chart_card.body, bg=theme.CARD_BG, highlightthickness=0,
        )
        self._chart.pack(fill="both", expand=True)
        self._chart.bind("<Configure>", lambda _e: self._draw_chart(1.0))

    # --- Расчёты ---------------------------------------------------------

    def refresh(self):
        """Пересчитать статистику и анимировать столбцы графика."""
        self._days = {"7 дней": 7, "14 дней": 14, "30 дней": 30}[self._period.get()]
        self._data = services.weekly_progress(
            self.app.user["id"], self._days, self.app.is_admin,
        )
        values = [item["percent"] for item in self._data]
        average = round(sum(values) / len(values)) if values else 0
        best = max(values) if values else 0
        best_day = next(
            (item["label"] for item in self._data if item["percent"] == best), "—"
        )
        marks = db.query(
            """SELECT COUNT(*) AS n FROM habit_logs l
               JOIN habits h ON h.id = l.habit_id
               WHERE l.done = 1 AND l.log_date BETWEEN ? AND ?"""
            + ("" if self.app.is_admin else " AND h.user_id = ?"),
            (self._data[0]["date"], self._data[-1]["date"])
            + (() if self.app.is_admin else (self.app.user["id"],)),
            one=True,
        )
        total_marks = marks["n"] if marks else 0

        self._card_avg.set_value(f"{average}%")
        self._card_best.set_value(f"{best}%")
        self._card_best.set_subtitle(f"лучший день: {best_day}")
        self._card_total.set_value(str(total_marks))
        forecast = min(100, round(average * 1.1))
        self._card_forecast.set_value(f"{forecast}%")
        self._chart_subtitle.configure(
            text=f"{self._days} дней · {datetime.date.today().strftime('%d.%m.%Y')}"
        )

        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except (ValueError, tk.TclError):
                pass
        self._animate_bars(0)

    def _animate_bars(self, step):
        """Постепенный рост столбцов — анимация объекта на экране."""
        self._draw_chart(step / 12)
        if step < 12:
            self._anim_job = self.after(28, lambda: self._animate_bars(step + 1))
        else:
            self._anim_job = None

    def _draw_chart(self, scale):
        canvas = self._chart
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 120 or height < 120 or not self._data:
            return
        canvas.delete("all")
        left, right, top, bottom = 42, 14, 16, 32
        plot_w = width - left - right
        plot_h = height - top - bottom
        if plot_w <= 0 or plot_h <= 0:
            return

        # Сетка и подписи уровня
        for percent in (0, 25, 50, 75, 100):
            y = top + plot_h * (1 - percent / 100)
            canvas.create_line(left, y, width - right, y, fill=theme.GRID, width=1)
            canvas.create_text(
                left - 8, y, text=f"{percent}%", anchor="e",
                font=font(8, mono=True), fill=theme.TEXT_MUTED,
            )

        count = len(self._data)
        slot = plot_w / count
        bar_w = max(3, min(34, slot * 0.62))
        for index, item in enumerate(self._data):
            value = item["percent"] * scale
            x_center = left + slot * (index + 0.5)
            y_top = top + plot_h * (1 - value / 100)
            color = mix(theme.ACCENT, theme.SUCCESS, value / 100)
            canvas.create_rectangle(
                x_center - bar_w / 2, y_top,
                x_center + bar_w / 2, top + plot_h,
                fill=color, outline="",
            )
            if scale > 0.55:
                canvas.create_text(
                    x_center, y_top - 8, text=f"{item['percent']}%",
                    font=font(8, mono=True), fill=theme.TEXT_SECONDARY,
                )
            label_step = max(1, count // 10)
            if index % label_step == 0 or index == count - 1:
                canvas.create_text(
                    x_center, top + plot_h + 16,
                    text=item["label"] if count <= 14 else item["date"][5:],
                    font=font(8), fill=theme.TEXT_MUTED,
                )
