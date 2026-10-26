# Automated Email Notification System

A REST API where logged in users schedule an email for a future date and time, and a
recurring cron job checks for anything due and sends it, retrying on failure.

Stack: **FastAPI** + **SQLAlchemy** + **SQLite**, cookie sessions via Starlette's
`SessionMiddleware`, password hashing via `passlib`/`bcrypt`, rate limiting via `slowapi`,
scheduled background jobs via `APScheduler`.

It runs entirely on a local mock outbox file by default, so it needs no SMTP account to try
out. See [Mock mode versus live mode](#mock-mode-versus-live-mode) below for pointing it at a
real mail server later.

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/seed_demo_data.py    # creates demo@email-notifications.dev / demo12345, schedules one due email

uvicorn app.main:app --reload --reload-dir app
```

Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs` once it is running. The background
cron job starts automatically and checks for due emails every thirty seconds by default; a
manual trigger is also available at `POST /cron/run`.

Run the test suite with:

```bash
pytest
```

## The main components

The app is organized the way the task spec asks for, as models, controllers, and views, even
though FastAPI does not use those exact folder names by default:

**`app/models.py` is the model layer.** `User` holds login credentials. `ScheduledEmail` is the
`scheduled_emails` table the spec calls for: `recipient_email`, `subject`, `body`,
`scheduled_time`, `status`, and `attempts`, plus `last_error`/`last_attempt_at`/`sent_at` so a
failed send leaves a trail instead of just a number going up. `status` is an enum (`pending`,
`sent`, `failed`), not a free text column.

**`app/email.py` holds the `Email` class the spec names explicitly.** It wraps one
`ScheduledEmail` row and exposes `scheduleEmail()` and `sendEmail()` as the spec literally
spells them, camelCase and all, rather than the snake_case Python would normally use, since the
point of this file is to satisfy that exact requirement. `scheduleEmail()` is a class method
that creates and saves a new row. `sendEmail()` attempts delivery once through whichever mailer
is active, then updates `attempts`, `status`, and `last_error` based on what happened. It never
decides when to run; that is the cron job's job.

**`app/mail/` is the delivery layer, swappable behind one interface.** `base.py` defines
`Mailer.send(to, subject, body)`, the only contract the rest of the app depends on.
`mock_mailer.py` appends a line of JSON to a local outbox file instead of calling a real
server, and treats any address whose local part starts with `bounce-` as a simulated bounce, so
retry behavior can be tested without a real flaky mail server. `smtp_mailer.py` sends for real
over SMTP with `STARTTLS`, using whatever host and credentials are set in `.env`. `registry.py`
picks one based on `MAIL_MODE`; nothing else in the app knows or cares which mailer is active.

**`app/cron.py` is the actual cron job's logic, independent of how it gets triggered.**
`process_due_emails()` queries for every `ScheduledEmail` that is still pending, is due, and has
not used up its retry budget, then calls `sendEmail()` on each one and tallies the result. Since
a failed send leaves `status` at `pending` (until the attempt limit is hit), the very next time
this function runs it will pick the same row back up automatically. That is the entire retry
mechanism; there is no separate retry queue to manage.

**`app/scheduler.py` is what actually behaves like a cron job.** An `APScheduler`
`BackgroundScheduler` calls `process_due_emails()` on a fixed interval (`CRON_INTERVAL_SECONDS`,
thirty seconds by default), started in `main.py`'s FastAPI lifespan and shut down cleanly on
exit. `POST /cron/run` calls the same function directly, for demos or for triggering it sooner
than the next tick.

**`app/deps.py` reads the login state straight out of the session.** `get_current_user` pulls a
`user_id` out of `request.session`, which Starlette's `SessionMiddleware` maintains as a signed
cookie, and loads the matching row. This is the one deliberate difference from the other two
practice APIs in this series, which both use JWTs: the spec for this task names sessions
specifically, so that is what got built.

**`app/controllers/` holds the actual HTTP endpoints, named controllers rather than routers to
match the spec's language, even though they are the same thing FastAPI calls a router:**

<table>
<tr><th>File</th><th>Routes</th><th>Notes</th></tr>
<tr><td><code>auth.py</code></td><td><code>POST /register</code>, <code>POST /login</code>, <code>POST /logout</code></td><td>Login sets <code>request.session["user_id"]</code>; logout clears the whole session</td></tr>
<tr><td><code>emails.py</code></td><td><code>POST /emails</code>, <code>GET /emails</code>, <code>GET /emails/{id}</code>, <code>DELETE /emails/{id}</code></td><td>Scoped to the logged in user throughout; canceling only works while still pending</td></tr>
<tr><td><code>cron.py</code></td><td><code>POST /cron/run</code></td><td>Manual trigger alongside the scheduled job, for anyone logged in</td></tr>
</table>

**`app/limiter.py` plus the `slowapi` wiring in `main.py` handle abuse prevention.** A `Limiter`
keyed by client IP, with a global default of one hundred requests per minute and a stricter
limit of five per minute specifically on `/login`, since that is the endpoint someone would
actually try to brute force.

**`app/main.py` assembles all of it.** Creates the tables on startup, adds the session
middleware, starts and stops the scheduler through `lifespan`, registers the rate limiter, and
mounts each controller. Nothing business specific lives here; it is purely wiring.

**`scripts/seed_demo_data.py`** creates a demo login and one already due scheduled email, so
there is something for the cron job to pick up immediately after the server starts.

**`tests/`** has sixteen pytest feature tests covering registration and login, scheduling and
canceling, that one user cannot read or cancel another user's email, that the cron job sends a
due email and leaves a future one alone, that rerunning the cron job is safe once something is
already sent, and that a repeatedly bouncing address retries up to the attempt limit and then
gets marked failed. The multi user authorization tests use two separate test clients rather than
one, since each `TestClient` keeps its own cookie jar and a shared one would just overwrite
whichever session logged in most recently.

## Mock mode versus live mode

`MAIL_MODE` (in `.env`, see `.env.example`) controls everything:

* **mock** (the default): `MockMailer` appends every send to a local `outbox.jsonl` file.
  Nothing leaves your machine, and the simulated bounce convention above makes retry behavior
  fully testable offline.
* **live**: `SmtpMailer` sends for real using `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/
  `SMTP_PASSWORD`/`SMTP_FROM_EMAIL` from `.env`. Works against Gmail's SMTP relay, Mailtrap's
  sandbox, or any standard SMTP provider; none require a paid plan to try.

Every other file in the app, including the cron job, the controllers, and the tests, behaves
identically in either mode, because they only ever call `Mailer.send()`, never a specific
provider.

## Decisions worth knowing about

* **The `Email` class uses camelCase method names on purpose**, breaking from PEP 8 for the one
  file where the task spec names the exact methods it wants (`scheduleEmail()`, `sendEmail()`).
  Everywhere else in the codebase follows normal Python style.
* **Sessions, not JWTs, even though the other two practice APIs in this series use JWTs.** The
  spec for this task specifically says registration and login with sessions, so that is the
  authentication model this one uses, rather than defaulting to what came before it.
* **A failed send does not get removed from the pending queue or moved somewhere else.** It just
  stays `pending` with `attempts` incremented, which means the existing due query picks it back
  up on the very next cron tick with no separate retry table or scheduling logic required, right
  up until `MAIL_MAX_ATTEMPTS` is reached and it finally flips to `failed`.
* **The mock bounce sentinel lives in the local part of the address (`bounce-` prefix), not the
  domain.** A reserved domain like `.test` seemed like the obvious choice at first, but
  `email_validator` correctly rejects reserved special use top level domains as invalid email
  addresses, so the sentinel had to move somewhere a normal validator would still accept.
* **Canceling a scheduled email is only allowed while it is still pending.** Once the cron job
  has sent it, or it has exhausted its retries and failed, deleting the row would erase the only
  record that it was ever attempted.
