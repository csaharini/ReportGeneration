"""Read and maintain the reusable standards and clause library."""
import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor


class StandardsLibraryError(RuntimeError):
    """Raised when the standards library cannot be reached."""


class StandardsValidationError(ValueError):
    """Raised for invalid manual standards-library entries."""


def _setting(name, auth_name, default=""):
    return os.getenv(name, os.getenv(auth_name, default))


def _settings():
    return {
        "host": _setting("STANDARDS_DB_HOST", "AUTH_DB_HOST", "127.0.0.1"),
        "port": int(_setting("STANDARDS_DB_PORT", "AUTH_DB_PORT", "3306")),
        "user": _setting("STANDARDS_DB_USER", "AUTH_DB_USER", "root"),
        "password": _setting("STANDARDS_DB_PASSWORD", "AUTH_DB_PASSWORD", ""),
        "database": _setting("STANDARDS_DB_NAME", "AUTH_DB_NAME", "csareport"),
    }


@contextmanager
def _connection():
    try:
        connection = pymysql.connect(
            **_settings(),
            cursorclass=DictCursor,
            connect_timeout=8,
            read_timeout=8,
            write_timeout=8,
            autocommit=False,
        )
    except pymysql.MySQLError as exc:
        raise StandardsLibraryError("The standards library is unavailable.") from exc
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _required(payload, name, label, limit):
    value = str(payload.get(name) or "").strip()
    if not value:
        raise StandardsValidationError(f"{label} is required.")
    if len(value) > limit:
        raise StandardsValidationError(f"{label} must be {limit} characters or fewer.")
    return value


def _optional(payload, name, label, limit):
    value = str(payload.get(name) or "").strip()
    if len(value) > limit:
        raise StandardsValidationError(f"{label} must be {limit} characters or fewer.")
    return value or None


def _optional_int(payload, name, label):
    value = payload.get(name)
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise StandardsValidationError(f"{label} must be a whole number.") from exc
    if number < 0 or number > 2_147_483_647:
        raise StandardsValidationError(f"{label} is outside the allowed range.")
    return number


def list_standards():
    """Return the compact data needed to populate the standard dropdown."""
    sql = """
        SELECT id, code, edition_year, title
        FROM standards
        ORDER BY code ASC, edition_year ASC, title ASC
    """
    try:
        with _connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
    except pymysql.MySQLError as exc:
        raise StandardsLibraryError("The standards library is unavailable.") from exc


def _summary_values(row):
    """Add the exact two values consumed by the Summary of Compliance table."""
    item = dict(row)
    code = str(item.get("standard_code") or item.get("code") or "").strip()
    clause_no = str(item.get("clause_no") or "").strip()
    title = str(item.get("title") or "").strip()
    # The report summary separates the reference from its requirement: the
    # Standard column receives the standard code and clause number; the
    # Compliance requirement column receives the clause title and the saved
    # requirement text. These values come only from the two library tables.
    item["summary_standard"] = " - ".join(part for part in (code, clause_no) if part)
    requirement_text = str(item.get("requirement_text") or "").strip()
    item["summary_requirement"] = "\n".join(part for part in (title, requirement_text) if part)
    return item


def list_clauses(standard_id):
    """Return clauses with the exact values required by the report summary."""
    try:
        standard_id = int(standard_id)
    except (TypeError, ValueError) as exc:
        raise StandardsValidationError("Invalid standard.") from exc
    if standard_id < 1:
        raise StandardsValidationError("Invalid standard.")
    sql = """
        SELECT
            c.id, c.standard_id, c.clause_no, c.title, c.requirement_text,
            c.formula_expr, c.min_atm_kg, c.max_atm_kg,
            s.code AS standard_code, s.edition_year, s.title AS standard_title
        FROM standard_clauses AS c
        INNER JOIN standards AS s ON s.id = c.standard_id
        WHERE c.standard_id = %s
        ORDER BY c.clause_no ASC, c.title ASC
    """
    try:
        with _connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (standard_id,))
                return [_summary_values(row) for row in cursor.fetchall()]
    except pymysql.MySQLError as exc:
        raise StandardsLibraryError("The standards library is unavailable.") from exc


def save_manual_entry(payload):
    """Upsert a manually entered standard and clause using the table unique keys."""
    if not isinstance(payload, dict):
        raise StandardsValidationError("Invalid standards-library entry.")
    code = _required(payload, "code", "Standard code", 50)
    edition_year = _required(payload, "edition_year", "Edition", 20)
    standard_title = _required(payload, "standard_title", "Standard title", 255)
    clause_no = _required(payload, "clause_no", "Clause number", 30)
    clause_title = _required(payload, "clause_title", "Clause title", 255)
    requirement_text = _optional(payload, "requirement_text", "Compliance requirement", 20_000)
    formula_expr = _optional(payload, "formula_expr", "Formula", 255)
    min_atm_kg = _optional_int(payload, "min_atm_kg", "Minimum ATM")
    max_atm_kg = _optional_int(payload, "max_atm_kg", "Maximum ATM")

    standard_sql = """
        INSERT INTO standards (code, edition_year, title)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id), title = VALUES(title)
    """
    clause_sql = """
        INSERT INTO standard_clauses
            (standard_id, clause_no, title, requirement_text, formula_expr, min_atm_kg, max_atm_kg)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            title = VALUES(title),
            requirement_text = VALUES(requirement_text),
            formula_expr = VALUES(formula_expr),
            min_atm_kg = VALUES(min_atm_kg),
            max_atm_kg = VALUES(max_atm_kg)
    """
    try:
        with _connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(standard_sql, (code, edition_year, standard_title))
                standard_id = cursor.lastrowid
                cursor.execute(clause_sql, (standard_id, clause_no, clause_title, requirement_text, formula_expr, min_atm_kg, max_atm_kg))
                clause_id = cursor.lastrowid
                cursor.execute("SELECT id, code, edition_year, title FROM standards WHERE id = %s", (standard_id,))
                standard = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT
                        c.id, c.standard_id, c.clause_no, c.title, c.requirement_text,
                        c.formula_expr, c.min_atm_kg, c.max_atm_kg,
                        s.code AS standard_code, s.edition_year, s.title AS standard_title
                    FROM standard_clauses AS c
                    INNER JOIN standards AS s ON s.id = c.standard_id
                    WHERE c.id = %s
                    """,
                    (clause_id,),
                )
                clause = _summary_values(cursor.fetchone())
    except pymysql.MySQLError as exc:
        raise StandardsLibraryError("The standards library could not be saved.") from exc
    return {"standard": standard, "clause": clause}
