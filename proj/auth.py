"""Database-backed account authentication for the report studio."""
import os
from contextlib import contextmanager
from email.utils import parseaddr

import bcrypt
import pymysql
from pymysql.cursors import DictCursor


class AuthError(ValueError):
    """A safe, user-facing authentication error."""


class AuthConfigurationError(RuntimeError):
    """Raised when the authentication database connection is unavailable."""


def _settings():
    # Local phpMyAdmin installation defaults; production should always set these.
    return {
        "host": os.getenv("AUTH_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("AUTH_DB_PORT", "3306")),
        "user": os.getenv("AUTH_DB_USER", "root"),
        "password": os.getenv("AUTH_DB_PASSWORD", ""),
        "database": os.getenv("AUTH_DB_NAME", "csareport"),
    }


@contextmanager
def _connection():
    try:
        connection = pymysql.connect(
            **_settings(), cursorclass=DictCursor,
            connect_timeout=8, read_timeout=8, write_timeout=8, autocommit=True,
        )
    except pymysql.MySQLError as exc:
        raise AuthConfigurationError("The authentication service is unavailable.") from exc
    try:
        yield connection
    finally:
        connection.close()


def _normalise_email(value):
    email = str(value or "").strip().casefold()
    _, parsed = parseaddr(email)
    if parsed != email or "@" not in email or len(email) > 254:
        raise AuthError("Enter a valid email address.")
    return email


def _validate_password(value):
    password = str(value or "")
    byte_length = len(password.encode("utf-8"))
    if len(password) < 8:
        raise AuthError("Password must contain at least 8 characters.")
    if byte_length > 72:
        raise AuthError("Password is too long.")
    return password


def _public_user(row):
    return {"id": row["id"], "email": row["email"], "display_name": row["display_name"]}


def create_user(display_name, email, password):
    name = str(display_name or "").strip()
    if not 2 <= len(name) <= 160:
        raise AuthError("Display name must be between 2 and 160 characters.")
    email = _normalise_email(email)
    password = _validate_password(password)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        with _connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, display_name, is_active) VALUES (%s, %s, %s, 1)",
                    (email, password_hash, name),
                )
                user_id = cursor.lastrowid
    except pymysql.err.IntegrityError as exc:
        if exc.args and exc.args[0] == 1062:
            raise AuthError("An account with this email already exists.") from exc
        raise AuthConfigurationError("The authentication service is unavailable.") from exc
    return {"id": user_id, "email": email, "display_name": name}


def authenticate(email, password):
    email = _normalise_email(email)
    password = str(password or "")
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, display_name, is_active FROM users WHERE email = %s LIMIT 1",
                (email,),
            )
            row = cursor.fetchone()
            if not row or not row["password_hash"] or not row["is_active"]:
                raise AuthError("Email or password is incorrect.")
            try:
                valid = bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8"))
            except ValueError:
                valid = False
            if not valid:
                raise AuthError("Email or password is incorrect.")
            cursor.execute("UPDATE users SET last_login_at = UTC_TIMESTAMP(3) WHERE id = %s", (row["id"],))
    return _public_user(row)


def get_user(user_id):
    if not user_id:
        return None
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, display_name FROM users WHERE id = %s AND is_active = 1 LIMIT 1",
                (user_id,),
            )
            row = cursor.fetchone()
    return _public_user(row) if row else None
