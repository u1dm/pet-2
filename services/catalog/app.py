from __future__ import annotations

from http import HTTPStatus
from decimal import Decimal, InvalidOperation

from microshop.shared.config import SERVICES, db_path
from microshop.shared.db import connect, migrate, row_to_dict, rows_to_dicts
from microshop.shared.http import HttpError, RequestContext, Router, serve


def init_db() -> None:
    conn = connect(db_path("catalog"))
    migrate(conn, [
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    ])
    conn.close()


def parse_product(body: dict) -> tuple[str, str, int, int]:
    sku = str(body.get("sku", "")).strip().upper()
    name = str(body.get("name", "")).strip()
    if len(sku) < 3:
        raise HttpError(HTTPStatus.BAD_REQUEST, "SKU must contain at least 3 characters")
    if len(name) < 2:
        raise HttpError(HTTPStatus.BAD_REQUEST, "Name must contain at least 2 characters")
    try:
        price = Decimal(str(body.get("price", "0")))
    except InvalidOperation as exc:
        raise HttpError(HTTPStatus.BAD_REQUEST, "Price must be numeric") from exc
    stock = int(body.get("stock", 0))
    if price < 0 or stock < 0:
        raise HttpError(HTTPStatus.BAD_REQUEST, "Price and stock must be non-negative")
    return sku, name, int(price * 100), stock


def create_product(ctx: RequestContext):
    sku, name, price_cents, stock = parse_product(ctx.body)
    conn = connect(db_path("catalog"))
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO products (sku, name, price_cents, stock) VALUES (?, ?, ?, ?)",
                (sku, name, price_cents, stock),
            )
        product = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (cur.lastrowid,)).fetchone())
        return HTTPStatus.CREATED, product
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HttpError(HTTPStatus.CONFLICT, "SKU already exists") from exc
        raise
    finally:
        conn.close()


def list_products(ctx: RequestContext):
    conn = connect(db_path("catalog"))
    products = rows_to_dicts(conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall())
    conn.close()
    return HTTPStatus.OK, products


def get_product(ctx: RequestContext):
    conn = connect(db_path("catalog"))
    product = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (ctx.path_params["id"],)).fetchone())
    conn.close()
    if not product:
        raise HttpError(HTTPStatus.NOT_FOUND, "Product not found")
    return HTTPStatus.OK, product


def reserve_stock(ctx: RequestContext):
    product_id = ctx.path_params["id"]
    quantity = int(ctx.body.get("quantity", 0))
    if quantity <= 0:
        raise HttpError(HTTPStatus.BAD_REQUEST, "Quantity must be positive")
    conn = connect(db_path("catalog"))
    try:
        with conn:
            product = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())
            if not product:
                raise HttpError(HTTPStatus.NOT_FOUND, "Product not found")
            if product["stock"] < quantity:
                raise HttpError(HTTPStatus.CONFLICT, "Insufficient stock")
            conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        updated = row_to_dict(conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())
        return HTTPStatus.OK, updated
    finally:
        conn.close()


def router() -> Router:
    init_db()
    r = Router()
    r.add("GET", "/health", lambda ctx: (HTTPStatus.OK, {"status": "ok", "service": "catalog"}))
    r.add("POST", "/products", create_product)
    r.add("GET", "/products", list_products)
    r.add("GET", "/products/{id}", get_product)
    r.add("POST", "/products/{id}/reserve", reserve_stock)
    return r


def main() -> None:
    cfg = SERVICES["catalog"]
    serve("catalog", cfg.host, cfg.port, router())


if __name__ == "__main__":
    main()
