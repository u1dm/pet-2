# MicroShop

MicroShop is a complete small microservice application without DevOps files. It models a simple shop flow:

- users service: registers and reads customers
- catalog service: manages products and stock reservations
- orders service: validates users/products, reserves stock and creates orders
- notifications service: consumes order-created events from the local event log
- gateway service: exposes one HTTP entrypoint for clients
- frontend: browser console served by the gateway

The implementation intentionally uses only Python standard library modules. Each service owns its own SQLite database under `data/`, and services communicate over HTTP.

## Run locally

```bash
python3 run_local.py
```

Gateway URL:

```text
http://127.0.0.1:8080
```

Open that URL in a browser to use the frontend. The same gateway also exposes the JSON API.

## Example flow

```bash
curl -s -X POST http://127.0.0.1:8080/users \
  -H 'content-type: application/json' \
  -d '{"email":"ada@example.com","name":"Ada Lovelace"}'

curl -s -X POST http://127.0.0.1:8080/products \
  -H 'content-type: application/json' \
  -d '{"sku":"BOOK-1","name":"Architecture Book","price":"24.90","stock":5}'

curl -s -X POST http://127.0.0.1:8080/orders \
  -H 'content-type: application/json' \
  -d '{"user_id":1,"product_id":1,"quantity":2}'

curl -s -X POST http://127.0.0.1:8080/notifications/sync
curl -s http://127.0.0.1:8080/notifications
```

## Service ports

| Service | Port |
| --- | ---: |
| gateway | 8080 |
| users | 8101 |
| catalog | 8102 |
| orders | 8103 |
| notifications | 8104 |

Ports can be overridden with `GATEWAY_PORT`, `USERS_PORT`, `CATALOG_PORT`, `ORDERS_PORT` and `NOTIFICATIONS_PORT`.

## Tests

```bash
python3 -m unittest
```

## DevOps part intentionally omitted

No Dockerfile, docker-compose, Kubernetes manifests, Terraform, CI/CD pipelines, service mesh config, observability stack or deployment scripts are included. Those are the parts you can implement.

I will evaluate your DevOps part by these criteria:

- repeatable local and remote deployment
- clean service isolation and configuration through environment variables
- database persistence and migration strategy
- health checks and readiness/liveness semantics
- logs, metrics and tracing plan
- secure secret handling
- rollback strategy and failure recovery
- resource limits, scaling and network boundaries
- CI pipeline quality: test, build, security scan, artifact publishing
- documentation that lets another engineer deploy the system from scratch
