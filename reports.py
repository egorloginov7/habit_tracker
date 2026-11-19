# -*- coding: utf-8 -*-
"""Отчёты в CSV и резервное копирование базы данных.

CSV пишется в кодировке UTF-8 с BOM: файл сразу корректно открывается
в Excel с кириллицей. Разделитель — ';'.
"""

import csv
import datetime
import os
from tkinter import filedialog, messagebox

import db
import services
from widgets import show_toast

REPORTS_DIR = os.path.join(db.BASE_DIR, "reports")


def _choose_path(parent, default_name):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return filedialog.asksaveasfilename(
        parent=parent,
        title="Сохранить отчёт",
        defaultextension=".csv",
        initialdir=REPORTS_DIR,
        initialfile=default_name,
        filetypes=[("CSV-файл", "*.csv"), ("Все файлы", "*.*")],
    )


def _write_csv(path, headers, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)


def export_habits_report(parent, user_id, is_admin=False):
    """Отчёт №1: выполнение привычек за всю историю."""
    path = _choose_path(
        parent, "habits_report_" + datetime.date.today().isoformat() + ".csv"
    )
    if not path:
        return None
    path = path.lstrip()
    headers, rows = services.report_habits(user_id, is_admin)
    _write_csv(path, headers, rows)
    db.log_action(
        user_id, "Выгрузка отчёта",
        f"Отчёт по привычкам: {len(rows)} записей -> {os.path.basename(path)}",
    )
    show_toast(parent, f"Отчёт сохранён: {os.path.basename(path)}")
    return path


def export_goals_report(parent, user_id, is_admin=False):
    """Отчёт №2: прогресс целей с расчётом статуса."""
    path = _choose_path(
        parent, "goals_report_" + datetime.date.today().isoformat() + ".csv"
    )
    if not path:
        return None
    headers, rows = services.report_goals(user_id, is_admin)
    _write_csv(path, headers, rows)
    db.log_action(
        user_id, "Выгрузка отчёта",
        f"Отчёт по целям: {len(rows)} записей -> {os.path.basename(path)}",
    )
    show_toast(parent, f"Отчёт сохранён: {os.path.basename(path)}")
    return path


def create_backup(parent, user_id):
    """Резервная копия БД через sqlite3.Connection.backup()."""
    try:
        path = db.backup_db()
    except OSError as exc:
        messagebox.showerror("Ошибка", f"Не удалось создать копию:\n{exc}", parent=parent)
        return None
    db.log_action(user_id, "Резервное копирование", os.path.basename(path))
    show_toast(parent, "Резервная копия БД создана")
    return path
