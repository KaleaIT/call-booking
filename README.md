# Call-Booking Platform

A microservice platform for booking calls/meetings. Event-driven, **database-per-service**
(each service runs its own datastore instance with its own credentials), wired together
with Kafka and fronted by an nginx gateway. Auth uses **asymmetric JWT (RS256)** and every
service manages its schema with **Alembic migrations**.

```
                         ┌──────────────┐
   browser  ──────────►  │  api-gateway │  (nginx :8080)
                         └──────┬───────┘
            ┌───────────────────┼────────────────────┐
            ▼                   ▼                    ▼
     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
     │ auth-svc   │     │ booking-svc  │     │ analytics-svc  │
     │ FastAPI    │     │ FastAPI      │     │ FastAPI        │
     │ auth-pg    │     │ booking-pg   │     │ ClickHouse     │
     │ RS256 sign │     │ Redis lock   │     └──────▲─────────┘
     └────────────┘     └──────┬───────┘            │
                               │ produces           │ consumes
                        booking.created /            │
                        booking.cancelled            │
                               ▼                     │
                        ┌─────────────┐  Kafka  ─────┘
                        │    Kafka    │◄──────────────┐
                        └──────┬──────┘               │
                  consumes     │      consumes        │
            ┌─────────────────┐│┌──────────────────────┐
            ▼                  ▼▼                       ▼
   ┌────────────────┐  ┌──────────────────┐
   │ calendar-svc   │  │ notification-svc │  ─► Redis pub/sub
   │ Kafka consumer │  │ Kafka consumer   │     ─► ws-server (WebSocket)
   │ calendar-pg    │  │ + ws-server      │     ─► browser (real-time)
   │ mock GCal      │  └──────────────────┘
   └────────────────┘
```

