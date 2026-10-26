import json
from datetime import datetime, timedelta

from conftest import login


def _past(minutes=5):
    return (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()


def _future(minutes=60):
    return (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()


def test_cron_run_requires_login(client):
    assert client.post("/cron/run").status_code == 401


def test_cron_sends_due_email(client, user):
    from app.config import settings

    login(client, "nina@test-suite.dev", "nina12345")
    created = client.post(
        "/emails",
        json={
            "recipient_email": "someone@example.com",
            "subject": "Due now",
            "body": "This is due",
            "scheduled_time": _past(),
        },
    ).json()

    response = client.post("/cron/run")
    assert response.status_code == 200
    body = response.json()
    assert body["checked"] == 1
    assert body["sent"] == 1
    assert body["failed"] == 0

    email = client.get(f"/emails/{created['id']}").json()
    assert email["status"] == "sent"
    assert email["attempts"] == 1
    assert email["sent_at"] is not None

    outbox = [json.loads(line) for line in open(settings.mock_outbox_path)]
    assert len(outbox) == 1
    assert outbox[0]["to"] == "someone@example.com"
    assert outbox[0]["subject"] == "Due now"


def test_cron_ignores_future_emails(client, user):
    login(client, "nina@test-suite.dev", "nina12345")
    client.post(
        "/emails",
        json={
            "recipient_email": "someone@example.com",
            "subject": "Not yet",
            "body": "body",
            "scheduled_time": _future(),
        },
    )

    response = client.post("/cron/run")
    assert response.json() == {"mode": "mock", "checked": 0, "sent": 0, "failed": 0}


def test_cron_is_idempotent_for_already_sent_email(client, user):
    login(client, "nina@test-suite.dev", "nina12345")
    client.post(
        "/emails",
        json={
            "recipient_email": "someone@example.com",
            "subject": "Due now",
            "body": "body",
            "scheduled_time": _past(),
        },
    )

    first = client.post("/cron/run").json()
    second = client.post("/cron/run").json()

    assert first["sent"] == 1
    assert second["checked"] == 0
    assert second["sent"] == 0


def test_cron_retries_failures_until_max_attempts(client, user):
    login(client, "nina@test-suite.dev", "nina12345")
    created = client.post(
        "/emails",
        json={
            "recipient_email": "bounce-always@example.com",
            "subject": "Will fail",
            "body": "body",
            "scheduled_time": _past(),
        },
    ).json()

    # MAIL_MAX_ATTEMPTS defaults to 3: the first two runs retry (status
    # stays pending), the third exhausts the budget and marks it failed.
    for expected_attempts in (1, 2, 3):
        response = client.post("/cron/run").json()
        assert response["checked"] == 1
        email = client.get(f"/emails/{created['id']}").json()
        assert email["attempts"] == expected_attempts
        assert "simulated delivery failure" in email["last_error"]

    assert email["status"] == "failed"

    # A fourth run no longer picks it up at all.
    response = client.post("/cron/run").json()
    assert response["checked"] == 0
