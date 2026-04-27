from __future__ import annotations

from http import HTTPStatus
import re

from microshop.shared.config import SERVICES, db_path
from microshop.shared.db import connect, migrate, row_to_dict, rows_to_dicts
from microshop.shared.http import HttpError, RequestContext, Router, serve


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def init_db() -> None:
    conn = connect(db_path("users"))
    migrate(conn, [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    ])
    conn.close()


def validate_user(body: dict) -> tuple[str, str]:
    email = str(body.get("email", "")).strip().lower()
    name = str(body.get("name", "")).strip()
    if not EMAIL_RE.match(email):
        raise HttpError(HTTPStatus.BAD_REQUEST, "Valid email is required")
    if len(name) < 2:
        raise HttpError(HTTPStatus.BAD_REQUEST, "Name must contain at least 2 characters")
    return email, name


def create_user(ctx: RequestContext):
    email, name = validate_user(ctx.body)
    conn = connect(db_path("users"))
    try:
        with conn:
            cur = conn.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone())
        return HTTPStatus.CREATED, user
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HttpError(HTTPStatus.CONFLICT, "Email is already registered") from exc
        raise
    finally:
        conn.close()


def list_users(ctx: RequestContext):
    conn = connect(db_path("users"))
    users = rows_to_dicts(conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall())
    conn.close()
    return HTTPStatus.OK, users


def get_user(ctx: RequestContext):
    conn = connect(db_path("users"))
    user = row_to_dict(conn.execute("SELECT * FROM users WHERE id = ?", (ctx.path_params["id"],)).fetchone())
    conn.close()
    if not user:
        raise HttpError(HTTPStatus.NOT_FOUND, "User not found")
    return HTTPStatus.OK, user


def router() -> Router:
    init_db()
    r = Router()
    r.add("GET", "/health", lambda ctx: (HTTPStatus.OK, {"status": "ok", "service": "users"}))
    r.add("POST", "/users", create_user)
    r.add("GET", "/users", list_users)
    r.add("GET", "/users/{id}", get_user)
    return r


def main() -> None:
    cfg = SERVICES["users"]
    serve("users", cfg.host, cfg.port, router())


if __name__ == "__main__":
    main()
