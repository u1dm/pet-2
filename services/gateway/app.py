from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from microshop.shared.config import SERVICES
from microshop.shared.http import HttpError, RawResponse, RequestContext, Router, request_json, serve


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

ROUTES = {
    "users": "users",
    "products": "catalog",
    "orders": "orders",
    "notifications": "notifications",
}


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}


def static_file(ctx: RequestContext):
    requested = ctx.path_params.get("asset", "index.html")
    if requested in {"", "/"}:
        requested = "index.html"
    path = (FRONTEND_DIR / requested).resolve()
    if FRONTEND_DIR.resolve() not in path.parents and path != FRONTEND_DIR.resolve():
        raise HttpError(HTTPStatus.NOT_FOUND, "Asset not found")
    if not path.is_file():
        raise HttpError(HTTPStatus.NOT_FOUND, "Asset not found")
    content_type = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
    return HTTPStatus.OK, RawResponse(path.read_bytes(), content_type)


def proxy(ctx: RequestContext):
    resource = ctx.path_params["resource"]
    tail = ctx.path_params.get("tail", "")
    service = ROUTES.get(resource)
    if not service:
        raise HttpError(HTTPStatus.NOT_FOUND, "Gateway route not found")
    target_path = "/" + resource + (f"/{tail}" if tail else "")
    if ctx.handler.path.find("?") != -1:
        target_path += "?" + ctx.handler.path.split("?", 1)[1]
    status, payload = request_json(ctx.method, SERVICES[service].base_url + target_path, ctx.body if ctx.method in {"POST", "PUT"} else None)
    return status, payload


def health(ctx: RequestContext):
    statuses = {}
    overall = HTTPStatus.OK
    for name, cfg in SERVICES.items():
        if name == "gateway":
            continue
        status, payload = request_json("GET", cfg.base_url + "/health")
        statuses[name] = payload if status == HTTPStatus.OK else {"status": "down"}
        if status != HTTPStatus.OK:
            overall = HTTPStatus.BAD_GATEWAY
    return overall, {"status": "ok" if overall == HTTPStatus.OK else "degraded", "services": statuses}


def router() -> Router:
    r = Router()
    r.add("GET", "/", static_file)
    r.add("GET", "/assets/{asset:path}", static_file)
    r.add("GET", "/health", health)
    r.add("GET", "/{resource}", proxy)
    r.add("POST", "/{resource}", proxy)
    r.add("GET", "/{resource}/{tail:path}", proxy)
    r.add("POST", "/{resource}/{tail:path}", proxy)
    return r


def main() -> None:
    cfg = SERVICES["gateway"]
    serve("gateway", cfg.bind_host, cfg.port, router())


if __name__ == "__main__":
    main()
