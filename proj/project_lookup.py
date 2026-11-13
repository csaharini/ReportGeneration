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


def _query_record(connection, record_id, fuzzy=False):
    if fuzzy:
        like = f"{record_id}%"
        sql = """
            SELECT
                CASE WHEN p.project_id = %s THEN p.project_id ELSE s.table_id END AS rae_id,
                s.subproject_name,
                p.project_id,
                p.project_name,
                CASE WHEN p.project_id = %s THEN 'project' ELSE 'subproject' END AS source,
                'fuzzy' AS match_type
            FROM projects AS p
            LEFT JOIN subprojects AS s ON s.project_id = p.project_id
            WHERE CAST(p.project_id AS CHAR) LIKE %s OR CAST(s.table_id AS CHAR) LIKE %s
            ORDER BY p.project_id ASC, s.table_id ASC
            LIMIT 1
        """
        params = (record_id, record_id, like, like)
    else:
        sql = """
            SELECT
                CASE WHEN p.project_id = %s THEN p.project_id ELSE s.table_id END AS rae_id,
                s.subproject_name,
                p.project_id,
                p.project_name,
                CASE WHEN p.project_id = %s THEN 'project' ELSE 'subproject' END AS source,
                'exact' AS match_type
            FROM projects AS p
            LEFT JOIN subprojects AS s ON s.project_id = p.project_id
            WHERE p.project_id = %s OR s.table_id = %s
            ORDER BY CASE WHEN p.project_id = %s THEN 0 ELSE 1 END, s.table_id ASC
            LIMIT 1
        """
        params = (record_id, record_id, record_id, record_id, record_id)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def find_project(rae_id: str):
    """Find a subproject and its parent project without modifying the database.

    RAE IDs normally map to `projects.project_id`.  A `subprojects.table_id`
    match is also accepted.  Starting from projects is important because a
    valid project can have no subprojects yet.

    Exact match is tried first; a prefix (fuzzy) match is used as a fallback
    so partial RAE IDs still surface the right project automatically.
    """
    try:
        record_id = int(str(rae_id).strip())
    except (TypeError, ValueError):
        return None
    if record_id < 1:
        return None

    with _connection() as connection:
        result = _query_record(connection, record_id, fuzzy=False)
        if result:
            return result
        result = _query_record(connection, record_id, fuzzy=True)
        return result
