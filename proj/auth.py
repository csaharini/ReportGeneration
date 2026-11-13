"""Database-backed account authentication for the report studio."""
import os
import uuid
from contextlib import contextmanager
from email.utils import parseaddr
from pathlib import Path

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
        _ensure_schema(connection)
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
    return {"id": row["id"], "email": row["email"], "full_name": row["full_name"], "avatar_url": row["avatar_url"] if "avatar_url" in row.keys() else None, "initials": row["initials"] if "initials" in row.keys() else None}


def _ensure_schema(connection):
    """Add avatar_url and initials columns to users if they do not already exist."""
    with connection.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM users LIKE 'avatar_url'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) NULL AFTER full_name")
        cursor.execute("SHOW COLUMNS FROM users LIKE 'initials'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN initials VARCHAR(10) NULL AFTER avatar_url")


def _avatar_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.join(here, "uploads", "avatars")
    os.makedirs(directory, exist_ok=True)
    return directory


def upload_avatar(user_id: int, file_bytes: bytes, filename: str, content_type: str):
    """Save an uploaded avatar image to disk and store its URL in the database."""
    allowed = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
    if content_type not in allowed:
        raise AuthError("Only PNG, JPG, GIF, or WEBP images are allowed.")
    if len(file_bytes) > 2 * 1024 * 1024:
        raise AuthError("Avatar image must be smaller than 2 MB.")
    ext = Path(filename).suffix.lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        ext = ".png"
    stored_name = f"{user_id}_{uuid.uuid4().hex}{ext}"
    directory = _avatar_dir()
    stored_path = os.path.join(directory, stored_name)
    with open(stored_path, "wb") as f:
        f.write(file_bytes)
    avatar_url = f"/avatars/{stored_name}"
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET avatar_url = %s WHERE id = %s AND is_active = 1", (avatar_url, user_id))
            if cursor.rowcount == 0:
                raise AuthError("User not found or inactive.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, email, full_name, avatar_url, initials FROM users WHERE id = %s AND is_active = 1 LIMIT 1", (user_id,))
            row = cursor.fetchone()
    return _public_user(row) if row else None


def reset_password(user_id: int, current_password: str, new_password: str):
    """Verify the current password and replace it with a new one."""
    new_password = _validate_password(new_password)
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, full_name, is_active FROM users WHERE id = %s AND is_active = 1 LIMIT 1",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row or not row["password_hash"]:
                raise AuthError("User not found or inactive.")
            try:
                valid = bcrypt.checkpw(str(current_password or "").encode("utf-8"), row["password_hash"].encode("utf-8"))
            except ValueError:
                valid = False
            if not valid:
                raise AuthError("Current password is incorrect.")
            new_hash = bcrypt.hashpw(str(new_password).encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, email, full_name, avatar_url, initials FROM users WHERE id = %s AND is_active = 1 LIMIT 1", (user_id,))
            row = cursor.fetchone()
    return _public_user(row) if row else None


def update_user_profile(user_id: int, updates: dict):
    """Update a user's profile fields (full_name, email, avatar_url, initials)."""
    if not updates:
        return None
    allowed = {}
    if "full_name" in updates:
        name = str(updates["full_name"] or "").strip()
        if not 2 <= len(name) <= 160:
            raise AuthError("Full name must be between 2 and 160 characters.")
        allowed["full_name"] = name
    if "email" in updates:
        allowed["email"] = _normalise_email(updates["email"])
    if "avatar_url" in updates:
        allowed["avatar_url"] = str(updates["avatar_url"] or "").strip() or None
    if "initials" in updates:
        initials = str(updates["initials"] or "").strip().upper()
        if len(initials) > 5:
            raise AuthError("Initials must be 5 characters or fewer.")
        allowed["initials"] = initials
    if not allowed:
        return None
    set_clause = ", ".join(f"{key} = %s" for key in allowed)
    params = list(allowed.values()) + [user_id]
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = %s AND is_active = 1", params)
            if cursor.rowcount == 0:
                raise AuthError("User not found or inactive.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, email, full_name, avatar_url, initials FROM users WHERE id = %s AND is_active = 1 LIMIT 1", (user_id,))
            row = cursor.fetchone()
    return _public_user(row) if row else None


def create_user(full_name, email, password, initials=""):
    name = str(full_name or "").strip()
    if not 2 <= len(name) <= 160:
        raise AuthError("Full name must be between 2 and 160 characters.")
    email = _normalise_email(email)
    password = _validate_password(password)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    initials_value = str(initials or "").strip().upper() or None
    try:
        with _connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, full_name, initials, is_active) VALUES (%s, %s, %s, %s, 1)",
                    (email, password_hash, name, initials_value),
                )
                user_id = cursor.lastrowid
    except pymysql.err.IntegrityError as exc:
        if exc.args and exc.args[0] == 1062:
            raise AuthError("An account with this email already exists.") from exc
        raise AuthConfigurationError("The authentication service is unavailable.") from exc
    return {"id": user_id, "email": email, "full_name": name, "initials": initials_value}


def authenticate(email, password):
    email = _normalise_email(email)
    password = str(password or "")
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, full_name, initials, is_active FROM users WHERE email = %s LIMIT 1",
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
                "SELECT id, email, full_name, avatar_url, initials FROM users WHERE id = %s AND is_active = 1 LIMIT 1",
                (user_id,),
            )
            row = cursor.fetchone()
    return _public_user(row) if row else None
