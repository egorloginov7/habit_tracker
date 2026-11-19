# -*- coding: utf-8 -*-
"""Бизнес-логика приложения: CRUD, поиск, фильтры, расчёты и отчёты.

Страницы не пишут SQL напрямую — всё проходит через этот слой.
Благодаря этому одну и ту же логику используют обычный и административный
интерфейсы, а также выгрузки отчётов.
"""

import datetime

from db import execute, query
from security import hash_password, verify_password

TODAY = lambda: datetime.date.today().isoformat()

HABIT_SORTS = {
    "name": "h.name COLLATE NOCASE",
    "category": "c.name COLLATE NOCASE",
    "done": "done_days DESC",
}
GOAL_SORTS = {
    "name": "g.title COLLATE NOCASE",
    "progress": "progress DESC",
    "deadline": "g.deadline",
}


# --- Авторизация ---------------------------------------------------------

def authenticate(username, password):
    """Вернуть строку пользователя или None, если логин/пароль неверны."""
    user = query("SELECT * FROM users WHERE username = ?", (username,), one=True)
    if user and verify_password(password, user["password_hash"], user["salt"]):
        return user
    return None


def get_user(user_id):
    return query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)


# --- Привычки ------------------------------------------------------------

def habits_list(user_id, search="", category_id=0, sort="name", all_users=False):
    """Список привычек с фильтрацией и сортировкой."""
    sql = """
        SELECT h.*, c.name AS category_name, c.color AS category_color,
               (SELECT COUNT(*) FROM habit_logs l
                WHERE l.habit_id = h.id AND l.done = 1) AS done_days,
               (SELECT l.done FROM habit_logs l
                WHERE l.habit_id = h.id AND l.log_date = ?) AS today_done,
               u.username
        FROM habits h
        JOIN categories c ON c.id = h.category_id
        JOIN users u ON u.id = h.user_id
        WHERE 1 = 1
    """
    params = [TODAY()]
    if not all_users:
        sql += " AND h.user_id = ?"
        params.append(user_id)
    if search:
        sql += " AND (LOWER(h.name) LIKE ? OR LOWER(h.description) LIKE ?)"
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])
    if category_id:
        sql += " AND h.category_id = ?"
        params.append(category_id)
    sql += " ORDER BY " + HABIT_SORTS.get(sort, HABIT_SORTS["name"])
    return query(sql, params)


def get_habit(habit_id):
    return query("SELECT * FROM habits WHERE id = ?", (habit_id,), one=True)


def add_habit(user_id, category_id, name, description):
    return execute(
        "INSERT INTO habits (user_id, category_id, name, description, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, category_id, name, description, TODAY()),
    )


def update_habit(habit_id, category_id, name, description):
    execute(
        "UPDATE habits SET category_id = ?, name = ?, description = ? WHERE id = ?",
        (category_id, name, description, habit_id),
    )


def delete_habit(habit_id):
    execute("DELETE FROM habits WHERE id = ?", (habit_id,))


def mark_habit(habit_id, done, day=None):
    """UPSERT отметки выполнения за конкретный день."""
    day = day or TODAY()
    execute(
        "INSERT INTO habit_logs (habit_id, log_date, done) VALUES (?, ?, ?) "
        "ON CONFLICT(habit_id, log_date) DO UPDATE SET done = excluded.done",
        (habit_id, day, 1 if done else 0),
    )


def habit_streak(habit_id):
    """Серия дней подряд с отметкой (считая от сегодня или вчерашнего дня)."""
    rows = query(
        "SELECT log_date FROM habit_logs WHERE habit_id = ? AND done = 1 "
        "ORDER BY log_date DESC",
        (habit_id,),
    )
    dates = {datetime.date.fromisoformat(row["log_date"]) for row in rows}
    cursor = datetime.date.today()
    if cursor not in dates:
        cursor -= datetime.timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= datetime.timedelta(days=1)
    return streak


# --- Цели ----------------------------------------------------------------

def goals_list(user_id, search="", category_id=0, sort="name", status="all",
               all_users=False):
    """Список целей с последним значением прогресса."""
    sql = """
        SELECT g.*, c.name AS category_name, c.color AS category_color,
               COALESCE((SELECT p.progress FROM goal_progress p
                         WHERE p.goal_id = g.id ORDER BY p.id DESC LIMIT 1), 0) AS progress,
               (SELECT COUNT(*) FROM goal_progress p WHERE p.goal_id = g.id) AS updates_count,
               u.username
        FROM goals g
        JOIN categories c ON c.id = g.category_id
        JOIN users u ON u.id = g.user_id
        WHERE 1 = 1
    """
    params = []
    if not all_users:
        sql += " AND g.user_id = ?"
        params.append(user_id)
    if search:
        sql += " AND (LOWER(g.title) LIKE ? OR LOWER(g.description) LIKE ?)"
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])
    if category_id:
        sql += " AND g.category_id = ?"
        params.append(category_id)
    if status == "done":
        sql += " AND COALESCE((SELECT p.progress FROM goal_progress p WHERE p.goal_id=g.id "
        sql += "ORDER BY p.id DESC LIMIT 1), 0) >= 70"
    elif status == "active":
        sql += " AND COALESCE((SELECT p.progress FROM goal_progress p WHERE p.goal_id=g.id "
        sql += "ORDER BY p.id DESC LIMIT 1), 0) < 70"
    sql += " ORDER BY " + GOAL_SORTS.get(sort, GOAL_SORTS["name"])
    return query(sql, params)


