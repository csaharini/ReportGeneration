"""Read-only lookup of report project details by RAE/subproject ID.

Database settings are deliberately read from the process environment so a
password is never stored in the application source or committed with it.
"""
import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor


class LookupConfigurationError(RuntimeError):
    """Raised when the report service has no database connection settings."""


def _settings():
    settings = {
        "host": os.getenv("RAE_DB_HOST", ""),
        "port": int(os.getenv("RAE_DB_PORT", "3306")),
        "user": os.getenv("RAE_DB_USER", ""),
        "password": os.getenv("RAE_DB_PASSWORD", ""),
        "database": os.getenv("RAE_DB_NAME", ""),
    }
    if not all((settings["host"], settings["user"], settings["password"], settings["database"])):
        raise LookupConfigurationError("Project lookup database is not configured.")
    return settings


@contextmanager
def _connection():
    connection = pymysql.connect(
        **_settings(),
        cursorclass=DictCursor,
        connect_timeout=8,
        read_timeout=8,
        write_timeout=8,
        autocommit=True,
    )
    try:
        yield connection
    finally:
        connection.close()


def find_project(rae_id: str):
    """Find a subproject and its parent project without modifying the database.

    RAE IDs normally map to `projects.project_id`.  A `subprojects.table_id`
    match is also accepted.  Starting from projects is important because a
    valid project can have no subprojects yet.
    """
    try:
        record_id = int(str(rae_id).strip())
    except (TypeError, ValueError):
        return None
    if record_id < 1:
        return None

    sql = """
        SELECT
            CASE WHEN p.project_id = %s THEN p.project_id ELSE s.table_id END AS rae_id,
            s.subproject_name,
            p.project_id,
            p.project_name,
            CASE WHEN p.project_id = %s THEN 'project' ELSE 'subproject' END AS match_type
        FROM projects AS p
        LEFT JOIN subprojects AS s ON s.project_id = p.project_id
        WHERE p.project_id = %s OR s.table_id = %s
        ORDER BY CASE WHEN p.project_id = %s THEN 0 ELSE 1 END, s.table_id ASC
        LIMIT 1
    """
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (record_id, record_id, record_id, record_id, record_id))
            return cursor.fetchone()
