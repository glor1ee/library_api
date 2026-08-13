# Library Service API

A RESTful API for managing a library's book inventory, borrowings and
payments, built with Django and Django REST Framework.

## Scope

This is a Flex-track submission of the Library Service assignment. All 15
"Coding Mandatory" tasks were implemented:

- CRUD for the Books Service
- Permissions for the Books Service
- CRUD & JWT authentication for the Users Service
- Borrowings list & detail endpoint, with filtering by `user_id` and `is_active`
- Create Borrowing endpoint (decrements book inventory)
- Return Borrowing functionality (increments book inventory)
- Notifications on each Borrowing creation (Telegram, via Django Q)
- Daily function for checking overdue borrowings (Telegram, via Django Q)
- List & Detail Payments Endpoint
- Stripe Payment Session creation, automated on every Borrowing
- success/cancel endpoints for the Payment Service
- FINE Payment for overdue books
- docker-compose setup

The four "Coding Optional" tasks (tracking expired Stripe sessions, denying
new borrowings while a payment is pending, a Telegram notification on
successful payment, and GitHub Actions) were not selected and are not
implemented.

## Tech stack

Django 6.1 · Django REST Framework 3.18 · djangorestframework-simplejwt
(JWT auth) · drf-spectacular (OpenAPI docs) · django-q2 (async tasks &
daily schedule, ORM broker) · stripe (payments) · PostgreSQL (SQLite
fallback for local dev) · coverage.py · Docker / docker-compose.

## Project structure

```
library_service_api/    # project settings and urls
user/                     # custom email-based User model, registration, JWT endpoints
books/                    # Book model & endpoints
borrowings/               # Borrowing model & endpoints, daily overdue check
payments/                 # Payment model, Stripe checkout sessions, success/cancel
notifications/            # Telegram sending helper + async notification tasks
```

## Getting started

### Option A - plain Python (SQLite, no Docker)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

No `DB_HOST` env var means the project automatically falls back to SQLite.

Notifications and the daily overdue check are processed by Django Q. Run a
worker in a second terminal for them to actually be delivered:

```bash
python manage.py qcluster
```

To have the daily overdue check run automatically (once a day) instead of
manually via `python manage.py check_overdue_borrowings`, register it once:

```bash
python manage.py setup_schedules
```

### Option B - Docker (PostgreSQL)

```bash
cp .env.sample .env      # edit values if you like
docker compose up --build
```

This starts the API, PostgreSQL, and a `qcluster` worker. The `app`
service applies migrations and registers the daily schedule
automatically on startup.

```bash
docker compose exec app python manage.py createsuperuser
```

### Stripe & Telegram

`STRIPE_SECRET_KEY`, `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are read
from the environment (see `.env.sample`). Without them, the app still
works normally - creating/returning borrowings still creates `Payment`
rows and still enqueues notifications, but no real Stripe session or
Telegram message is sent (this is logged, not an error). Fill them in to
get real Stripe Checkout sessions and Telegram messages.

### API documentation

- Swagger UI: `GET /api/doc/swagger/`
- Redoc: `GET /api/doc/redoc/`
- Raw OpenAPI schema: `GET /api/schema/`
- Django admin: `GET /admin/`

## Authentication

There's no username - users register and log in with their email. Register,
then obtain a JWT access/refresh token pair, then send the access token on
every subsequent request as `Authorization: Bearer <token>`.

```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "strongpass1", "first_name": "Alice"}'
```

```json
{
  "id": 1,
  "email": "alice@example.com",
  "first_name": "Alice",
  "last_name": "",
  "is_staff": false
}
```

```bash
curl -X POST http://localhost:8000/api/users/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "strongpass1"}'
```

```json
{ "refresh": "<refresh token>", "access": "<access token>" }
```

```bash
curl -X POST http://localhost:8000/api/users/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh token>"}'
```

## Endpoint reference

All endpoints below (except registering and obtaining a token) require
`Authorization: Bearer <access token>`. Paginated list endpoints return
`{"count", "next", "previous", "results"}` (10 items per page).

### Users (`/api/users/`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/users/` | Register a new account |
| POST | `/api/users/token/` | Obtain a JWT access/refresh token pair |
| POST | `/api/users/token/refresh/` | Refresh an access token |
| GET, PUT, PATCH | `/api/users/me/` | View/update your own profile |

### Books (`/api/books/`)

Reading (list/retrieve) is open to any authenticated user; creating,
updating and deleting require `is_staff`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/books/` | List books |
| POST | `/api/books/` | Add a new book (staff only) |
| GET | `/api/books/{id}/` | Book detail |
| PUT, PATCH | `/api/books/{id}/` | Update a book, including inventory (staff only) |
| DELETE | `/api/books/{id}/` | Delete a book (staff only) |

```bash
curl -X POST http://localhost:8000/api/books/ \
  -H "Authorization: Bearer <staff access token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "cover": "SOFT", "inventory": 3, "daily_fee": "1.50"}'
```

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "cover": "SOFT",
  "inventory": 3,
  "daily_fee": "1.50"
}
```

### Borrowings (`/api/borrowings/`)

A regular user only ever sees their own borrowings. Staff users see every
borrowing and can filter by `user_id`; `is_active=true` narrows the list
to borrowings that haven't been returned yet (`is_active=false` for
already-returned ones). Creating a borrowing also creates a pending
`Payment` (with a Stripe Checkout session) and enqueues a Telegram
notification; returning one overdue additionally creates a FINE payment
(`daily_fee * overdue_days * FINE_MULTIPLIER`, multiplier `2` by default).

| Method | Path | Description |
|---|---|---|
| GET | `/api/borrowings/` | List borrowings (`?user_id=&is_active=`) |
| POST | `/api/borrowings/` | Create a borrowing (`book`, `expected_return_date`) - decrements inventory |
| GET | `/api/borrowings/{id}/` | Borrowing detail |
| POST | `/api/borrowings/{id}/return/` | Mark as returned - increments inventory |

Borrow a book:

```bash
curl -X POST http://localhost:8000/api/borrowings/ \
  -H "Authorization: Bearer <access token>" \
  -H "Content-Type: application/json" \
  -d '{"book": 1, "expected_return_date": "2026-08-20"}'
```

```json
{
  "id": 1,
  "expected_return_date": "2026-08-20",
  "book": 1
}
```

Return it:

```bash
curl -X POST http://localhost:8000/api/borrowings/1/return/ \
  -H "Authorization: Bearer <access token>"
```

```json
{
  "id": 1,
  "borrow_date": "2026-08-10",
  "expected_return_date": "2026-08-20",
  "actual_return_date": "2026-08-15",
  "book": {
    "id": 1,
    "title": "Dune",
    "author": "Frank Herbert",
    "cover": "SOFT",
    "inventory": 3,
    "daily_fee": "1.50"
  },
  "user_email": "alice@example.com"
}
```

### Payments (`/api/payments/`)

A regular user only ever sees payments for their own borrowings; staff see
all payments.

| Method | Path | Description |
|---|---|---|
| GET | `/api/payments/` | List payments |
| GET | `/api/payments/{id}/` | Payment detail, including the Stripe `session_url` |
| GET | `/api/payments/success/?session_id=` | Confirm a Stripe payment and mark it `PAID` |
| GET | `/api/payments/cancel/` | Informational message for an abandoned payment |

```bash
curl http://localhost:8000/api/payments/ -H "Authorization: Bearer <access token>"
```

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {"id": 1, "status": "PENDING", "type": "PAYMENT", "borrowing": 1, "money_to_pay": "6.00"}
  ]
}
```

## Running tests

```bash
coverage run manage.py test
coverage report
```
