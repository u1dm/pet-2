from __future__ import annotations

from http import HTTPStatus

from microshop.shared.config import SERVICES, db_path
from microshop.shared.db import connect, migrate, row_to_dict, rows_to_dicts
from microshop.shared.events import read_events
from microshop.shared.http import RequestContext, Router, serve


def init_db() -> None:
    conn = connect(db_path("notifications"))
    migrate(conn, [
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    ])
    conn.close()


def sync_events(ctx: RequestContext):
    conn = connect(db_path("notifications"))
    created = 0
    try:
        with conn:
            for event in read_events():
                if event.type != "order.created":
                    continue
                order = event.payload["order"]
                user = event.payload["user"]
                message = f"Order #{order['id']} for {user['email']} was created"
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO notifications (event_id, user_id, channel, message, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (event.id, order["user_id"], "email", message, "queued"),
                )
                created += cur.rowcount
    finally:
        conn.close()
    return HTTPStatus.OK, {"created": created}


def list_notifications(ctx: RequestContext):
    user_id = ctx.query.get("user_id")
    conn = connect(db_path("notifications"))
    if user_id:
        rows = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall()
    notifications = rows_to_dicts(rows)
    conn.close()
    return HTTPStatus.OK, notifications


def get_notification(ctx: RequestContext):
    conn = connect(db_path("notifications"))
    notification = row_to_dict(conn.execute("SELECT * FROM notifications WHERE id = ?", (ctx.path_params["id"],)).fetchone())
    conn.close()
    if not notification:
        from microshop.shared.http import HttpError
        raise HttpError(HTTPStatus.NOT_FOUND, "Notification not found")
    return HTTPStatus.OK, notification


def router() -> Router:
    init_db()
    r = Router()
    r.add("GET", "/health", lambda ctx: (HTTPStatus.OK, {"status": "ok", "service": "notifications"}))
    r.add("POST", "/notifications/sync", sync_events)
    r.add("GET", "/notifications", list_notifications)
    r.add("GET", "/notifications/{id}", get_notification)
    return r


def main() -> None:
    cfg = SERVICES["notifications"]
    serve("notifications", cfg.host, cfg.port, router())


if __name__ == "__main__":
    main()
