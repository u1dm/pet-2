from __future__ import annotations

from http import HTTPStatus

from microshop.shared.config import SERVICES, db_path
from microshop.shared.db import connect, migrate, row_to_dict, rows_to_dicts
from microshop.shared.events import publish
from microshop.shared.http import HttpError, RequestContext, Router, request_json, serve


def init_db() -> None:
    conn = connect(db_path("orders"))
    migrate(conn, [
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    ])
    conn.close()


def upstream(service: str, path: str) -> str:
    return SERVICES[service].base_url + path


def create_order(ctx: RequestContext):
    user_id = int(ctx.body.get("user_id", 0))
    product_id = int(ctx.body.get("product_id", 0))
    quantity = int(ctx.body.get("quantity", 0))
    if user_id <= 0 or product_id <= 0 or quantity <= 0:
        raise HttpError(HTTPStatus.BAD_REQUEST, "user_id, product_id and quantity must be positive")

    user_status, user = request_json("GET", upstream("users", f"/users/{user_id}"))
    if user_status != HTTPStatus.OK:
        raise HttpError(user_status, user.get("error", "User validation failed"))

    product_status, product = request_json("GET", upstream("catalog", f"/products/{product_id}"))
    if product_status != HTTPStatus.OK:
        raise HttpError(product_status, product.get("error", "Product validation failed"))

    reserve_status, reserve = request_json("POST", upstream("catalog", f"/products/{product_id}/reserve"), {"quantity": quantity})
    if reserve_status != HTTPStatus.OK:
        raise HttpError(reserve_status, reserve.get("error", "Stock reservation failed"))

    total_cents = int(product["price_cents"]) * quantity
    conn = connect(db_path("orders"))
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO orders (user_id, product_id, quantity, total_cents, status) VALUES (?, ?, ?, ?, ?)",
                (user_id, product_id, quantity, total_cents, "created"),
            )
        order = row_to_dict(conn.execute("SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)).fetchone())
    finally:
        conn.close()

    publish("order.created", {"order": order, "user": user, "product": product})
    return HTTPStatus.CREATED, order


def list_orders(ctx: RequestContext):
    user_id = ctx.query.get("user_id")
    conn = connect(db_path("orders"))
    if user_id:
        orders = rows_to_dicts(conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall())
    else:
        orders = rows_to_dicts(conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall())
    conn.close()
    return HTTPStatus.OK, orders


def get_order(ctx: RequestContext):
    conn = connect(db_path("orders"))
    order = row_to_dict(conn.execute("SELECT * FROM orders WHERE id = ?", (ctx.path_params["id"],)).fetchone())
    conn.close()
    if not order:
        raise HttpError(HTTPStatus.NOT_FOUND, "Order not found")
    return HTTPStatus.OK, order


def router() -> Router:
    init_db()
    r = Router()
    r.add("GET", "/health", lambda ctx: (HTTPStatus.OK, {"status": "ok", "service": "orders"}))
    r.add("POST", "/orders", create_order)
    r.add("GET", "/orders", list_orders)
    r.add("GET", "/orders/{id}", get_order)
    return r


def main() -> None:
    cfg = SERVICES["orders"]
    serve("orders", cfg.host, cfg.port, router())


if __name__ == "__main__":
    main()
