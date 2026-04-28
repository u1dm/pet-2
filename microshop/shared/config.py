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
    bind_host: str

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def service_config(name: str, default_port: str) -> ServiceConfig:
    prefix = name.upper()
    return ServiceConfig(
        name=name,
        host=os.environ.get(f"{prefix}_HOST", "127.0.0.1"),
        port=int(os.environ.get(f"{prefix}_PORT", default_port)),
        bind_host=os.environ.get(f"{prefix}_BIND_HOST", os.environ.get("MICROSHOP_BIND_HOST", "127.0.0.1")),
    )


SERVICES = {
    "users": service_config("users", "8101"),
    "catalog": service_config("catalog", "8102"),
    "orders": service_config("orders", "8103"),
    "notifications": service_config("notifications", "8104"),
    "gateway": service_config("gateway", "8080"),
}


def db_path(service_name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{service_name}.sqlite3"


def event_log_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "events.jsonl"
