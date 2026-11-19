# -*- coding: utf-8 -*-
"""Переиспользуемые элементы интерфейса с анимациями.

Все анимации сделаны на стандартном tkinter через after() — без external
библиотек. Три обязательных вида:
  1. анимация кнопок (плавная подсветка при наведении и «нажатие»);
  2. анимация объектов (рост прогресс-баров, появление уведомлений,
     движение индикатора в боковом меню — в main_window.py);
  3. анимация фона (AnimatedBackground работает сам, без пользователя).
"""

import math
import tkinter as tk

import theme
from theme import font, hex_color, mix, rgb


class Card(tk.Frame):
    """Белая карточка с рамкой; контент кладётся в `card.body`."""

    def __init__(self, master, padx=20, pady=18, bg=None, **kwargs):
        super().__init__(
            master, bg=bg or theme.CARD_BG,
            highlightbackground=theme.CARD_BORDER,
            highlightthickness=1, **kwargs,
        )
        self.body = tk.Frame(self, bg=bg or theme.CARD_BG)
        self.body.pack(fill="both", expand=True, padx=padx, pady=pady)


class AnimatedButton(tk.Button):
    """Кнопка с плавной подсветкой при наведении и анимацией нажатия."""

    def __init__(self, master, text, command=None, color=None, hover=None,
                 press=None, size=10, width=None, **kwargs):
        self._base = color or theme.ACCENT
        self._hover = hover or theme.ACCENT_HOVER
        self._press = press or theme.ACCENT_PRESS
        self._current = self._base
        self._job = None
        self._inside = False

        super().__init__(
            master,
            text=text,
            command=command,
            bg=self._base,
            fg="#FFFFFF",
            activebackground=self._base,
            activeforeground="#FFFFFF",
            font=font(size, bold=True),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=16,
            pady=7,
            width=width,
            **kwargs,
        )
        self.bind("<Enter>", lambda _e: self._on_enter())
        self.bind("<Leave>", lambda _e: self._on_leave())
        self.bind("<ButtonPress>", lambda _e: self._on_press())
        self.bind("<ButtonRelease>", lambda _e: self._on_release())
        self.bind("<FocusIn>", lambda _e: self._on_enter())
        self.bind("<FocusOut>", lambda _e: self._on_leave())

    # --- анимация цвета ---
    def _animate(self, target, duration=150, steps=8):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except (ValueError, tk.TclError):
                pass
        start, end = rgb(self._current), rgb(target)
        step = [0]

        def tick():
            step[0] += 1
            t = step[0] / steps
            self._current = hex_color(
                [start[i] + (end[i] - start[i]) * t for i in range(3)]
            )
            self.configure(bg=self._current, activebackground=self._current)
            if step[0] < steps:
                self._job = self.after(max(8, duration // steps), tick)
            else:
                self._job = None

        tick()

    def set_colors(self, base, hover, press):
        """Сменить цветовую схему кнопки (например, на зелёную «Готово»)."""
        self._base, self._hover, self._press = base, hover, press
        self._animate(base, 180)

    def _on_enter(self):
        self._inside = True
        self._animate(self._hover)

    def _on_leave(self):
        self._inside = False
        self.configure(relief="flat")
        self._animate(self._base)

    def _on_press(self):
        self.configure(relief="sunken", bd=1)
        self._animate(self._press, 90, 4)  # быстрое «нажатие»

    def _on_release(self):
        self.configure(relief="flat", bd=0)
        self._animate(self._hover if self._inside else self._base, 180)


class SidebarButton(tk.Label):
    """Пункт бокового меню с подсветкой при наведении."""

    def __init__(self, master, text, command=None):
        super().__init__(
            master, text=text, bg=theme.SIDEBAR_BG,
            fg=theme.TEXT_ON_DARK_MUTED, font=font(11),
            anchor="w", padx=18, pady=12, cursor="hand2",
        )
        self._command = command
        self._active = False
        self.bind("<Button-1>", lambda _e: self._invoke())
        self.bind("<Enter>", lambda _e: self._hover(True))
        self.bind("<Leave>", lambda _e: self._hover(False))

    def _invoke(self):
        if self._command:
            self._command()

    def _hover(self, inside):
        if not self._active:
            self.configure(bg=theme.SIDEBAR_HOVER if inside else theme.SIDEBAR_BG)

    def set_active(self, active):
        self._active = active
        self.configure(
            bg=theme.SIDEBAR_ACTIVE if active else theme.SIDEBAR_BG,
            fg="#FFFFFF" if active else theme.TEXT_ON_DARK_MUTED,
            font=font(11, bold=active),
        )


class StatCard(Card):
    """Карточка с числом и подписью."""

    def __init__(self, master, title, value="—", subtitle="", accent=None):
        super().__init__(master, padx=18, pady=16)
        tk.Label(
            self.body, text=title, bg=theme.CARD_BG,
            fg=theme.TEXT_SECONDARY, font=font(10),
        ).pack(anchor="w")
        self._value = tk.Label(
            self.body, text=value, bg=theme.CARD_BG,
            fg=accent or theme.ACCENT, font=font(22, bold=True),
        )
        self._value.pack(anchor="w", pady=(8, 0))
        self._subtitle = None
        if subtitle:
            self._subtitle = tk.Label(
                self.body, text=subtitle, bg=theme.CARD_BG,
                fg=theme.TEXT_SECONDARY, font=font(9),
            )
            self._subtitle.pack(anchor="w", pady=(4, 0))

    def set_value(self, value):
        self._value.configure(text=value)

    def set_subtitle(self, value):
        if self._subtitle is None:
            self._subtitle = tk.Label(
                self.body, text="", bg=theme.CARD_BG,
                fg=theme.TEXT_SECONDARY, font=font(9),
            )
            self._subtitle.pack(anchor="w", pady=(4, 0))
        self._subtitle.configure(text=value)


class ProgressBar(tk.Canvas):
    """Полоса прогресса, которая «вырастает» до нужного значения."""

    def __init__(self, master, height=12, color=None, **kwargs):
        super().__init__(
            master, height=height, bg=theme.CARD_BG,
            highlightthickness=0, **kwargs,
        )
        self._height = height
        self._color = color or theme.ACCENT
        self._current = 0
        self._target = 0
        self._job = None
        self.bind("<Configure>", lambda _e: self._render())

    def set(self, percent, animate=True):
        self._target = max(0, min(100, percent))
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except (ValueError, tk.TclError):
                pass
        if not animate:
            self._current = self._target
            self._render()
            return
        step = (self._target - self._current) / 10
        for part in range(10):
            self.after(part * 18, lambda v=self._current + step * (part + 1): self._set_and_draw(v))
        self.after(10 * 18, lambda: self._set_and_draw(self._target))

    def _set_and_draw(self, value):
        self._current = value
        self._render()

    def _render(self):
        self.delete("all")
        width = max(self.winfo_width(), 2)
        self.create_rectangle(0, 0, width, self._height, fill=theme.TRACK_BG, width=0)
        fill = round(width * self._current / 100)
        if fill > 0:
            self.create_rectangle(0, 0, fill, self._height, fill=self._color, width=0)


class AnimatedBackground(tk.Canvas):
    """Фон с медленно движущимися мягкими пятнами — работает сам.

    Используется и в окне входа, и на главной странице. Никаких событий
    от пользователя не требуется: цикл запускается методом start().
    """

    def __init__(self, master, base=None, blobs=None, interval=60, **kwargs):
        super().__init__(
            master, bg=base or theme.BG,
            highlightthickness=0, bd=0, **kwargs,
        )
        self._base = base or theme.BG
        self._blobs = blobs or [
            (theme.ACCENT_SOFT, 0.35, 0.6, 0.0009, 0.0),
            (theme.SUCCESS_SOFT, 0.30, 0.8, 0.0013, 2.1),
            ("#EDE9FE", 0.28, 0.5, 0.0011, 4.0),
            (theme.WARNING_SOFT, 0.25, 0.7, 0.0007, 1.2),
        ]
        self._interval = interval
        self._tick_count = 0
        self._running = False
        self._job = None
        self.bind("<Configure>", lambda _e: self._draw())

    def start(self):
        if not self._running:
            self._running = True
            self._tick()

    def stop(self):
        self._running = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except (ValueError, tk.TclError):
                pass
            self._job = None

    def _tick(self):
        self._tick_count += 1
        self._draw()
        if self._running:
            self._job = self.after(self._interval, self._tick)

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        self.delete("all")

        # Мягкий вертикальный градиент полосами
        bands = max(12, h // 8)
        for index in range(bands):
            t = index / bands
            color = mix(self._base, "#FFFFFF", 0.55 * (1 - t))
            self.create_rectangle(
                0, h * index / bands, w, h * (index + 1) / bands + 1,
                fill=color, outline="",
            )

        # Пятна, движущиеся по синусоиде
        for color, radius_part, amplitude, speed, phase in self._blobs:
            radius = max(20, min(w, h) * radius_part)
            cx = w * (0.5 + amplitude * 0.5 * math.sin(self._tick_count * speed + phase))
            cy = h * (0.5 + amplitude * 0.5 * math.cos(self._tick_count * speed * 0.8 + phase))
            for ring in range(4, 0, -1):
                r = radius * ring / 4
                shade = mix(self._base, color, 0.55 / ring)
                self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=shade, outline="")


class Toast(tk.Toplevel):
    """Небольшое уведомление, которое само исчезает с анимацией."""

    def __init__(self, master, message, color=theme.SUCCESS):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        frame = tk.Frame(self, bg=color, padx=18, pady=10)
        frame.pack()
        tk.Label(
            frame, text=message, bg=color, fg="#FFFFFF", font=font(10, bold=True),
        ).pack()

        self.update_idletasks()
        parent_x = master.winfo_rootx()
        parent_y = master.winfo_rooty()
        parent_w = master.winfo_width()
        self.geometry(f"+{parent_x + parent_w // 2 - self.winfo_width() // 2}+{parent_y + 40}")

        self._alpha = 1.0
        self.after(1800, self._fade)

    def _fade(self):
        self._alpha -= 0.1
        if self._alpha <= 0:
            self.destroy()
        else:
            try:
                self.attributes("-alpha", self._alpha)
            except tk.TclError:
                pass
            self.after(80, self._fade)


def show_toast(master, message, color=theme.SUCCESS):
    """Показать уведомление (не блокирует работу)."""
    Toast(master, message, color)
