# -*- coding: utf-8 -*-
"""SQLite-база данных: схема, тестовые данные, резервное копирование.

8 таблиц, между ними внешние ключи:
  roles ──< users ──< habits ──< habit_logs
                  └──< goals  ──< goal_progress
  users ──< action_logs
  categories ──< habits, categories ──< goals
"""

import datetime
import os
import random
import sqlite3
from contextlib import contextmanager

from security import hash_password

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "habit_tracker.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

SCHEMA = """
CREATE TABLE IF NOT EXISTS roles (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role_id       INTEGER NOT NULL REFERENCES roles(id),
    full_name     TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#2563EB'
);

CREATE TABLE IF NOT EXISTS habits (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS goals (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    target_value INTEGER NOT NULL DEFAULT 100,
    deadline     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id       INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    log_date TEXT NOT NULL,
    done     INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    UNIQUE (habit_id, log_date)
);

CREATE TABLE IF NOT EXISTS goal_progress (
    id         INTEGER PRIMARY KEY,
    goal_id    INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    progress   INTEGER NOT NULL CHECK (progress BETWEEN 0 AND 100),
    note       TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_logs (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT NOT NULL,
    details    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);
CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_habit_date ON habit_logs(habit_id, log_date);
CREATE INDEX IF NOT EXISTS idx_actions_created ON action_logs(created_at);
"""


@contextmanager
def db():
    """Контекстный менеджер соединения: сам коммитит и закрывает."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql, params=(), one=False):
    """SELECT-запрос, возвращает список словарей (или одну строку)."""
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = [dict(row) for row in rows]
    return result[0] if one and result else (None if one else result)


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE — вернуть id последней изменённой строки."""
    with db() as conn:
        cursor = conn.execute(sql, params)
        return cursor.lastrowid


def log_action(user_id, action, details=""):
    """Записать действие в журнал (для требования 9)."""
    execute(
        "INSERT INTO action_logs (user_id, action, details, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            user_id,
            action,
            details,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )


