# -*- coding: utf-8 -*-
"""Безопасность: хэширование паролей и проверка вводимых значений.

Пароли НЕ хранятся в открытом виде: для каждого пользователя генерируется
соль, затем PBKDF2-HMAC-SHA256 с 210 000 итераций. Сравнение идёт через
hmac.compare_digest, чтобы не было утечки по времени ответа.
"""

import datetime
import hashlib
import hmac
import os
import re

ITERATIONS = 210_000


def hash_password(password):
    """Вернуть (хэш, соль) в hexadecimal."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS
    )
    return digest.hex(), salt.hex()


def verify_password(password, stored_hash, salt):
    """Проверить пароль по сохранённому хэшу и соли."""
    try:
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS
        )
        return hmac.compare_digest(digest.hex(), stored_hash)
    except (ValueError, TypeError):
        return False


def require_text(value, field, min_len=1, max_len=120):
    """Непустой текст заданной длины."""
    value = (value or "").strip()
    if len(value) < min_len:
        raise ValueError(f"Поле «{field}» не может быть пустым")
    if len(value) > max_len:
        raise ValueError(f"Поле «{field}» слишком длинное (максимум {max_len})")
    return value


def require_username(value):
    """Логин: 3–20 символов, латиница, цифры, точка, дефис, подчёркивание."""
    value = require_text(value, "Логин", 3, 20)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError("Логин: только латинские буквы, цифры и символы _ . -")
    return value


def require_password(value):
    """Пароль: не короче 6 символов."""
    value = (value or "").strip()
    if len(value) < 6:
        raise ValueError("Пароль должен содержать минимум 6 символов")
    if len(value) > 100:
        raise ValueError("Пароль слишком длинный")
    return value


def require_int(value, field, minimum, maximum):
    """Целое число в заданном диапазоне."""
    text = str(value or "").strip()
    try:
        number = int(text)
    except ValueError:
        raise ValueError(f"Поле «{field}» должно быть целым числом") from None
    if not minimum <= number <= maximum:
        raise ValueError(f"Поле «{field}»: допустимо от {minimum} до {maximum}")
    return number


def require_date(value, field="Дата"):
    """Дата в формате ГГГГ-ММ-ДД."""
    text = (value or "").strip()
    try:
        return datetime.date.fromisoformat(text).isoformat()
    except ValueError:
        raise ValueError(f"Поле «{field}»: нужен формат ГГГГ-ММ-ДД") from None


def require_phone(value):
    """Телефон: необязательный '+', цифры, пробелы, скобки и дефисы."""
    value = require_text(value, "Телефон", 7, 25)
    if not re.fullmatch(r"\+?[0-9 ()\-]+", value):
        raise ValueError("Телефон содержит недопустимые символы")
    return value
