"""Read and maintain the reusable engineering-materials library."""
import os
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation

import pymysql
from pymysql.cursors import DictCursor


class MaterialsLibraryError(RuntimeError):
    """Raised when the materials library cannot be reached."""


class MaterialsValidationError(ValueError):
    """Raised for invalid material-library entries."""


def _setting(name, auth_name, default=""):
    return os.getenv(name, os.getenv(auth_name, default))


def _settings():
    return {
        "host": _setting("MATERIALS_DB_HOST", "AUTH_DB_HOST", "127.0.0.1"),
        "port": int(_setting("MATERIALS_DB_PORT", "AUTH_DB_PORT", "3306")),
        "user": _setting("MATERIALS_DB_USER", "AUTH_DB_USER", "root"),
        "password": _setting("MATERIALS_DB_PASSWORD", "AUTH_DB_PASSWORD", ""),
        "database": _setting("MATERIALS_DB_NAME", "AUTH_DB_NAME", "csareport"),
    }


@contextmanager
def _connection():
    try:
        connection = pymysql.connect(
            **_settings(), cursorclass=DictCursor,
            connect_timeout=8, read_timeout=8, write_timeout=8, autocommit=False,
        )
    except pymysql.MySQLError as exc:
        raise MaterialsLibraryError("The materials library is unavailable.") from exc
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _required_text(payload, name, label, limit):
    value = str(payload.get(name) or "").strip()
    if not value:
        raise MaterialsValidationError(f"{label} is required.")
    if len(value) > limit:
        raise MaterialsValidationError(f"{label} must be {limit} characters or fewer.")
    return value


def _optional_text(payload, name, label, limit):
    value = str(payload.get(name) or "").strip()
    if len(value) > limit:
        raise MaterialsValidationError(f"{label} must be {limit} characters or fewer.")
    return value or None


def _decimal(payload, name, label, required=False):
    raw = payload.get(name)
    if raw in (None, ""):
        if required:
            raise MaterialsValidationError(f"{label} is required.")
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MaterialsValidationError(f"{label} must be a number.") from exc
    if value < 0 or value > Decimal("999999.99"):
        raise MaterialsValidationError(f"{label} is outside the allowed range.")
    return value


def _optional_id(payload, name, label):
    value = payload.get(name)
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise MaterialsValidationError(f"{label} must be a whole number.") from exc
    if number < 1:
        raise MaterialsValidationError(f"{label} must be positive.")
    return number


def list_materials():
    """Return all report-ready material values for the picker."""
    sql = """
        SELECT id, grade, material_type, tensile_mpa, yield_mpa,
               youngs_modulus_gpa, poisson_ratio, density_kg_m3,
               source_standard_id, category, notes
        FROM materials
        ORDER BY category ASC, grade ASC
    """
    try:
        with _connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
    except pymysql.MySQLError as exc:
        raise MaterialsLibraryError("The materials library is unavailable.") from exc


def save_manual_material(payload):
    """Upsert a manual entry using the database's unique grade constraint."""
    if not isinstance(payload, dict):
        raise MaterialsValidationError("Invalid material-library entry.")
    grade = _required_text(payload, "grade", "Material grade", 50)
    material_type = _required_text(payload, "material_type", "Material type", 100)
    tensile_mpa = _decimal(payload, "tensile_mpa", "Tensile strength", required=True)
    yield_mpa = _decimal(payload, "yield_mpa", "Yield strength")
    youngs_modulus_gpa = _decimal(payload, "youngs_modulus_gpa", "Young's modulus")
    poisson_ratio = _decimal(payload, "poisson_ratio", "Poisson's ratio")
    density_kg_m3 = _decimal(payload, "density_kg_m3", "Density")
    source_standard_id = _optional_id(payload, "source_standard_id", "Source standard ID")
    category = str(payload.get("category") or "steel").strip().lower()
    if category not in {"steel", "weld_metal", "bolt"}:
        raise MaterialsValidationError("Category must be steel, weld metal, or bolt.")
    notes = _optional_text(payload, "notes", "Notes", 255)

    upsert = """
        INSERT INTO materials
            (grade, material_type, tensile_mpa, yield_mpa, youngs_modulus_gpa,
             poisson_ratio, density_kg_m3, source_standard_id, category, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id), material_type = VALUES(material_type),
            tensile_mpa = VALUES(tensile_mpa), yield_mpa = VALUES(yield_mpa),
            youngs_modulus_gpa = VALUES(youngs_modulus_gpa),
            poisson_ratio = VALUES(poisson_ratio), density_kg_m3 = VALUES(density_kg_m3),
            source_standard_id = VALUES(source_standard_id), category = VALUES(category),
            notes = VALUES(notes)
    """
    select = """
        SELECT id, grade, material_type, tensile_mpa, yield_mpa,
               youngs_modulus_gpa, poisson_ratio, density_kg_m3,
               source_standard_id, category, notes
        FROM materials WHERE id = %s
    """
    try:
        with _connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    upsert,
                    (grade, material_type, tensile_mpa, yield_mpa, youngs_modulus_gpa,
                     poisson_ratio, density_kg_m3, source_standard_id, category, notes),
                )
                material_id = cursor.lastrowid
                cursor.execute(select, (material_id,))
                return cursor.fetchone()
    except pymysql.MySQLError as exc:
        raise MaterialsLibraryError("The material could not be saved.") from exc