def get_goal(goal_id):
    return query("SELECT * FROM goals WHERE id = ?", (goal_id,), one=True)


def add_goal(user_id, category_id, title, description, target_value, deadline):
    return execute(
        "INSERT INTO goals (user_id, category_id, title, description, "
        "target_value, deadline) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, category_id, title, description, target_value, deadline),
    )


def update_goal(goal_id, category_id, title, description, target_value, deadline):
    execute(
        "UPDATE goals SET category_id=?, title=?, description=?, "
        "target_value=?, deadline=? WHERE id=?",
        (category_id, title, description, target_value, deadline, goal_id),
    )


def delete_goal(goal_id):
    execute("DELETE FROM goals WHERE id = ?", (goal_id,))


def set_goal_progress(goal_id, progress, note):
    execute(
        "INSERT INTO goal_progress (goal_id, progress, note, updated_at) "
        "VALUES (?, ?, ?, ?)",
        (goal_id, progress, note, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


def goal_history(goal_id):
    return query(
        "SELECT * FROM goal_progress WHERE goal_id = ? ORDER BY id DESC",
        (goal_id,),
    )


# --- Справочники и пользователи -----------------------------------------

def categories_list():
    return query("SELECT * FROM categories ORDER BY name COLLATE NOCASE")


def add_category(name, color):
    return execute("INSERT INTO categories (name, color) VALUES (?, ?)", (name, color))


def update_category(category_id, name, color):
    execute("UPDATE categories SET name=?, color=? WHERE id=?",
            (name, color, category_id))


def delete_category(category_id):
    execute("DELETE FROM categories WHERE id = ?", (category_id,))


def users_list():
    return query(
        "SELECT u.*, r.name AS role_name FROM users u "
        "JOIN roles r ON r.id = u.role_id ORDER BY u.id"
    )


def add_user(username, password, role_id, full_name):
    password_hash, salt = hash_password(password)
    return execute(
        "INSERT INTO users (username, password_hash, salt, role_id, full_name, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (username, password_hash, salt, role_id, full_name,
         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


def update_user(user_id, username, role_id, full_name, password=None):
    if password:
        password_hash, salt = hash_password(password)
        execute(
            "UPDATE users SET username=?, role_id=?, full_name=?, "
            "password_hash=?, salt=? WHERE id=?",
            (username, role_id, full_name, password_hash, salt, user_id),
        )
    else:
        execute(
            "UPDATE users SET username=?, role_id=?, full_name=? WHERE id=?",
            (username, role_id, full_name, user_id),
        )


def delete_user(user_id):
    execute("DELETE FROM users WHERE id = ?", (user_id,))


# --- Статистика и расчёты ------------------------------------------------

def dashboard_stats(user_id, is_admin=False):
    habits_count = query(
        "SELECT COUNT(*) AS n FROM habits" if is_admin else
        "SELECT COUNT(*) AS n FROM habits WHERE user_id=?",
        () if is_admin else (user_id,), one=True,
    )["n"]
    done_today = query(
        """SELECT COUNT(*) AS n FROM habit_logs l
           JOIN habits h ON h.id = l.habit_id
           WHERE l.done = 1 AND l.log_date = ?"""
        + ("" if is_admin else " AND h.user_id = ?"),
        (TODAY(),) if is_admin else (TODAY(), user_id), one=True,
    )["n"]
    goals_count = query(
        "SELECT COUNT(*) AS n FROM goals" if is_admin else
        "SELECT COUNT(*) AS n FROM goals WHERE user_id=?",
        () if is_admin else (user_id,), one=True,
    )["n"]
    avg_progress = query(
        """SELECT COALESCE(ROUND(AVG(progress)), 0) AS n FROM goal_progress p
           WHERE p.id IN (SELECT MAX(id) FROM goal_progress GROUP BY goal_id)"""
        + ("" if is_admin else
           " AND p.goal_id IN (SELECT id FROM goals WHERE user_id=?)"),
        () if is_admin else (user_id,), one=True,
    )["n"]
    return {
        "habits": habits_count,
        "done_today": done_today,
        "goals": goals_count,
        "avg_progress": avg_progress,
    }


def weekly_progress(user_id, days=7, is_admin=False):
    """Процент выполненных привычек по дням."""
    where = "" if is_admin else " AND h.user_id = ?"
    params = () if is_admin else (user_id,)
    total = query(
        "SELECT COUNT(*) AS n FROM habits h WHERE 1=1" + where, params, one=True,
    )["n"]
    result = []
    for offset in range(days - 1, -1, -1):
        day = datetime.date.today() - datetime.timedelta(days=offset)
        row = query(
            """SELECT COUNT(*) AS n FROM habit_logs l
               JOIN habits h ON h.id = l.habit_id
               WHERE l.log_date = ? AND l.done = 1""" + where,
            (day.isoformat(),) + params, one=True,
        )
        percent = round(row["n"] * 100 / total) if total else 0
        result.append({
            "date": day.isoformat(),
            "label": day.strftime("%d.%m"),
            "weekday": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][day.weekday()],
            "percent": percent,
        })
    return result


def recent_actions(limit=6, user_id=None, is_admin=False):
    sql = (
        "SELECT a.*, u.full_name, u.username FROM action_logs a "
        "LEFT JOIN users u ON u.id = a.user_id WHERE 1=1"
    )
    params = []
    if not is_admin and user_id:
        sql += " AND a.user_id = ?"
        params.append(user_id)
    sql += " ORDER BY a.id DESC LIMIT ?"
    params.append(limit)
    return query(sql, params)


def action_logs_list(search="", user_id=0, limit=200):
    sql = (
        "SELECT a.*, COALESCE(u.full_name, '—') AS full_name FROM action_logs a "
        "LEFT JOIN users u ON u.id = a.user_id WHERE 1=1"
    )
    params = []
    if search:
        sql += " AND (LOWER(a.action) LIKE ? OR LOWER(a.details) LIKE ?)"
        params.extend([f"%{search.lower()}%"] * 2)
    if user_id:
        sql += " AND a.user_id = ?"
        params.append(user_id)
    sql += " ORDER BY a.id DESC LIMIT ?"
    params.append(limit)
    return query(sql, params)


# --- Сквозной поиск ------------------------------------------------------

def normalize_search_text(text):
    """Привести поисковую строку к единому виду: обрезка + нижний регистр."""
    return (text or "").strip().lower()


def global_search(text, is_admin=False):
    """Искать одновременно в привычках, целях, справочниках и (для админа)
    пользователях и журнале. Возвращает список для перехода."""
    text = normalize_search_text(text)
    if len(text) < 2:
        return []
    like = f"%{text}%"
    found = []

    for row in habits_list(0, search=text, all_users=True):
        found.append({
            "type": "Привычка", "title": row["name"],
            "subtitle": row["category_name"] + " · " + (row["username"] or ""),
            "page": "Привычки", "id": row["id"],
        })
    for row in goals_list(0, search=text, all_users=True):
        found.append({
            "type": "Цель", "title": row["title"],
            "subtitle": f"{row['category_name']} · {row['progress']}%",
            "page": "Цели", "id": row["id"],
        })
    for row in categories_list():
        if text.lower() in row["name"].lower():
            found.append({
                "type": "Справочник", "title": row["name"],
                "subtitle": "Категория", "page": "Администрирование", "id": row["id"],
            })
    if is_admin:
        for row in query(
            "SELECT * FROM users WHERE LOWER(username) LIKE ? OR "
            "LOWER(full_name) LIKE ?", (like, like)
        ):
            found.append({
                "type": "Пользователь", "title": row["full_name"],
                "subtitle": "@" + row["username"],
                "page": "Администрирование", "id": row["id"],
            })
        for row in query(
            "SELECT * FROM action_logs WHERE LOWER(action) LIKE ? OR "
            "LOWER(details) LIKE ? ORDER BY id DESC LIMIT 20", (like, like)
        ):
            found.append({
                "type": "Журнал", "title": row["action"],
                "subtitle": row["details"] + " · " + row["created_at"],
                "page": "Журнал действий", "id": row["id"],
            })
    return found[:50]


# --- Отчёты --------------------------------------------------------------

def report_habits(user_id, is_admin=False):
    """Данные отчёта «Выполнение привычек»."""
    rows = habits_list(user_id, sort="name", all_users=is_admin)
    result = []
    for row in rows:
        days = query(
            "SELECT COUNT(*) AS n FROM habit_logs WHERE habit_id = ?",
            (row["id"],), one=True,
        )["n"]
        done = row["done_days"]
        percent = round(done * 100 / days) if days else 0
        result.append([
            row.get("username", ""), row["name"], row["category_name"],
            days, done, f"{percent}%", habit_streak(row["id"]),
        ])
    return (
        ["Пользователь", "Привычка", "Категория", "Дней в истории",
         "Выполнено", "Процент", "Серия (дней)"],
        result,
    )


def report_goals(user_id, is_admin=False):
    """Данные отчёта «Прогресс целей» (включает расчёт статуса)."""
    rows = goals_list(user_id, sort="name", all_users=is_admin)
    result = []
    for row in rows:
        progress = row["progress"]
        status = "Завершено" if progress >= 100 else (
            "Почти готово" if progress >= 70 else "В работе"
        )
        result.append([
            row.get("username", ""), row["title"], row["category_name"],
            row["target_value"], row["deadline"], f"{progress}%", status,
        ])
    return (
        ["Пользователь", "Цель", "Категория", "Целевое значение",
         "Дедлайн", "Прогресс", "Статус"],
        result,
    )