Each service ships in **its own compose file** under `services/<svc>/docker-compose.yml`
(carrying its own database), and the root `docker-compose.yml` simply `include`s them all
plus the shared infra (`docker-compose.infra.yml`: Kafka, Redis, ClickHouse, Kafdrop). The
split means any service can be lifted onto its own server unchanged — see
[Deploying a service on its own server](#deploying-a-service-on-its-own-server).

## Services

| Service                | Stack                              | Port | Responsibility |
|------------------------|------------------------------------|------|----------------|
| `auth-service`         | FastAPI + PostgreSQL + JWT         | 8001 | register / login / `/auth/me` |
| `booking-service`      | FastAPI + PostgreSQL + Redis lock  | 8002 | slots, booking, cancellation; emits Kafka events |
| `calendar-service`     | FastAPI + PostgreSQL + Kafka       | 8003 | consumes events, mock Google Calendar, `booking_id → external_event_id` |
| `notification-service` | Kafka consumer + Redis pub/sub + FastAPI WS | — | consumes events, pushes real-time notifications over WebSocket (`/api/notifications/ws`) |
| `analytics-service`    | FastAPI + ClickHouse + Kafka       | 8005 | consumes events, statistics API |
| `frontend`             | React + Vite                       | 5173 | login/register, dashboard, slots, booking, analytics |
| `api-gateway`          | nginx                              | 8080 | routes `/auth /booking /calendar /analytics` to services, `/` to frontend |

Each backend is an **independent FastAPI app** with its **own database instance** and
**own credentials** (true database-per-service): `auth-postgres`, `booking-postgres` and
`calendar-postgres` are three separate PostgreSQL containers; analytics uses ClickHouse.
There are no cross-service foreign keys and no shared schema — services communicate only
through Kafka events and verified JWTs.

## Quick start

```bash
docker network create callbooking      # shared external network (once)
cp .env.example .env
bash scripts/gen-jwt-keys.sh           # generate RS256 key pair (once)
docker-compose up -d --build
```

Then open the app through the gateway: **http://localhost:8080**

> Schema is applied automatically: each service's container runs `alembic upgrade head`
> (see `entrypoint.sh`) before starting, so the databases are migrated on first boot.

### Healthchecks

```bash
# via gateway (port 8080)
curl http://localhost:8080/auth/health
curl http://localhost:8080/booking/health
curl http://localhost:8080/calendar/health
curl http://localhost:8080/analytics/health

# or directly on each service port
curl http://localhost:8001/health   # auth
curl http://localhost:8002/health   # booking
curl http://localhost:8003/health   # calendar
curl http://localhost:8005/health   # analytics
```

## End-to-end flow

Through the UI at http://localhost:8080, or via curl against the gateway:

```bash
GW=http://localhost:8080

# 1. register
curl -s -X POST $GW/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"secret","full_name":"Alice"}'

# 2. login -> grab the token
TOKEN=$(curl -s -X POST $GW/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"secret"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 3. create a slot
curl -s -X POST $GW/booking/slots -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"start_time":"2026-07-01T10:00:00Z","end_time":"2026-07-01T10:30:00Z"}'

# 4. book slot #1  -> emits booking.created
curl -s -X POST $GW/booking/slots/1/book -H "Authorization: Bearer $TOKEN"

# 5. events propagate to Kafka -> calendar / notification / analytics
docker compose logs calendar-service notification-worker

# 6. analytics
curl -s $GW/analytics/stats -H "Authorization: Bearer $TOKEN"
```

Cancel a booking (emits `booking.cancelled`):

```bash
curl -s -X POST $GW/booking/bookings/1/cancel -H "Authorization: Bearer $TOKEN"
```

## How it fits together

- **Auth** issues a JWT signed with an **RSA private key (RS256)** that only
  `auth-service` holds. `booking-service` verifies it with the **public key alone** — it
  can check a signature but can never forge one, and never calls auth synchronously. A
  leak in any verifier cannot mint tokens. Keys are generated by `scripts/gen-jwt-keys.sh`
  into `infra/jwt/` and mounted read-only (`private.pem` → auth only, `public.pem` → verifiers).
- **Booking** acquires a Redis lock (`lock:slot:<id>`) around the read-check-write so
  two concurrent requests can't double-book the same slot. On success it produces a
  `booking.created` (or `booking.cancelled`) event to Kafka.
- **Calendar / Notification / Analytics** each consume those topics independently in
  their own consumer group:
  - calendar creates a mock Google Calendar event and persists `booking_id → external_event_id`,
  - notification builds a notification for each participant (guest + host), publishes it to
    a Redis pub/sub channel and stores a short per-user history; the bundled ws-server fans
    it out to the user's browser over WebSocket in real time,
  - analytics appends a row to ClickHouse and serves aggregate stats.

## Running a single service independently

Because each service is a self-contained compose file (service **+ its own database**),
any one of them runs on its own. `auth-service` is fully standalone — it needs nothing but
its own Postgres:

```bash
docker network create callbooking            # once
bash scripts/gen-jwt-keys.sh                 # once
docker-compose --env-file .env -f services/auth-service/docker-compose.yml up --build
```

Services that use the shared backbone (`booking`, `calendar`, `notification`, `analytics`
need Kafka/Redis/ClickHouse) start the same way; just have the backbone reachable first:

```bash
docker-compose --env-file .env -f docker-compose.infra.yml up -d
docker-compose --env-file .env -f services/booking-service/docker-compose.yml up --build
```

They attach to the shared external `callbooking` network and find the backbone by its
env hostnames. The client code retries until Kafka/Redis/ClickHouse are reachable, so
startup order doesn't matter.

## Deploying a service on its own server

The monorepo is **not** a deployment boundary — each service builds and ships
independently. To move, say, `booking-service` to a dedicated host:

1. Build/pull its image: `docker build -t booking-service services/booking-service`.
2. Run it there with `services/booking-service/docker-compose.yml` (it carries its own
   `booking-postgres`).
3. Point its env at the real backbone: set `KAFKA_BOOTSTRAP_SERVERS`, `REDIS_HOST`, and
   (if the DB is external) `BOOKING_POSTGRES_HOST` to the real endpoints.

Nothing else in the platform needs to change — there are no shared databases, no shared
code, and no synchronous calls into other services. The `include` + single network in this
repo is only a convenience for running everything together on one machine.

## Database migrations (Alembic)

`auth`, `booking` and `calendar` each own an independent Alembic history under
`services/<svc>/migrations/`. Schema is applied automatically at container start
(`entrypoint.sh` → `alembic upgrade head`). To create a new migration after changing models:

```bash
docker-compose exec booking-service alembic revision --autogenerate -m "add column"
docker-compose exec booking-service alembic upgrade head
```

(`analytics` uses ClickHouse and bootstraps its table via `init_schema()`; `notification`
is stateless.)

## Local development (without Docker)

Each service is standalone. Example for one service:

```bash
cd services/auth-service
pip install -r requirements.txt
# point env vars at localhost infra, run migrations, then start:
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

## Environment

All configuration lives in `.env` (see `.env.example`). Key knobs: **per-service**
Postgres credentials (`AUTH_POSTGRES_*`, `BOOKING_POSTGRES_*`, `CALENDAR_POSTGRES_*`),
Redis/Kafka/ClickHouse connection info, JWT settings (`JWT_ALGORITHM=RS256`, keys in
`infra/jwt/`), and per-service ports.