def init_db():
    """Создать структуру и при первом запуске залить тестовые данные."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA)
        empty = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        if empty:
            _seed(conn)


def _seed(conn):
    """Тестовые данные: 8 таблиц, более 250 записей."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.date.today()
    rnd = random.Random(42)

    conn.executemany(
        "INSERT INTO roles (id, name) VALUES (?, ?)",
        [(1, "admin"), (2, "user")],
    )

    users = []
    passwords = {
        "admin": "admin123",
        "user": "user123",
        "marina": "user123",
        "alex": "user123",
        "dmitry": "user123",
        "anna": "user123",
    }
    full_names = {
        "admin": "Администратор системы",
        "user": "Логинов Егор Андреевич",
        "marina": "Ковалёва Марина Сергеевна",
        "alex": "Смирнов Александр Павлович",
        "dmitry": "Орлов Дмитрий Ильич",
        "anna": "Белова Анна Викторовна",
    }
    for index, (username, password) in enumerate(passwords.items(), start=1):
        password_hash, salt = hash_password(password)
        role_id = 1 if username == "admin" else 2
        users.append((index, username, password_hash, salt, role_id,
                      full_names[username], now))
    conn.executemany(
        "INSERT INTO users (id, username, password_hash, salt, role_id, "
        "full_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        users,
    )

    categories = [
        (1, "Здоровье", "#10B981"),
        (2, "Обучение", "#2563EB"),
        (3, "Спорт", "#F59E0B"),
        (4, "Финансы", "#8B5CF6"),
        (5, "Творчество", "#EC4899"),
        (6, "Бытовое", "#64748B"),
    ]
    conn.executemany(
        "INSERT INTO categories (id, name, color) VALUES (?, ?, ?)",
        categories,
    )

    habit_names = [
        (1, "Пить воду", "8 стаканов в течение дня", 1),
        (2, "Зарядка", "15 минут упражнений после подъёма", 3),
        (3, "Чтение", "20 страниц перед сном", 2),
        (4, "Дневник", "Запись итогов дня", 5),
        (5, "Уборка", "10 минут на рабочем столе", 6),
        (6, "Бег", "3 км в спокойном темпе", 3),
        (7, "Английский", "30 новых слов", 2),
        (8, "Бюджет", "Учёт расходов за день", 4),
        (9, "Сон", "Лечь до 23:00", 1),
        (10, "Прогулка", "30 минут на свежем воздухе", 1),
        (11, "Йога", "Растяжка 20 минут", 3),
        (12, "Курс Python", "Одно занятие", 2),
        (13, "Рисование", "15 минут практики", 5),
        (14, "Планирование", "Список дел на завтра", 6),
    ]
    habits = []
    for habit_id, name, description, category_id in habit_names:
        user_id = 1 if habit_id <= 5 else 2 + (habit_id - 6) % 5
        habits.append((habit_id, user_id, category_id, name, description,
                       (today - datetime.timedelta(days=30)).isoformat()))
    conn.executemany(
        "INSERT INTO habits (id, user_id, category_id, name, description, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?)",
        habits,
    )

    # История выполнений: 14 привычек × 14 дней = 196 записей
    logs = []
    log_id = 1
    for habit_id in range(1, 15):
        for days_ago in range(14):
            day = (today - datetime.timedelta(days=days_ago)).isoformat()
            done = 1 if rnd.random() < 0.72 else 0
            logs.append((log_id, habit_id, day, done))
            log_id += 1
    conn.executemany(
        "INSERT INTO habit_logs (id, habit_id, log_date, done) "
        "VALUES (?, ?, ?, ?)",
        logs,
    )

    goal_data = [
        (1, 1, 2, "Прочитать 12 книг за год", "Одна книга в месяц", 12, 30),
        (2, 1, 3, "Пробежать 10 км без остановки", "Подготовка к забегу", 10, 90),
        (3, 1, 2, "Выучить 1000 английских слов", "По 30 слов в день", 1000, 60),
        (4, 1, 4, "Накопить 500 000", "Финансовая подушка", 500000, 365),
        (5, 2, 1, "Снизить вес на 5 кг", "Здоровый образ жизни", 5, 120),
        (6, 2, 2, "Пройти курс Python", "Практика каждый день", 100, 45),
        (7, 3, 5, "Нарисовать 30 скетчей", "Ежедневная практика", 30, 60),
        (8, 4, 3, "Сделать 100 отжиманий", "Пошаговая цель", 100, 90),
        (9, 5, 6, "Навести порядок в архиве", "Систематизация файлов", 100, 30),
        (10, 6, 2, "Изучить SQL", "Теория и практика", 100, 60),
    ]
    conn.executemany(
        "INSERT INTO goals (id, user_id, category_id, title, description, "
        "target_value, deadline) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (i, u, c, title, desc, target,
             (today + datetime.timedelta(days=days)).isoformat())
            for i, u, c, title, desc, target, days in goal_data
        ],
    )

    progress_rows = []
    progress_id = 1
    for goal_id in range(1, 11):
        for step, value in enumerate((rnd.randint(5, 20), rnd.randint(25, 70))):
            progress_rows.append((
                progress_id, goal_id, value,
                "Начало работы" if step == 0 else "Текущий результат",
                (today - datetime.timedelta(days=20 - step * 10)).isoformat(),
            ))
            progress_id += 1
    conn.executemany(
        "INSERT INTO goal_progress (id, goal_id, progress, note, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        progress_rows,
    )

    actions = [
        "Вход в систему", "Добавлена привычка", "Отметка выполнения",
        "Обновление цели", "Выгрузка отчёта", "Резервное копирование",
    ]
    conn.executemany(
        "INSERT INTO action_logs (user_id, action, details, created_at) "
        "VALUES (?, ?, ?, ?)",
        [
            (
                1 + index % 6,
                actions[index % len(actions)],
                f"Тестовая запись №{index + 1}",
                (today - datetime.timedelta(days=index % 10)).isoformat()
                + f" {8 + index % 10:02d}:{index % 60:02d}:00",
            )
            for index in range(30)
        ],
    )


def backup_db():
    """Создать резервную копию БД через штатный API sqlite3."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    filename = "backup_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".db"
    path = os.path.join(BACKUP_DIR, filename)
    source = sqlite3.connect(DB_PATH)
    target = sqlite3.connect(path)
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()
    return path


def table_counts():
    """Количество записей в каждой таблице — для раздела «О программе»."""
    tables = [
        "roles", "users", "categories", "habits",
        "goals", "habit_logs", "goal_progress", "action_logs",
    ]
    result = {}
    with db() as conn:
        for table in tables:
            result[table] = conn.execute(
                f"SELECT COUNT(*) FROM {table}"  # имена таблиц фиксированы в коде
            ).fetchone()[0]
    return result
