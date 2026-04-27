from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("MICROSHOP_DATA_DIR", ROOT_DIR / "data"))


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


SERVICES = {
    "users": ServiceConfig("users", "127.0.0.1", int(os.environ.get("USERS_PORT", "8101"))),
    "catalog": ServiceConfig("catalog", "127.0.0.1", int(os.environ.get("CATALOG_PORT", "8102"))),
    "orders": ServiceConfig("orders", "127.0.0.1", int(os.environ.get("ORDERS_PORT", "8103"))),
    "notifications": ServiceConfig("notifications", "127.0.0.1", int(os.environ.get("NOTIFICATIONS_PORT", "8104"))),
    "gateway": ServiceConfig("gateway", "127.0.0.1", int(os.environ.get("GATEWAY_PORT", "8080"))),
}


def db_path(service_name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{service_name}.sqlite3"


def event_log_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "events.jsonl"
