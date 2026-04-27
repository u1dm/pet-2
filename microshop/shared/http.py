from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


Handler = Callable[["RequestContext"], tuple[int, Any]]


@dataclass(frozen=True)
class RawResponse:
    body: bytes
    content_type: str


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class RequestContext:
    def __init__(self, handler: BaseHTTPRequestHandler, path_params: dict[str, str], body: dict[str, Any] | None):
        parsed = urlparse(handler.path)
        self.handler = handler
        self.method = handler.command
        self.path = parsed.path
        self.query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        self.path_params = path_params
        self.body = body or {}


class Router:
    def __init__(self) -> None:
        self.routes: list[tuple[str, re.Pattern[str], Handler]] = []

    def add(self, method: str, pattern: str, handler: Handler) -> None:
        regex = "/" if pattern == "/" else pattern.rstrip("/")
        regex = re.sub(r"{([a-zA-Z_][a-zA-Z0-9_]*):path}", r"(?P<\1>.+)", regex)
        regex = re.sub(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", r"(?P<\1>[^/]+)", regex)
        regex = "^" + regex + "$"
        self.routes.append((method.upper(), re.compile(regex), handler))

    def match(self, method: str, path: str) -> tuple[Handler, dict[str, str]]:
        normalized = path.rstrip("/") or "/"
        for route_method, regex, handler in self.routes:
            match = regex.match(normalized)
            if route_method == method.upper() and match:
                return handler, match.groupdict()
        raise HttpError(HTTPStatus.NOT_FOUND, "Route not found")


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any] | None:
    length = int(handler.headers.get("content-length", "0"))
    if length == 0:
        return None
    try:
        return json.loads(handler.rfile.read(length).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HttpError(HTTPStatus.BAD_REQUEST, "Invalid JSON body") from exc


def write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any] | list[Any] | None) -> None:
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def write_raw(handler: BaseHTTPRequestHandler, status: int, response: RawResponse) -> None:
    handler.send_response(status)
    handler.send_header("content-type", response.content_type)
    handler.send_header("content-length", str(len(response.body)))
    handler.end_headers()
    handler.wfile.write(response.body)


def make_handler(router: Router) -> type[BaseHTTPRequestHandler]:
    class AppHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.handle_request()

        def do_POST(self) -> None:
            self.handle_request()

        def do_PUT(self) -> None:
            self.handle_request()

        def do_DELETE(self) -> None:
            self.handle_request()

        def handle_request(self) -> None:
            try:
                parsed = urlparse(self.path)
                body = read_json(self)
                handler, path_params = router.match(self.command, parsed.path)
                status, payload = handler(RequestContext(self, path_params, body))
                if isinstance(payload, RawResponse):
                    write_raw(self, status, payload)
                else:
                    write_json(self, status, payload)
            except HttpError as exc:
                write_json(self, exc.status, {"error": exc.message})
            except Exception as exc:
                write_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return AppHandler


def serve(name: str, host: str, port: int, router: Router) -> None:
    print(f"{name} listening on http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), make_handler(router)).serve_forever()


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | list[Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"content-type": "application/json"} if payload is not None else {}
    request = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=3) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw or "{}")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw or "{}")
    except URLError as exc:
        raise HttpError(HTTPStatus.BAD_GATEWAY, f"Upstream unavailable: {exc.reason}") from exc
